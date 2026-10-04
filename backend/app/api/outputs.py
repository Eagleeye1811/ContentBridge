from __future__ import annotations

import functools
import uuid

import anyio
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession, FlexibleUser
from app.api.facts import _serialize as serialize_sheet
from app.models import (
    AuditLog,
    Document,
    DocumentBlock,
    Export,
    Fact,
    FactSheet,
    Job,
    Output,
    OutputClaim,
)
from app.pipeline.stages import generate_outputs
from app.schemas.content_ir import ContentIR
from app.schemas.documents import JobOut
from app.schemas.outputs import (
    AudienceInfo,
    CatalogOut,
    ContentIRUpdate,
    ControlInfo,
    FormatChoiceInfo,
    FormatInfo,
    FormatOptionInfo,
    GenerateRequest,
    OutputDetail,
    OutputListItem,
    OutputOut,
)
from app.services.access import can_create
from app.services.generation.audiences import AUDIENCES, LANGUAGES
from app.services.generation.controls import (
    DEFAULT_CONTROLS,
    DETAIL_LEVELS,
    OBJECTIVES,
    STYLES,
    TONES,
    UnknownControl,
    resolve_controls,
)
from app.services.generation.formats import FORMATS, UnknownFormat, get_format
from app.services.generation.formats.base import (
    UnknownFormatOption,
    chosen_audience,
    resolve_options,
)
from app.services.llm import llm_available
from app.services.rendering import RENDERERS, get_renderer, render_bytes
from app.services.storage import storage

router = APIRouter(tags=["outputs"])


async def _owned_document(db: DbSession, user: CurrentUser, document_id: uuid.UUID) -> Document:
    from app.config import settings

    doc = await db.get(Document, document_id)
    if doc is None or (
        user.role != "admin"
        and doc.owner_id != user.id
        and settings.app_env != "development"
    ):
        raise HTTPException(404, "Document not found")
    return doc


async def _owned_output(db: DbSession, user: CurrentUser, output_id: uuid.UUID) -> Output:
    output = await db.get(Output, output_id)
    if output is None:
        raise HTTPException(404, "Output not found")
    await _owned_document(db, user, output.document_id)
    return output


def _title(output: Output) -> str:
    return (output.content_ir or {}).get("title", "") if output.content_ir else ""


def _summary(output: Output) -> OutputOut:
    try:
        renderers = list(get_format(output.type).renderers)
    except UnknownFormat:
        renderers = []
    return OutputOut.model_validate(output).model_copy(
        update={"title": _title(output), "renderers": renderers}
    )


def _control_infos(registry) -> list[ControlInfo]:
    return [
        ControlInfo(key=o.key, name=o.name, description=o.description) for o in registry.values()
    ]


@router.get("/catalog", response_model=CatalogOut)
async def catalog() -> CatalogOut:
    """Everything the Studio can offer, read straight from the registries."""
    return CatalogOut(
        formats=[
            FormatInfo(
                key=s.key,
                name=s.name,
                description=s.description,
                renderers=list(s.renderers),
                options=[
                    FormatOptionInfo(
                        key=o.key,
                        label=o.label,
                        help=o.help,
                        default=o.default,
                        choices=[FormatChoiceInfo(key=c.key, label=c.label) for c in o.choices],
                    )
                    for o in s.options
                ],
            )
            for s in FORMATS.values()
        ],
        audiences=[AudienceInfo(key=a.key, name=a.name) for a in AUDIENCES.values()],
        languages=LANGUAGES,
        tones=_control_infos(TONES),
        detail_levels=_control_infos(DETAIL_LEVELS),
        objectives=_control_infos(OBJECTIVES),
        styles=_control_infos(STYLES),
        defaults=DEFAULT_CONTROLS,
    )


@router.post("/documents/{document_id}/outputs", response_model=JobOut, status_code=202)
async def create_outputs(
    document_id: uuid.UUID,
    body: GenerateRequest,
    db: DbSession,
    user: CurrentUser,
    background: BackgroundTasks,
) -> JobOut:
    """Fan out one request across types and languages. One job, many outputs."""
    await _owned_document(db, user, document_id)

    types: list[str] = []
    for key in body.types:
        try:
            # Normalise legacy keys (social -> linkedin) so new rows use the current one.
            canonical = get_format(key).key
        except UnknownFormat as exc:
            raise HTTPException(422, str(exc)) from exc
        if canonical not in types:
            types.append(canonical)
    refused = [t for t in types if not can_create(user, t)]
    if refused:
        role = user.job_role.name if user.job_role else "your role"
        names = ", ".join(get_format(t).name for t in refused)
        raise HTTPException(403, f"{role} cannot create: {names}.")
    if body.audience is not None and body.audience not in AUDIENCES:
        raise HTTPException(422, f"Unknown audience {body.audience!r}")
    unknown_langs = [x for x in body.languages if x not in LANGUAGES]
    if unknown_langs:
        raise HTTPException(422, f"Unsupported language(s): {', '.join(unknown_langs)}")

    # Each type gets its own audience and controls: an explicit choice in the
    # request wins, then an option that implies one, then the type's defaults.
    plans: dict[str, dict] = {}
    for t in types:
        spec = get_format(t)
        try:
            options = resolve_options(spec, body.options.get(t) or body.options.get(spec.key))
            controls = resolve_controls(
                {
                    **{k: v for k, v in spec.defaults.items() if k != "audience"},
                    **body.controls(),
                }
            )
        except (UnknownFormatOption, UnknownControl) as exc:
            raise HTTPException(422, str(exc)) from exc
        audience = (
            body.audience
            or chosen_audience(spec, options)
            or spec.defaults.get("audience")
            or "officer"
        )
        plans[t] = {"options": options, "controls": controls, "audience": audience}

    sheet = await db.scalar(
        select(FactSheet).where(
            FactSheet.document_id == document_id, FactSheet.is_current.is_(True)
        )
    )
    if sheet is None:
        raise HTTPException(
            409, "This source has no key facts yet. Open Key facts and find them first."
        )
    if not llm_available():
        raise HTTPException(
            503, "Writing is not available: no AI model is configured on the server."
        )

    requests = [
        {
            "type": t,
            "audience": plans[t]["audience"],
            "language": lang,
            "controls": plans[t]["controls"],
            "options": plans[t]["options"],
        }
        for t in types
        for lang in body.languages
    ]

    job = Job(
        document_id=document_id,
        kind="generate",
        status="queued",
        stage="queued",
        payload={"requests": requests},
    )
    db.add(job)
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="document",
            entity_id=document_id,
            action="generate",
            payload={"requests": requests},
        )
    )
    # Commit before scheduling: the task opens its own session.
    await db.commit()

    background.add_task(generate_outputs, document_id, job.id, requests)
    return JobOut.model_validate(job)


@router.get("/documents/{document_id}/outputs", response_model=list[OutputOut])
async def list_outputs(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> list[OutputOut]:
    await _owned_document(db, user, document_id)
    rows = await db.scalars(
        select(Output).where(Output.document_id == document_id).order_by(Output.created_at.desc())
    )
    return [_summary(o) for o in rows]


@router.get("/outputs", response_model=list[OutputListItem])
async def list_all_outputs(db: DbSession, user: CurrentUser) -> list[OutputListItem]:
    """Everything this user has created, across all of their sources, newest first."""
    rows = await db.execute(
        select(Output, Document.filename)
        .join(Document, Document.id == Output.document_id)
        .where(Document.owner_id == user.id)
        .order_by(Output.created_at.desc())
    )
    return [
        OutputListItem(**_summary(output).model_dump(), document_name=filename)
        for output, filename in rows.all()
    ]


@router.get("/outputs/{output_id}", response_model=OutputDetail)
async def get_output(output_id: uuid.UUID, db: DbSession, user: CurrentUser) -> OutputDetail:
    output = await _owned_output(db, user, output_id)
    ir = ContentIR.model_validate(output.content_ir)

    cited = {fid for node in ir.nodes for fid in node.fact_ids}
    sheet = await db.scalar(
        select(FactSheet)
        .where(FactSheet.id == output.fact_sheet_id)
        .options(selectinload(FactSheet.facts).selectinload(Fact.evidence))
    )
    facts = []
    if sheet is not None:
        serialized = await serialize_sheet(db, sheet)
        facts = [f for f in serialized.facts if str(f.id) in cited]

    return OutputDetail(
        **_summary(output).model_dump(),
        content_ir=ir,
        facts=facts,
    )


@router.patch("/outputs/{output_id}", response_model=OutputDetail)
async def update_output(
    output_id: uuid.UUID, body: ContentIRUpdate, db: DbSession, user: CurrentUser
) -> OutputDetail:
    """Human edit. ContentIR is the unit a reviewer edits, not rendered text."""
    output = await _owned_output(db, user, output_id)
    if output.status == "approved":
        raise HTTPException(409, "Approved outputs cannot be edited. Regenerate a new version.")

    output.content_ir = body.content_ir.model_dump(mode="json")

    # Any edit invalidates the prior verification completely. Clearing the
    # score but leaving `verified_at` and the claim rows in place would let an
    # edited output be submitted, and approved, on evidence that describes text
    # which no longer exists.
    output.status = "draft"
    output.trust_score = None
    output.verified_at = None
    await db.execute(delete(OutputClaim).where(OutputClaim.output_id == output.id))
    db.add(AuditLog(actor_id=user.id, entity="output", entity_id=output.id, action="edit"))
    await db.commit()

    return await get_output(output_id, db, user)


@router.post("/outputs/{output_id}/regenerate", response_model=JobOut, status_code=202)
async def regenerate(
    output_id: uuid.UUID, db: DbSession, user: CurrentUser, background: BackgroundTasks
) -> JobOut:
    output = await _owned_output(db, user, output_id)
    if not can_create(user, get_format(output.type).key):
        raise HTTPException(403, f"Your role cannot create {get_format(output.type).name}.")
    if not llm_available():
        raise HTTPException(
            503, "Writing is not available: no AI model is configured on the server."
        )

    request = {
        "type": get_format(output.type).key,
        "audience": output.audience,
        "language": output.language,
        "controls": {k: v for k, v in (output.controls or {}).items() if k != "format"},
        "options": (output.controls or {}).get("format") or {},
    }
    job = Job(
        document_id=output.document_id,
        kind="generate",
        status="queued",
        stage="queued",
        payload={"requests": [request]},
    )
    db.add(job)
    await db.commit()

    background.add_task(generate_outputs, output.document_id, job.id, [request])
    return JobOut.model_validate(job)


@router.get("/outputs/{output_id}/export")
async def export_output(
    output_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    format: str = Query("markdown", description=f"one of: {', '.join(sorted(RENDERERS))}"),
    citations: bool = Query(False, description="append a source list"),
) -> Response:
    """Render the ContentIR. A pure function of the stored structure -- no LLM
    call, so the same output always exports identically."""
    output = await _owned_output(db, user, output_id)
    if format not in RENDERERS:
        raise HTTPException(422, f"Unknown format {format!r}. Available: {', '.join(RENDERERS)}")

    spec = get_format(output.type)
    if format not in spec.renderers:
        raise HTTPException(
            422,
            f"{spec.name} cannot be rendered as {format!r}. Available: {', '.join(spec.renderers)}",
        )

    document = await db.get(Document, output.document_id)
    source_name = document.filename if document else ""

    # Resolve fact ids to human-readable citations for the appendix. Renderers
    # stay pure: they are handed the strings, they do not look anything up.
    citation_map: dict[str, str] = {}
    if citations:
        sheet = await db.scalar(
            select(FactSheet)
            .where(FactSheet.id == output.fact_sheet_id)
            .options(selectinload(FactSheet.facts).selectinload(Fact.evidence))
        )
        if sheet is not None:
            blocks = {
                b.id: b
                for b in await db.scalars(
                    select(DocumentBlock).where(DocumentBlock.document_id == output.document_id)
                )
            }
            for fact in sheet.facts:
                places = []
                for ev in fact.evidence:
                    block = blocks.get(ev.block_id)
                    if block is None:
                        continue
                    where = f"p.{block.page_no}"
                    if block.section_path:
                        where += f", {block.section_path}"
                    places.append(where)
                citation_map[str(fact.id)] = f"{fact.statement} \u2014 {source_name}" + (
                    f" ({'; '.join(dict.fromkeys(places))})" if places else ""
                )

    ir = ContentIR.model_validate(output.content_ir)

    # ── MP4: serve pre-rendered video if available, else render in thread pool ────
    if format == "mp4":
        existing_export = await db.scalar(
            select(Export)
            .where(Export.output_id == output.id, Export.format == format)
            .order_by(Export.created_at.desc())
        )
        if existing_export and existing_export.storage_uri:
            try:
                body = await anyio.to_thread.run_sync(storage.get, existing_export.storage_uri)
                renderer = get_renderer(format)
                stem = f"{output.type}_{output.audience}_{output.language}_v{output.version}"
                filename = f"{stem}.{renderer.extension}"
                return Response(
                    content=body,
                    media_type=renderer.media_type,
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'},
                )
            except Exception:
                pass  # Fallback to fresh render if stored file is missing

        from app.services.rendering.video_renderer import render as video_render

        orientation = (output.controls or {}).get("format", {}).get("screen", "wide")
        lang = output.language or "en"

        body = await anyio.to_thread.run_sync(
            functools.partial(video_render, ir, orientation=orientation, language=lang),
            cancellable=True,
        )
    else:
        body = render_bytes(
            ir,
            format,
            include_citations=citations,
            citations=citation_map,
            source_name=source_name,
            output_type=spec.key,
        )

    renderer = get_renderer(format)
    stem = f"{output.type}_{output.audience}_{output.language}_v{output.version}"
    filename = f"{stem}.{renderer.extension}"

    # Record what left the building.
    uri = await anyio.to_thread.run_sync(storage.put, f"exports/{output.id}/{filename}", body)
    db.add(Export(output_id=output.id, format=format, storage_uri=uri, size_bytes=len(body)))
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="output",
            entity_id=output.id,
            action="export",
            payload={"format": format, "bytes": len(body)},
        )
    )
    await db.commit()

    return Response(
        content=body,
        media_type=renderer.media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/outputs/{output_id}/video-status")
async def get_video_status(
    output_id: uuid.UUID,
    db: DbSession,
    user: FlexibleUser,
) -> dict:
    """Check if pre-rendered MP4 video is available for an output without blocking."""
    output = await _owned_output(db, user, output_id)
    existing_export = await db.scalar(
        select(Export)
        .where(Export.output_id == output.id, Export.format == "mp4")
        .order_by(Export.created_at.desc())
    )
    if existing_export and existing_export.storage_uri:
        local_path = storage.path(existing_export.storage_uri)
        if local_path and local_path.exists() and local_path.stat().st_size > 0:
            return {
                "ready": True,
                "size_bytes": local_path.stat().st_size,
                "created_at": existing_export.created_at.isoformat() if existing_export.created_at else None,
            }
    return {"ready": False, "size_bytes": None, "created_at": None}


@router.get("/outputs/{output_id}/video-stream")
async def stream_output_video(
    output_id: uuid.UUID,
    db: DbSession,
    user: FlexibleUser,
) -> Response:
    """Stream pre-rendered MP4 video file with HTTP Range partial content support."""
    from fastapi.responses import FileResponse

    output = await _owned_output(db, user, output_id)
    existing_export = await db.scalar(
        select(Export)
        .where(Export.output_id == output.id, Export.format == "mp4")
        .order_by(Export.created_at.desc())
    )
    if not existing_export or not existing_export.storage_uri:
        raise HTTPException(404, "Video has not been rendered yet. Call render-video first.")

    local_path = storage.path(existing_export.storage_uri)
    if not local_path or not local_path.exists():
        raise HTTPException(404, "Rendered video file not found in storage.")

    return FileResponse(
        str(local_path),
        media_type="video/mp4",
        filename=f"video_{output.audience}_{output.language}_v{output.version}.mp4",
    )


_THUMB_CACHE: dict[tuple[str, int], bytes] = {}


def _render_thumb_sync(target_scene: Any, idx: int, total_scenes: int, orientation: str) -> bytes:
    import io
    import pathlib
    import tempfile
    from PIL import Image
    from app.services.rendering.providers import HybridVideoPipeline, ScenePlanner

    scene_spec = ScenePlanner.plan_scene(
        node=target_scene,
        scene_id=idx + 1,
        duration=5.0,
        orientation=orientation,
    )

    img = None
    with tempfile.TemporaryDirectory(prefix="cb_thumb_", ignore_cleanup_errors=True) as tmpdir:
        tmp = pathlib.Path(tmpdir)
        try:
            pipeline = HybridVideoPipeline()
            clip_path, _ = pipeline.resolve_scene_clip(scene_spec, tmp)
            if clip_path and clip_path.exists():
                from moviepy import VideoFileClip
                with VideoFileClip(str(clip_path)) as vclip:
                    t = min(1.0, max(0.0, vclip.duration / 2.0))
                    frame = vclip.get_frame(t)
                    img = Image.fromarray(frame)
        except Exception:
            img = None

    if img is None:
        from app.services.rendering.scene_visual import render_scene_image
        img = render_scene_image(
            target_scene.title,
            visual_notes=target_scene.notes or "",
            items=target_scene.items,
            index=idx,
            total=total_scenes,
            orientation=orientation,
        )

    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


@router.get("/outputs/{output_id}/thumbnail")
async def get_output_thumbnail(
    output_id: uuid.UUID,
    db: DbSession,
    user: FlexibleUser,
    scene: int = Query(0, description="0-based scene index"),
) -> Response:
    """Generate & return an actual video frame thumbnail image for any scene in a video output."""
    output = await _owned_output(db, user, output_id)
    cache_key = (str(output_id), scene)
    if cache_key in _THUMB_CACHE:
        return Response(content=_THUMB_CACHE[cache_key], media_type="image/jpeg")

    ir = ContentIR.model_validate(output.content_ir)
    scenes = [n for n in ir.nodes if n.kind == "scene"]
    if not scenes:
        raise HTTPException(400, "Output has no scene nodes.")

    idx = max(0, min(scene, len(scenes) - 1))
    target_scene = scenes[idx]
    orientation = (output.controls or {}).get("format", {}).get("screen", "wide")

    jpeg_bytes = await anyio.to_thread.run_sync(
        _render_thumb_sync, target_scene, idx, len(scenes), orientation
    )
    _THUMB_CACHE[cache_key] = jpeg_bytes
    return Response(content=jpeg_bytes, media_type="image/jpeg")


@router.post("/outputs/{output_id}/render-video", response_model=JobOut, status_code=202)
async def render_video(
    output_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    background: BackgroundTasks,
) -> JobOut:
    """Kick off an asynchronous MP4 render job for a video output.

    Video generation is CPU-intensive (30-90 s per video).  Rather than
    blocking the HTTP connection, this endpoint creates a Job row immediately
    and runs the render in the background.  Poll ``GET /jobs/{job_id}`` to
    track progress; the rendered file URI is returned in ``result.storage_uri``
    when the job succeeds.
    """
    from app.pipeline.stages import render_video_output

    output = await _owned_output(db, user, output_id)
    spec = get_format(output.type)
    if "mp4" not in spec.renderers:
        raise HTTPException(422, f"{spec.name} does not support MP4 export.")

    # Clear prior stale mp4 export rows and storage files
    exports = list(
        await db.scalars(
            select(Export).where(Export.output_id == output_id, Export.format == "mp4")
        )
    )
    for exp in exports:
        if exp.storage_uri:
            try:
                storage.delete(exp.storage_uri)
            except Exception:
                pass
        await db.delete(exp)

    job = Job(
        document_id=output.document_id,
        kind="render_video",
        status="queued",
        stage="queued",
        payload={"output_id": str(output_id)},
    )
    db.add(job)
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="output",
            entity_id=output_id,
            action="render_video",
        )
    )
    await db.commit()

    background.add_task(render_video_output, output_id, job.id)
    return JobOut.model_validate(job)
