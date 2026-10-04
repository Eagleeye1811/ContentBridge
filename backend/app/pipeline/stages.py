"""The one pipeline.

Intake runs parse -> index -> extract as a single job so the UI shows one
progress bar with honest stage names. Each stage is an independent coroutine,
so moving to a real worker queue later is mechanical.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

import anyio
from sqlalchemy import delete, select, update

from app.db import SessionLocal
from app.models import Chunk, Document, DocumentBlock, Fact, FactEvidence, FactSheet, Job
from app.pipeline.jobs import mark
from app.services.indexing.chunker import chunk_blocks
from app.services.indexing.embeddings import get_embedder
from app.services.indexing.qdrant_store import ChunkPoint, VectorStore
from app.services.ingestion import parse_document
from app.services.llm import llm_available
from app.services.sot.fact_extractor import extract_facts
from app.services.storage import storage

log = logging.getLogger(__name__)

# Progress is split across the three stages so the bar moves sensibly.
PARSE_SPAN = (0.05, 0.30)
INDEX_SPAN = (0.30, 0.60)
EXTRACT_SPAN = (0.60, 1.00)


def _lerp(span: tuple[float, float], fraction: float) -> float:
    lo, hi = span
    return lo + (hi - lo) * max(0.0, min(1.0, fraction))


# --------------------------------------------------------------------------
# Stage 1: parse
# --------------------------------------------------------------------------


async def _parse(db, document: Document, job: Job) -> int:
    await mark(db, job, stage="parsing document", progress=PARSE_SPAN[0])
    document.status = "parsing"
    await db.commit()

    data = await anyio.to_thread.run_sync(storage.get, document.storage_uri)
    parsed = await anyio.to_thread.run_sync(parse_document, document.filename, data)

    # Re-ingest is idempotent: drop anything from a previous attempt.
    await db.execute(delete(DocumentBlock).where(DocumentBlock.document_id == document.id))
    db.add_all(
        DocumentBlock(
            document_id=document.id,
            page_no=b.page_no,
            section_path=b.section_path,
            order_idx=b.order_idx,
            block_type=b.block_type,
            text=b.text,
            bbox=b.bbox,
        )
        for b in parsed.blocks
    )
    document.page_count = parsed.page_count
    document.status = "parsed"
    document.error = None
    await db.commit()
    return len(parsed.blocks)


# --------------------------------------------------------------------------
# Stage 2: index
# --------------------------------------------------------------------------


async def _index(db, document: Document, job: Job) -> int:
    await mark(db, job, stage="indexing chunks", progress=INDEX_SPAN[0])
    document.status = "indexing"
    await db.commit()

    blocks = list(
        await db.scalars(
            select(DocumentBlock)
            .where(DocumentBlock.document_id == document.id)
            .order_by(DocumentBlock.order_idx)
        )
    )
    chunks = chunk_blocks(blocks)
    if not chunks:
        document.status = "indexed"
        await db.commit()
        return 0

    embedder = get_embedder()
    store = VectorStore()
    try:
        await store.ensure_collection(embedder.dim)
        # Replace rather than append, so re-indexing cannot leave stale vectors.
        await store.delete_document(document.id)
        await db.execute(delete(Chunk).where(Chunk.document_id == document.id))

        vectors = await embedder.embed([c.text for c in chunks])
        await mark(db, job, progress=_lerp(INDEX_SPAN, 0.7))

        points, rows = [], []
        for chunk, vector in zip(chunks, vectors, strict=True):
            point_id = str(uuid.uuid4())
            points.append(
                ChunkPoint(
                    point_id=point_id,
                    vector=vector,
                    document_id=document.id,
                    block_ids=chunk.block_ids,
                    text=chunk.text,
                    page_no=chunk.page_no,
                    section_path=chunk.section_path,
                )
            )
            rows.append(
                Chunk(
                    document_id=document.id,
                    block_ids=chunk.block_ids,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    qdrant_point_id=point_id,
                )
            )

        await store.upsert(points)
        db.add_all(rows)
        document.status = "indexed"
        await db.commit()
    finally:
        await store.close()

    return len(chunks)


# --------------------------------------------------------------------------
# Stage 3: extract the Source of Truth
# --------------------------------------------------------------------------


async def _extract(db, document: Document, job: Job) -> int:
    from app.config import settings

    await mark(db, job, stage="extracting facts", progress=EXTRACT_SPAN[0])
    document.status = "extracting"
    await db.commit()

    blocks = list(
        await db.scalars(
            select(DocumentBlock)
            .where(DocumentBlock.document_id == document.id)
            .order_by(DocumentBlock.order_idx)
        )
    )

    facts = await extract_facts(blocks)

    # Supersede any previous sheet rather than deleting it: approvals and
    # outputs reference the version they were generated from.
    previous = await db.scalar(
        select(FactSheet)
        .where(FactSheet.document_id == document.id)
        .order_by(FactSheet.version.desc())
    )
    await db.execute(
        update(FactSheet).where(FactSheet.document_id == document.id).values(is_current=False)
    )

    sheet = FactSheet(
        document_id=document.id,
        version=(previous.version + 1) if previous else 1,
        model=settings.llm_model if settings.llm_provider != "stub" else "stub",
        is_current=True,
    )
    db.add(sheet)
    await db.flush()

    for fact in facts:
        row = Fact(
            fact_sheet_id=sheet.id,
            key=fact.key,
            type=fact.type,
            statement=fact.statement,
            canonical_value=fact.canonical_value,
            unit=fact.unit,
            confidence=fact.confidence,
        )
        db.add(row)
        await db.flush()
        db.add_all(
            FactEvidence(
                fact_id=row.id,
                block_id=e.block_id,
                quote=e.quote,
                char_start=e.char_start,
                char_end=e.char_end,
            )
            for e in fact.evidence
        )

    document.status = "ready"
    await db.commit()
    return len(facts)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------


async def process_document(document_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Full intake. Opens its own session: the request has already returned."""
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        document = await db.get(Document, document_id)
        if job is None or document is None:
            log.error("intake: job %s or document %s vanished", job_id, document_id)
            return

        try:
            await mark(db, job, status="running", stage="starting", progress=0.02)

            block_count = await _parse(db, document, job)
            chunk_count = await _index(db, document, job)

            result = {"blocks": block_count, "chunks": chunk_count, "pages": document.page_count}

            if llm_available():
                result["facts"] = await _extract(db, document, job)
                note = None
            else:
                # Degrade gracefully: the document is still fully searchable and
                # every block is citable. Extraction can be triggered later.
                note = (
                    "No LLM configured - skipped fact extraction. Set GEMINI_API_KEY "
                    "(or LLM_PROVIDER=stub), then POST /documents/{id}/fact-sheet."
                )
                result["facts"] = 0
                result["note"] = note
                log.warning("intake: %s", note)

            await mark(db, job, status="succeeded", stage="done", progress=1.0, result=result)
            log.info("intake complete for %s: %s", document.filename, result)

        except Exception as exc:  # noqa: BLE001 - surfaced through the job row
            log.exception("intake failed for document %s", document_id)
            await db.rollback()
            document.status = "failed"
            document.error = str(exc)
            await db.commit()
            await mark(db, job, status="failed", stage="failed", error=str(exc))


async def extract_only(document_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Re-run extraction against an already-indexed document."""
    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        document = await db.get(Document, document_id)
        if job is None or document is None:
            return
        try:
            await mark(db, job, status="running", stage="extracting facts", progress=0.1)
            count = await _extract(db, document, job)
            await mark(
                db, job, status="succeeded", stage="done", progress=1.0, result={"facts": count}
            )
        except Exception as exc:  # noqa: BLE001
            log.exception("extraction failed for document %s", document_id)
            await db.rollback()
            await mark(db, job, status="failed", stage="failed", error=str(exc))


# --------------------------------------------------------------------------
# Generation: one pipeline, many outputs
# --------------------------------------------------------------------------


async def generate_outputs(
    document_id: uuid.UUID,
    job_id: uuid.UUID,
    requests: list[dict],
) -> None:
    """Produce one Output row per (type, audience, language) combination.

    Every combination goes through the same generator; only the FormatSpec and
    the audience fragment differ. A failure on one combination does not abort
    the rest -- partial results are more useful than none.
    """
    from sqlalchemy.orm import selectinload

    from app.models import FactSheet, Output
    from app.services.generation.audiences import get_audience
    from app.services.generation.formats import get_format
    from app.services.generation.formats.base import apply_options
    from app.services.generation.generator import generate

    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        document = await db.get(Document, document_id)
        if job is None or document is None:
            log.error("generate: job %s or document %s vanished", job_id, document_id)
            return

        try:
            await mark(db, job, status="running", stage="loading facts", progress=0.05)

            sheet = await db.scalar(
                select(FactSheet)
                .where(FactSheet.document_id == document_id, FactSheet.is_current.is_(True))
                .options(selectinload(FactSheet.facts))
                .order_by(FactSheet.version.desc())
            )
            if sheet is None or not sheet.facts:
                raise RuntimeError("No current Source of Truth. Run extraction first.")

            facts = sorted(sheet.facts, key=lambda f: (f.type, f.key))
            created, failures = [], []

            for i, req in enumerate(requests):
                label = f"{req['type']}/{req['audience']}/{req['language']}"
                await mark(
                    db,
                    job,
                    stage=f"generating {label}",
                    progress=0.05 + 0.9 * (i / max(1, len(requests))),
                )
                try:
                    result = await generate(
                        facts=facts,
                        spec=apply_options(get_format(req["type"]), req.get("options")),
                        audience=get_audience(req["audience"]),
                        language=req["language"],
                        source_name=document.filename,
                        controls=req.get("controls"),
                    )
                except Exception as exc:  # noqa: BLE001 - reported per combination
                    log.exception("generation failed for %s", label)
                    failures.append(f"{label}: {exc}")
                    continue

                aud_key = get_audience(req["audience"]).key
                previous = await db.scalar(
                    select(Output)
                    .where(
                        Output.document_id == document_id,
                        Output.type == req["type"],
                        Output.audience.in_([req["audience"], aud_key]),
                        Output.language == req["language"],
                    )
                    .order_by(Output.version.desc())
                )
                final_ir = result.content_ir
                if req["type"] == "ppt":
                    from app.services.rendering.layout_validator import validate_and_autofix_deck
                    final_ir, fixes = validate_and_autofix_deck(
                        final_ir,
                        detail_level=(req.get("controls") or {}).get("detail_level", "balanced"),
                    )
                    if fixes:
                        log.info("%s auto-fixed layout issues: %s", label, "; ".join(fixes))

                output = Output(
                    document_id=document_id,
                    fact_sheet_id=sheet.id,
                    type=req["type"],
                    audience=aud_key,
                    language=req["language"],
                    controls={**(req.get("controls") or {}), "format": req.get("options") or {}},
                    status="draft",
                    content_ir=final_ir.model_dump(mode="json"),
                    version=(previous.version + 1) if previous else 1,
                    model=result.model,
                )
                db.add(output)
                await db.flush()
                created.append(str(output.id))
                if result.dropped_citations:
                    log.warning("%s dropped: %s", label, "; ".join(result.dropped_citations))

            await db.commit()

            if not created:
                raise RuntimeError("; ".join(failures) or "No outputs were generated")

            await mark(
                db,
                job,
                status="succeeded",
                stage="done",
                progress=1.0,
                result={"outputs": created, "failures": failures},
            )

        except Exception as exc:  # noqa: BLE001 - surfaced through the job row
            log.exception("generation job failed for document %s", document_id)
            await db.rollback()
            await mark(db, job, status="failed", stage="failed", error=str(exc))


# --------------------------------------------------------------------------
# Verification
# --------------------------------------------------------------------------


async def _persist_consistency(db, document_id: uuid.UUID, analysis) -> int:
    """Replace this document's issues with the current analysis.

    Human decisions survive: an issue a reviewer accepted or resolved keeps
    that status if the same issue reappears.
    """
    from app.models import ConsistencyIssue

    def identity(kind: str, fact_id, expected: str | None, observed: dict) -> tuple:
        """Stable identity for an issue across re-verification runs.

        An unsourced figure has no fact and no expected value, so it has to be
        identified by what was observed instead. Getting this wrong silently
        discards a reviewer's decision.
        """
        if kind == "unsourced_number":
            return (kind, tuple(sorted((observed or {}).items())))
        return (kind, str(fact_id), expected)

    existing = list(
        await db.scalars(
            select(ConsistencyIssue).where(ConsistencyIssue.document_id == document_id)
        )
    )
    decided = {
        identity(i.kind, i.fact_id, i.expected_value, i.observed): (i.status, i.note)
        for i in existing
        if i.status != "open"
    }
    await db.execute(delete(ConsistencyIssue).where(ConsistencyIssue.document_id == document_id))

    high = 0
    for row in analysis.mismatches:
        observed = {c.output_id: c.stated for c in row.cells if c.stated is not None}
        status, note = decided.get(
            identity("value_mismatch", row.fact_id, row.expected, observed), ("open", None)
        )
        if status == "open":
            high += 1
        db.add(
            ConsistencyIssue(
                document_id=document_id,
                kind="value_mismatch",
                fact_id=uuid.UUID(row.fact_id),
                severity="high",
                expected_value=row.expected,
                observed=observed,
                status=status,
                note=note,
            )
        )

    for item in analysis.unsourced:
        observed = {item.output_id: item.value}
        status, note = decided.get(
            identity("unsourced_number", None, None, observed), ("open", None)
        )
        db.add(
            ConsistencyIssue(
                document_id=document_id,
                kind="unsourced_number",
                fact_id=None,
                severity="medium",
                expected_value=None,
                observed=observed,
                status=status,
                note=note or item.snippet,
            )
        )

    await db.commit()
    return high


async def verify_output(output_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Run both verification layers over one output.

    Layer 1 is document-wide by nature: consistency is a property of the set of
    outputs, not of any single one, so verifying one recomputes the matrix.
    """
    from sqlalchemy.orm import selectinload

    from app.models import ClaimEvidence, Fact, FactSheet, Output, OutputClaim
    from app.schemas.content_ir import ContentIR
    from app.services.retrieval.search import search as retrieval_search
    from app.services.verification.atomizer import atomize
    from app.services.verification.claims import (
        ClaimResult,
        EvidenceRef,
        evidence_fingerprint,
        gather_evidence,
        verify_prepared,
    )
    from app.services.verification.consistency import analyze
    from app.services.verification.scoring import trust_score

    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        output = await db.get(Output, output_id)
        if job is None or output is None:
            log.error("verify: job %s or output %s vanished", job_id, output_id)
            return

        try:
            await mark(db, job, status="running", stage="loading", progress=0.05)

            sheet = await db.scalar(
                select(FactSheet)
                .where(FactSheet.id == output.fact_sheet_id)
                .options(selectinload(FactSheet.facts).selectinload(Fact.evidence))
            )
            if sheet is None:
                raise RuntimeError("The fact sheet this output was generated from is gone.")

            facts = {str(f.id): f for f in sheet.facts}
            blocks = {
                b.id: b
                for b in await db.scalars(
                    select(DocumentBlock).where(DocumentBlock.document_id == output.document_id)
                )
            }

            # --- Layer 1: deterministic, document-wide ---------------------
            await mark(db, job, stage="checking consistency", progress=0.2)
            siblings = list(
                await db.scalars(select(Output).where(Output.document_id == output.document_id))
            )
            analysis = analyze(
                list(sheet.facts),
                [(str(o.id), ContentIR.model_validate(o.content_ir)) for o in siblings],
            )
            high_issues = await _persist_consistency(db, output.document_id, analysis)
            mine = sum(
                1
                for row in analysis.mismatches
                for cell in row.cells
                if cell.output_id == str(output.id) and cell.agrees is False
            )

            # --- Layer 2: claim adjudication -------------------------------
            await mark(db, job, stage="verifying claims", progress=0.4)
            ir = ContentIR.model_validate(output.content_ir)
            claims = atomize(ir)

            async def evidence_for(claim):
                refs: list[EvidenceRef] = []
                seen: set[uuid.UUID] = set()
                for fid in claim.fact_ids:
                    fact = facts.get(fid)
                    if fact is None:
                        continue
                    for ev in fact.evidence:
                        block = blocks.get(ev.block_id)
                        if block is None or block.id in seen:
                            continue
                        seen.add(block.id)
                        refs.append(
                            EvidenceRef(
                                block_id=block.id,
                                text=block.text,
                                page_no=block.page_no,
                                section_path=block.section_path,
                            )
                        )
                if refs:
                    return refs
                # Uncited claims still get a hearing rather than an automatic fail.
                try:
                    for hit in await retrieval_search(output.document_id, claim.text, limit=3):
                        for bid in hit.block_ids:
                            block = blocks.get(bid)
                            if block is None or block.id in seen:
                                continue
                            seen.add(block.id)
                            refs.append(
                                EvidenceRef(
                                    block_id=block.id,
                                    text=block.text,
                                    page_no=block.page_no,
                                    section_path=block.section_path,
                                    similarity=hit.score,
                                )
                            )
                except Exception:  # noqa: BLE001 - retrieval is a bonus, not a requirement
                    log.warning("retrieval fallback failed for a claim", exc_info=True)
                return refs

            prepared = await gather_evidence(claims, evidence_for)

            # Reuse verdicts for claims whose text and evidence are unchanged,
            # so re-verifying after a small edit costs almost nothing.
            cached: dict[str, OutputClaim] = {}
            for prior in await db.scalars(
                select(OutputClaim).where(OutputClaim.output_id == output.id)
            ):
                prior_blocks = list(
                    await db.scalars(
                        select(ClaimEvidence.block_id).where(ClaimEvidence.claim_id == prior.id)
                    )
                )
                if prior.verdict is None:
                    continue
                key = evidence_fingerprint(
                    prior.text,
                    [
                        EvidenceRef(block_id=b, text="", page_no=0, section_path="")
                        for b in prior_blocks
                    ],
                )
                cached[key] = prior

            todo, reused = [], []
            for claim, evidence in prepared:
                hit = cached.get(evidence_fingerprint(claim.text, evidence))
                if hit is None:
                    todo.append((claim, evidence))
                else:
                    reused.append(
                        ClaimResult(
                            claim=claim,
                            verdict=hit.verdict,
                            score=hit.score or 0.0,
                            rationale=hit.rationale or "",
                            evidence=evidence,
                        )
                    )

            results = reused + await verify_prepared(todo)

            await mark(db, job, stage="scoring", progress=0.85)
            await db.execute(delete(OutputClaim).where(OutputClaim.output_id == output.id))
            for result in results:
                row = OutputClaim(
                    output_id=output.id,
                    node_id=result.claim.node_id,
                    text=result.claim.text,
                    cited_fact_ids=[uuid.UUID(f) for f in result.claim.fact_ids],
                    verdict=result.verdict,
                    score=result.score,
                    rationale=result.rationale,
                )
                db.add(row)
                await db.flush()
                db.add_all(
                    ClaimEvidence(claim_id=row.id, block_id=e.block_id, similarity=e.similarity)
                    for e in result.evidence
                )

            output.trust_score = trust_score([r.verdict for r in results], mine)
            output.status = "verified"
            output.verified_at = datetime.now(UTC)
            await db.commit()

            await mark(
                db,
                job,
                status="succeeded",
                stage="done",
                progress=1.0,
                result={
                    "claims": len(results),
                    "trust_score": output.trust_score,
                    "mismatches_in_this_output": mine,
                    "open_high_issues": high_issues,
                    "unsourced": len(analysis.unsourced),
                    "claims_reused_from_cache": len(reused),
                },
            )

        except Exception as exc:  # noqa: BLE001 - surfaced through the job row
            log.exception("verification failed for output %s", output_id)
            await db.rollback()
            await mark(db, job, status="failed", stage="failed", error=str(exc))


# --------------------------------------------------------------------------
# Video render: blocking MP4 render job
# --------------------------------------------------------------------------


async def render_video_output(output_id: uuid.UUID, job_id: uuid.UUID) -> None:
    """Render an approved/verified video output to MP4 and persist it.

    The render is CPU-bound and can take 30–90 seconds depending on the number
    of scenes and the host hardware.  Progress is reported as stage updates so
    the frontend can show a spinner or progress bar.
    """
    import functools

    import anyio

    from app.models import Export, Output
    from app.schemas.content_ir import ContentIR
    from app.services.rendering.video_renderer import render as video_render

    async with SessionLocal() as db:
        job = await db.get(Job, job_id)
        output = await db.get(Output, output_id)
        if job is None or output is None:
            log.error("render_video: job %s or output %s vanished", job_id, output_id)
            return

        try:
            await mark(db, job, status="running", stage="loading storyboard", progress=0.05)

            ir = ContentIR.model_validate(output.content_ir)
            scenes = [n for n in ir.nodes if n.kind == "scene" and (n.text or "").strip()]
            if not scenes:
                raise RuntimeError("No scene nodes found — cannot render video.")

            orientation = (output.controls or {}).get("format", {}).get("screen", "wide")
            language = output.language or "en"

            await mark(
                db, job,
                stage=f"rendering {len(scenes)} scenes (TTS + visuals + video encode)",
                progress=0.10,
            )

            # Run the blocking render in a thread so the event loop stays free.
            mp4_bytes: bytes = await anyio.to_thread.run_sync(
                functools.partial(video_render, ir, orientation=orientation, language=language),
                cancellable=True,
            )

            await mark(db, job, stage="saving video file", progress=0.90)

            filename = (
                f"video_{output.audience}_{output.language}_v{output.version}.mp4"
            )
            uri = await anyio.to_thread.run_sync(
                storage.put, f"exports/{output.id}/{filename}", mp4_bytes
            )
            db.add(
                Export(
                    output_id=output.id,
                    format="mp4",
                    storage_uri=uri,
                    size_bytes=len(mp4_bytes),
                )
            )
            await db.commit()

            await mark(
                db,
                job,
                status="succeeded",
                stage="done",
                progress=1.0,
                result={
                    "storage_uri": uri,
                    "size_bytes": len(mp4_bytes),
                    "scenes": len(scenes),
                    "orientation": orientation,
                    "language": language,
                },
            )
            log.info(
                "render_video: MP4 ready for output %s — %.1f MB",
                output_id, len(mp4_bytes) / 1e6,
            )

        except Exception as exc:  # noqa: BLE001
            log.exception("render_video failed for output %s", output_id)
            await db.rollback()
            await mark(db, job, status="failed", stage="failed", error=str(exc))
