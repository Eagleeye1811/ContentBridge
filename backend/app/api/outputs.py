from __future__ import annotations

import logging
from datetime import UTC, datetime
import uuid

import anyio
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Response
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

log = logging.getLogger(__name__)

from app.api.deps import CurrentUser, DbSession
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
from app.schemas.content_ir import ContentIR, DraftNode, Node
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
    PresentationOutlineRequest,
    PresentationOutlineResponse,
    PresentationReconfigureRequest,
    PresentationReconfigureResponse,
    PresentationRevertRequest,
    SlideCountAdjustRequest,
    SlideRegenerateRequest,
    SendEmailRequest,
    SendEmailResponse,
    SlideOutlineItem,
)
from app.services.access import can_create
from app.services.email_dispatch import send_official_email
from app.services.generation.generator import generate
from app.services.generation.prompt_builder import render_facts
from app.services.llm import get_llm
from app.services.generation.audiences import AUDIENCES, LANGUAGES, get_audience, UnknownAudience
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
    apply_options,
    chosen_audience,
    resolve_options,
)
from app.services.llm import llm_available
from app.services.rendering import RENDERERS, get_renderer, render_bytes
from app.services.storage import storage

router = APIRouter(tags=["outputs"])


async def _owned_document(db: DbSession, user: CurrentUser, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
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
        audiences=[AudienceInfo(key=a.key, name=a.name) for a in {a.key: a for a in AUDIENCES.values()}.values()],
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
    if body.audience is not None:
        try:
            get_audience(body.audience)
        except UnknownAudience as exc:
            raise HTTPException(422, str(exc)) from exc
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
        audience = get_audience(
            body.audience
            or chosen_audience(spec, options)
            or spec.defaults.get("audience")
            or "officer"
        ).key
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

    ir = body.content_ir
    if output.type == "ppt":
        from app.services.rendering.layout_validator import validate_and_autofix_deck
        ir, _ = validate_and_autofix_deck(ir)

    output.content_ir = ir.model_dump(mode="json")

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


@router.post("/documents/{document_id}/presentation-outline", response_model=PresentationOutlineResponse)
async def generate_presentation_outline(
    document_id: uuid.UUID,
    body: PresentationOutlineRequest,
    db: DbSession,
    user: CurrentUser,
) -> PresentationOutlineResponse:
    """Generate an AI slide outline before generating the full PowerPoint presentation."""
    doc = await _owned_document(db, user, document_id)
    sheet = await db.scalar(
        select(FactSheet)
        .where(FactSheet.document_id == document_id, FactSheet.is_current.is_(True))
        .options(selectinload(FactSheet.facts))
        .order_by(FactSheet.version.desc())
    )
    if sheet is None or not sheet.facts:
        raise HTTPException(
            409, "This source has no key facts yet. Open Key facts and find them first."
        )
    if not llm_available():
        raise HTTPException(
            503, "Outline generation is not available: no AI model is configured on the server."
        )

    facts = sorted(sheet.facts, key=lambda f: (f.type, f.key))
    fact_block, label_map = render_facts(facts)

    target_count = int(body.slide_count) if body.slide_count and body.slide_count.isdigit() else None
    content_slides_needed = max(1, target_count - 1) if target_count else None
    count_instruction = (
        f"EXACTLY {content_slides_needed} content slide cards (which with 1 cover slide equals {target_count} physical slides total)"
        if content_slides_needed
        else "a reasonable number of content slide cards (between 4 and 14)"
    )

    prompt = f"""You are an expert presentation designer. Create a slide outline for a presentation based ONLY on the provided source facts.

PRESENTATION CONFIGURATION:
- Title Hint: {body.title or "Suggest an executive title based on facts"}
- Purpose: {body.purpose}
- Audience: {body.audience}
- Target Total Physical Slide Count: {body.slide_count} ({count_instruction})
- Duration: {body.duration} minutes
- Language: {body.language}
- Detail Level: {body.content_detail}
- Visual Preference: {body.visual_preference}
- Additional Guidance: {body.additional_instructions or "None"}

SOURCE FACTS:
{fact_block}

Produce a structured presentation outline with:
1. `title`: Main presentation title.
2. `slides`: List of slide outline cards. You MUST produce {count_instruction}. Each slide card MUST have:
   - `id`: Short stable ID (e.g., out_1, out_2)
   - `title`: Short slide title (under 8 words)
   - `key_message`: Core takeaway of this slide
   - `summary`: Short summary of points to present
   - `suggested_layout`: One of 'standard_bullet', 'two_column', 'process', 'timeline', 'metrics', 'comparison', 'table', 'key_takeaways', 'references'
   - `fact_ids`: Array of fact labels cited (e.g. ["f0", "f2"])
"""
    llm = get_llm()
    outline = await llm.complete_structured(
        system="You structure presentation slide outlines strictly from source facts.",
        prompt=prompt,
        schema=PresentationOutlineResponse,
    )

    # Validate and adjust outline content slide count so total physical slides = target_count (cover + content slides)
    if target_count and outline.slides:
        target_content_count = max(1, target_count - 1)
        if len(outline.slides) > target_content_count:
            outline.slides = outline.slides[:target_content_count]
        elif len(outline.slides) < target_content_count:
            existing_count = len(outline.slides)
            layouts = ['standard_bullet', 'two_column', 'process', 'metrics', 'key_takeaways', 'references']
            for i in range(existing_count + 1, target_content_count + 1):
                outline.slides.append(
                    SlideOutlineItem(
                        id=f"out_{i}",
                        title=f"Detailed Findings & Action Plan Part {i - existing_count}",
                        key_message="Strategic recommendations and implementation steps.",
                        summary="Overview of implementation roadmap and verified findings.",
                        suggested_layout=layouts[(i - 1) % len(layouts)],
                        fact_ids=[f"f{min(i, len(facts)-1)}"] if facts else [],
                    )
                )

    return outline


@router.post("/outputs/{output_id}/slides/{slide_id}/regenerate", response_model=OutputDetail)
async def regenerate_single_slide(
    output_id: uuid.UUID,
    slide_id: str,
    body: SlideRegenerateRequest,
    db: DbSession,
    user: CurrentUser,
) -> OutputDetail:
    """Regenerate a single slide using AI while keeping all other slides intact."""
    output = await _owned_output(db, user, output_id)
    if output.status == "approved":
        raise HTTPException(409, "Approved outputs cannot be edited. Regenerate a new version.")
    if not llm_available():
        raise HTTPException(
            503, "Writing is not available: no AI model is configured on the server."
        )

    ir = ContentIR.model_validate(output.content_ir)
    target_node = next((n for n in ir.nodes if n.id == slide_id), None)
    if target_node is None:
        raise HTTPException(404, f"Slide node {slide_id!r} not found in this presentation.")

    sheet = await db.scalar(
        select(FactSheet)
        .where(FactSheet.id == output.fact_sheet_id)
        .options(selectinload(FactSheet.facts))
    )
    if sheet is None or not sheet.facts:
        raise HTTPException(409, "Fact sheet not found for this presentation.")

    document = await db.get(Document, output.document_id)
    source_name = document.filename if document else ""

    facts = sorted(sheet.facts, key=lambda f: (f.type, f.key))
    fact_block, label_map = render_facts(facts)

    prompt = f"""Rewrite and enhance ONLY Slide Node '{slide_id}' ({target_node.title or 'Slide'}).

CURRENT SLIDE CONTENT:
Title: {target_node.title}
Items: {target_node.items}
Notes: {target_node.notes}
Layout: {target_node.layout}

USER REGENERATION INSTRUCTION:
{body.instructions or "Enhance clarity, conciseness, and speaker notes."}

SOURCE FACTS:
{fact_block}

Produce the updated single DraftNode for this slide. Keep kind as 'slide'. Cite valid fact labels in fact_ids.
"""
    llm = get_llm()
    updated_draft_node = await llm.complete_structured(
        system="You rewrite individual presentation slides strictly based on source facts.",
        prompt=prompt,
        schema=DraftNode,
    )

    new_node = Node(
        id=slide_id,
        kind="slide",
        title=updated_draft_node.title,
        text=updated_draft_node.text,
        items=updated_draft_node.items or None,
        notes=updated_draft_node.notes,
        rows=updated_draft_node.rows or None,
        layout=updated_draft_node.layout or target_node.layout,
        fact_ids=[str(label_map[lbl].id) for lbl in updated_draft_node.fact_ids if lbl in label_map],
    )

    new_nodes = [new_node if n.id == slide_id else n for n in ir.nodes]
    updated_ir = ContentIR(title=ir.title, nodes=new_nodes)
    if output.type == "ppt":
        from app.services.rendering.layout_validator import validate_and_autofix_deck
        updated_ir, _ = validate_and_autofix_deck(updated_ir)

    output.content_ir = updated_ir.model_dump(mode="json")
    output.status = "draft"
    db.add(AuditLog(actor_id=user.id, entity="output", entity_id=output.id, action="slide_regenerate"))
    await db.commit()

    return await get_output(output_id, db, user)


@router.get("/outputs/{output_id}/export")
async def export_output(
    output_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    format: str = Query("markdown", description=f"one of: {', '.join(sorted(RENDERERS))}"),
    citations: bool = Query(False, description="append a source list"),
    theme: str = Query("navy_white", description="theme for PowerPoint export"),
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
    stored_theme = (output.controls or {}).get("theme")
    effective_theme = (theme if (theme and theme != "navy_white") else None) or stored_theme or theme or "corporate_blue"

    body = render_bytes(
        ir,
        format,
        include_citations=citations,
        citations=citation_map,
        source_name=source_name,
        output_type=spec.key,
        theme=effective_theme,
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


def check_deck_quality(ir: ContentIR, detail_level: str = "balanced") -> list[str]:
    """Inspect ContentIR deck and return quality & layout geometry warnings."""
    from app.services.rendering.layout_validator import validate_deck_geometry
    return validate_deck_geometry(ir, detail_level=detail_level)


@router.post("/outputs/{output_id}/reconfigure", response_model=PresentationReconfigureResponse)
async def reconfigure_presentation(
    output_id: uuid.UUID,
    body: PresentationReconfigureRequest,
    db: DbSession,
    user: CurrentUser,
) -> PresentationReconfigureResponse:
    """Reconfigure an existing presentation: theme, detail level, audience, purpose, language, and slide content."""
    output = await _owned_output(db, user, output_id)
    if output.status == "approved":
        raise HTTPException(409, "Approved outputs cannot be reconfigured. Regenerate a new version.")

    summary: list[str] = []

    curr_controls = output.controls or {}
    old_theme = curr_controls.get("theme", "corporate_blue")
    old_detail = curr_controls.get("detail_level", "balanced")
    old_purpose = curr_controls.get("purpose", "executive briefing")
    old_audience = output.audience
    old_lang = output.language
    current_ir = ContentIR.model_validate(output.content_ir)
    old_title = current_ir.title or ""

    new_theme = body.config.theme if (body.config and body.config.theme) else old_theme
    new_detail = body.config.content_detail if (body.config and body.config.content_detail) else old_detail
    new_purpose = body.config.purpose if (body.config and body.config.purpose) else old_purpose
    new_audience = body.config.audience if (body.config and body.config.audience) else old_audience
    new_lang = body.config.language if (body.config and body.config.language) else old_lang
    new_title = (
        body.config.title.strip()
        if (body.config and body.config.title is not None and body.config.title.strip())
        else old_title
    )
    new_duration = body.config.duration if (body.config and body.config.duration) else curr_controls.get("duration", "10")
    new_instructions = body.config.additional_instructions if (body.config and body.config.additional_instructions) else ""

    # Validate target audience
    try:
        aud_profile = get_audience(new_audience)
    except UnknownAudience as exc:
        raise HTTPException(422, str(exc)) from exc

    # Determine if AI slide regeneration is required
    old_aud_profile = get_audience(old_audience)
    needs_content_regen = (
        old_detail != new_detail or
        old_purpose != new_purpose or
        old_aud_profile.key != aud_profile.key or
        old_lang != new_lang or
        (new_instructions and new_instructions != curr_controls.get("additional_instructions", "")) or
        (body.config and body.config.slide_count and body.config.slide_count != "auto")
    )

    new_ir = current_ir

    if needs_content_regen:
        if not llm_available():
            raise HTTPException(503, "Writing is not available: no AI model is configured on the server.")

        try:
            sheet = await db.scalar(
                select(FactSheet)
                .where(FactSheet.id == output.fact_sheet_id)
                .options(selectinload(FactSheet.facts))
            )
            if sheet and sheet.facts:
                document = await db.get(Document, output.document_id)
                source_name = document.filename if document else ""
                facts = sorted(sheet.facts, key=lambda f: (f.type, f.key))

                target_slides_opt = body.config.slide_count if (body.config and body.config.slide_count) else "auto"
                spec = apply_options(
                    get_format(output.type),
                    {"slides": target_slides_opt, "presenting_to": new_audience}
                )

                gen_controls = resolve_controls({
                    **{k: v for k, v in spec.defaults.items() if k != "audience"},
                    **{k: v for k, v in curr_controls.items() if k != "version_history"},
                    "detail_level": new_detail,
                    "purpose": new_purpose,
                    "duration": new_duration,
                    "additional_instructions": new_instructions,
                })

                gen_result = await generate(
                    facts=facts,
                    spec=spec,
                    audience=aud_profile,
                    language=new_lang,
                    source_name=source_name,
                    controls=gen_controls,
                )

                gen_ir = gen_result.content_ir

                # Preserve manually edited slides if requested
                if body.preserve_user_edits and body.content_ir:
                    modified_user_nodes = {
                        n.id: n for n in body.content_ir.nodes if getattr(n, "is_user_modified", False)
                    }
                    if modified_user_nodes:
                        merged_nodes = [modified_user_nodes.get(n.id, n) for n in gen_ir.nodes]
                        gen_ir = ContentIR(title=gen_ir.title or new_title, nodes=merged_nodes)
                        summary.append(f"Preserved {len(modified_user_nodes)} manually customized slide(s)")

                new_ir = gen_ir

        except Exception as exc:
            log.exception("Reconfiguration AI generation failed for output %s", output_id)
            raise HTTPException(
                500,
                f"Unable to update presentation: We couldn't regenerate the presentation with these settings. Please try again. ({exc})"
            ) from exc

    # Ensure title is updated on IR
    if new_title:
        new_ir = ContentIR(title=new_title, nodes=new_ir.nodes)

    # Auto-fit & validate deck geometry
    if output.type == "ppt":
        from app.services.rendering.layout_validator import validate_and_autofix_deck
        new_ir, fixes = validate_and_autofix_deck(new_ir, detail_level=new_detail)
        if fixes:
            summary.extend([f"Auto-fit: {f}" for f in fixes])

    # Record summary of changes
    if old_theme != new_theme:
        summary.append(f"Theme: {old_theme} → {new_theme}")
    if old_detail != new_detail:
        summary.append(f"Detail level: {old_detail.capitalize()} → {new_detail.capitalize()}")
    if old_purpose != new_purpose:
        summary.append(f"Purpose: {old_purpose} → {new_purpose}")
    if old_aud_profile.key != aud_profile.key:
        summary.append(f"Audience: {old_aud_profile.key} → {aud_profile.key}")
    if old_lang != new_lang:
        summary.append(f"Language: {old_lang.upper()} → {new_lang.upper()}")
    if old_title != new_title:
        summary.append(f"Title updated: '{new_title}'")

    if not summary:
        summary.append("Configuration updated successfully")

    # Snapshot previous version into version_history for version revert
    raw_history = curr_controls.get("version_history", [])
    version_history: list[dict[str, Any]] = []
    if isinstance(raw_history, list):
        for snap in raw_history[-9:]:
            if isinstance(snap, dict):
                clean_snap_controls = {
                    k: v for k, v in snap.get("controls", {}).items() if k != "version_history"
                }
                version_history.append({
                    "version": snap.get("version"),
                    "controls": clean_snap_controls,
                    "content_ir": snap.get("content_ir"),
                    "timestamp": snap.get("timestamp"),
                })

    snap_controls = {k: v for k, v in curr_controls.items() if k != "version_history"}
    version_history.append({
        "version": output.version,
        "controls": snap_controls,
        "content_ir": output.content_ir,
        "timestamp": datetime.now(UTC).isoformat(),
    })

    updated_controls = {
        **snap_controls,
        "theme": new_theme,
        "detail_level": new_detail,
        "purpose": new_purpose,
        "duration": new_duration,
        "additional_instructions": new_instructions,
        "version_history": version_history,
    }

    output.controls = updated_controls
    output.audience = aud_profile.key
    output.language = new_lang
    output.content_ir = new_ir.model_dump(mode="json")
    output.version += 1
    output.status = "draft"

    db.add(AuditLog(actor_id=user.id, entity="output", entity_id=output.id, action="reconfigure"))
    await db.commit()

    detail = await get_output(output_id, db, user)
    quality_warnings = check_deck_quality(new_ir, detail_level=new_detail)

    return PresentationReconfigureResponse(
        output=detail,
        change_summary=summary,
        warnings=quality_warnings,
    )


@router.post("/outputs/{output_id}/revert", response_model=OutputDetail)
async def revert_presentation(
    output_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    body: PresentationRevertRequest | None = None,
) -> OutputDetail:
    """Revert presentation to the previous version in history."""
    output = await _owned_output(db, user, output_id)
    raw_history = (output.controls or {}).get("version_history", [])
    history: list[dict[str, Any]] = []
    if isinstance(raw_history, list):
        for snap in raw_history:
            if isinstance(snap, dict):
                clean_snap_controls = {
                    k: v for k, v in snap.get("controls", {}).items() if k != "version_history"
                }
                history.append({
                    "version": snap.get("version"),
                    "controls": clean_snap_controls,
                    "content_ir": snap.get("content_ir"),
                    "timestamp": snap.get("timestamp"),
                })

    if not history:
        raise HTTPException(400, "No previous version available to revert.")

    last_snap = history.pop()
    output.content_ir = last_snap["content_ir"]
    clean_last_controls = {
        k: v for k, v in last_snap.get("controls", {}).items() if k != "version_history"
    }
    output.controls = {**clean_last_controls, "version_history": history}
    output.version = max(1, output.version - 1)
    output.status = "draft"

    db.add(AuditLog(actor_id=user.id, entity="output", entity_id=output.id, action="revert"))
    await db.commit()

    return await get_output(output_id, db, user)


@router.post("/outputs/{output_id}/adjust-outline", response_model=PresentationOutlineResponse)
async def adjust_presentation_outline(
    output_id: uuid.UUID,
    body: SlideCountAdjustRequest,
    db: DbSession,
    user: CurrentUser,
) -> PresentationOutlineResponse:
    """Propose slide count adjustments (add or consolidate slides) based on source facts."""
    output = await _owned_output(db, user, output_id)
    sheet = await db.scalar(
        select(FactSheet)
        .where(FactSheet.id == output.fact_sheet_id)
        .options(selectinload(FactSheet.facts))
    )
    if sheet is None or not sheet.facts:
        raise HTTPException(409, "Fact sheet not found for this presentation.")

    current_ir = ContentIR.model_validate(output.content_ir)
    current_slides = [n for n in current_ir.nodes if n.kind == "slide"]

    target_count = int(body.target_count) if body.target_count.isdigit() else (len(current_slides) + 1)
    target_content_count = max(1, target_count - 1)

    outline_items = [
        SlideOutlineItem(
            id=node.id,
            title=node.title or f"Slide {idx+2}",
            key_message=node.text or (node.items[0] if node.items else "Key message"),
            summary="; ".join((node.items or [])[:3]),
            suggested_layout=node.layout or "standard_bullet",
            fact_ids=node.fact_ids,
        )
        for idx, node in enumerate(current_slides)
    ]

    if target_content_count > len(outline_items):
        facts = sorted(sheet.facts, key=lambda f: (f.type, f.key))
        layouts = ['two_column', 'process', 'metrics', 'table', 'key_takeaways', 'references']
        for i in range(len(outline_items) + 1, target_content_count + 1):
            outline_items.append(
                SlideOutlineItem(
                    id=f"n_new_{i}",
                    title=f"Detailed Findings & Action Plan Part {i}",
                    key_message="Strategic recommendations and verified source details.",
                    summary="Overview of additional source facts and implementation steps.",
                    suggested_layout=layouts[(i - 1) % len(layouts)],
                    fact_ids=[str(facts[min(i, len(facts)-1)].id)] if facts else [],
                )
            )
    elif target_content_count < len(outline_items) and target_content_count >= 1:
        non_modified = [s for s in outline_items if not any(n.is_user_modified for n in current_slides if n.id == s.id)]
        modified = [s for s in outline_items if any(n.is_user_modified for n in current_slides if n.id == s.id)]
        
        kept = (modified + non_modified)[:target_content_count]
        outline_items = sorted(kept, key=lambda s: next((i for i, orig in enumerate(outline_items) if orig.id == s.id), 999))

    return PresentationOutlineResponse(
        title=current_ir.title,
        slides=outline_items,
    )


@router.post("/outputs/{id}/send-email", response_model=SendEmailResponse)
async def dispatch_output_email(
    id: uuid.UUID,
    req: SendEmailRequest,
    db: DbSession,
    user: CurrentUser,
) -> SendEmailResponse:
    """Send the generated email to a target recipient."""
    output = await db.get(Output, id)
    if output is None:
        raise HTTPException(status_code=404, detail="Output not found")

    if not req.to_email or "@" not in req.to_email:
        raise HTTPException(status_code=400, detail="A valid recipient email is required.")

    ir = ContentIR.model_validate(output.content_ir)
    subject = ir.title or "Official Communication"

    # Render email content
    from app.services.rendering import html_writer, text

    body_text = text.render(ir, output_type="email")
    if req.note:
        body_text = f"Sender Note:\n{req.note}\n\n---\n\n{body_text}"

    body_html = html_writer.render(ir, output_type="email")

    try:
        result = await send_official_email(
            to_email=req.to_email.strip(),
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            cc_emails=[c.strip() for c in req.cc_emails if c.strip()] if req.cc_emails else None,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Email delivery error: {exc}") from exc

    db.add(
        AuditLog(
            actor_id=user.id,
            entity="output",
            entity_id=output.id,
            action="send_email",
            payload={
                "recipient": req.to_email,
                "cc": req.cc_emails,
                "message_id": result.message_id,
                "delivery_mode": result.delivery_mode,
            },
        )
    )
    await db.commit()

    return SendEmailResponse(
        success=result.success,
        recipient=result.recipient,
        subject=result.subject,
        message_id=result.message_id,
        sent_at=result.sent_at,
        delivery_mode=result.delivery_mode,
        detail=result.detail,
    )

