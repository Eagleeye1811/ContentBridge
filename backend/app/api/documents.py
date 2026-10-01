from __future__ import annotations

import uuid

import anyio
from fastapi import APIRouter, BackgroundTasks, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy import delete as sql_delete
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.config import settings
from app.models import AuditLog, Document, DocumentBlock, Export, Job, Output
from app.pipeline.stages import process_document
from app.schemas.documents import BlockOut, DocumentOut, JobOut, UploadResponse
from app.services.indexing.qdrant_store import VectorStore
from app.services.ingestion import SUPPORTED, UnsupportedFormat, extension_of, mime_for, pdf_parser
from app.services.storage import sha256_hex, storage

router = APIRouter(prefix="/documents", tags=["documents"])


async def _owned(db: DbSession, user: CurrentUser, document_id: uuid.UUID) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or doc.owner_id != user.id:
        raise HTTPException(404, "Document not found")
    return doc


@router.post("", response_model=UploadResponse, status_code=201)
async def upload(
    db: DbSession,
    user: CurrentUser,
    background: BackgroundTasks,
    file: UploadFile = File(...),
) -> UploadResponse:
    filename = file.filename or "upload"
    if extension_of(filename) not in SUPPORTED:
        raise HTTPException(415, f"Unsupported file type. Allowed: {', '.join(SUPPORTED)}")

    data = await file.read()
    if not data:
        raise HTTPException(400, "Uploaded file is empty")
    limit = settings.max_upload_mb * 1024 * 1024
    if len(data) > limit:
        raise HTTPException(413, f"File exceeds the {settings.max_upload_mb} MB limit")

    try:
        mime = mime_for(filename)
    except UnsupportedFormat as exc:
        raise HTTPException(415, str(exc)) from exc

    document_id = uuid.uuid4()
    key = f"documents/{document_id}{extension_of(filename)}"
    uri = await anyio.to_thread.run_sync(storage.put, key, data)

    document = Document(
        id=document_id,
        owner_id=user.id,
        filename=filename,
        mime=mime,
        storage_uri=uri,
        sha256=sha256_hex(data),
        size_bytes=len(data),
        status="uploaded",
    )
    job = Job(document_id=document_id, kind="ingest", status="queued", stage="queued")
    db.add_all([document, job])
    db.add(
        AuditLog(
            actor_id=user.id,
            entity="document",
            entity_id=document_id,
            action="upload",
            payload={"filename": filename, "size_bytes": len(data)},
        )
    )
    # Commit before scheduling: the background task opens its own session and
    # would not see these rows if we left the commit to dependency teardown.
    await db.commit()

    background.add_task(process_document, document_id, job.id)

    return UploadResponse(
        document=DocumentOut.model_validate(document),
        job=JobOut.model_validate(job),
    )


@router.get("", response_model=list[DocumentOut])
async def list_documents(db: DbSession, user: CurrentUser) -> list[DocumentOut]:
    rows = await db.scalars(
        select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
    )
    return [DocumentOut.model_validate(d) for d in rows]


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> DocumentOut:
    return DocumentOut.model_validate(await _owned(db, user, document_id))


@router.delete("/{document_id}", status_code=204)
async def delete_document(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> Response:
    """Remove a source and everything made from it: blocks, facts, outputs,
    exported files and its search index. The audit trail is kept."""
    doc = await _owned(db, user, document_id)

    export_uris = list(
        await db.scalars(
            select(Export.storage_uri)
            .join(Output, Output.id == Export.output_id)
            .where(Output.document_id == document_id)
        )
    )

    store = VectorStore()
    try:
        await store.delete_document(document_id)
    finally:
        await store.close()

    for uri in [doc.storage_uri, *export_uris]:
        try:
            await anyio.to_thread.run_sync(storage.delete, uri)
        except (FileNotFoundError, OSError):
            pass  # already gone; the database row is what matters

    db.add(
        AuditLog(
            actor_id=user.id,
            entity="document",
            entity_id=document_id,
            action="delete",
            payload={"filename": doc.filename},
        )
    )
    # Blocks, chunks, fact sheets, outputs, claims and exports cascade in the
    # database; a bulk delete avoids loading them all into the session first.
    await db.execute(sql_delete(Document).where(Document.id == document_id))
    await db.commit()
    return Response(status_code=204)


@router.get("/{document_id}/blocks", response_model=list[BlockOut])
async def list_blocks(
    document_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    page: int | None = Query(None, ge=1, description="Filter to a single page"),
) -> list[BlockOut]:
    await _owned(db, user, document_id)
    stmt = select(DocumentBlock).where(DocumentBlock.document_id == document_id)
    if page is not None:
        stmt = stmt.where(DocumentBlock.page_no == page)
    rows = await db.scalars(stmt.order_by(DocumentBlock.order_idx))
    return [BlockOut.model_validate(b) for b in rows]


@router.get("/{document_id}/file")
async def download(document_id: uuid.UUID, db: DbSession, user: CurrentUser) -> StreamingResponse:
    doc = await _owned(db, user, document_id)
    data = await anyio.to_thread.run_sync(storage.get, doc.storage_uri)
    return StreamingResponse(
        iter([data]),
        media_type=doc.mime,
        headers={"Content-Disposition": f'inline; filename="{doc.filename}"'},
    )


@router.get(
    "/{document_id}/pages/{page_no}/image",
    responses={200: {"content": {"image/png": {}}}},
)
async def page_image(
    document_id: uuid.UUID,
    page_no: int,
    db: DbSession,
    user: CurrentUser,
    dpi: int = Query(110, ge=50, le=300),
) -> Response:
    """Rasterized page for the traceability viewer. PDF pages are rendered; an
    image source is its own single page. DOCX, PPTX and text have no fixed page
    geometry, so the UI shows a structured text view."""
    doc = await _owned(db, user, document_id)
    if doc.mime.startswith("image/"):
        if page_no != 1:
            raise HTTPException(404, "Image sources have a single page")
        data = await anyio.to_thread.run_sync(storage.get, doc.storage_uri)
        return Response(
            content=data, media_type=doc.mime, headers={"Cache-Control": "private, max-age=3600"}
        )
    if doc.mime != "application/pdf":
        raise HTTPException(415, "Page images are only available for PDF and image sources")

    data = await anyio.to_thread.run_sync(storage.get, doc.storage_uri)
    try:
        png = await anyio.to_thread.run_sync(pdf_parser.render_page_png, data, page_no, dpi)
    except IndexError as exc:
        raise HTTPException(404, str(exc)) from exc

    return Response(
        content=png, media_type="image/png", headers={"Cache-Control": "private, max-age=3600"}
    )
