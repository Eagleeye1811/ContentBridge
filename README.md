# ContentBridge

**SIH 2026 · PS 26154 — Gen AI Platform for Automated Content Transformation**

Upload an authoritative document. Get seven verified outputs — advisory, deck, executive
summary, official email, social post, press release, report — in English, Hindi and Marathi,
each one traceable back to a page and a line of the source.

## The core idea

Every output type walks **one** pipeline. There is no separate AI pipeline per format.

```
Upload ──▶ Parse ──▶ Blocks (page, section, bbox)       ── traceability anchors
                         │
                         ├──▶ Chunk + Embed ──▶ Qdrant  ── retrieval
                         │
                         └──▶ Fact Extraction ──▶ FACT SHEET   ◀── the Source of Truth
                                                     │
             ┌───────────────────────────────────────┴──────────────────────────┐
             │  GENERATOR — FactSheet + FormatSpec + Audience + Language         │
             │  emits ContentIR: nodes, each carrying the fact_ids it used       │
             └───────────────────────────────────────┬──────────────────────────┘
                                                     │
                                   VERIFY ───────────┤  L1 numeric consistency (deterministic)
                                                     │  L2 claim verification (LLM vs evidence)
                                                     │
                             REVIEW / EDIT / APPROVE ┤
                                                     │
                                  RENDER ────────────┴──▶ .pptx .docx .md .html .txt
```

Two intermediate representations carry the whole design:

- **FactSheet** — normalized facts, each born with `evidence: [block_id]`. Numbers are
  canonicalized exactly once, so consistency is a comparison against one value rather than a
  seven-way diff.
- **ContentIR** — a format-neutral node tree. The LLM never emits PPTX or DOCX; renderers are
  pure functions of ContentIR. It is also the unit a human edits and the unit verification scores.

Adding an eighth output type is a config file, not a pipeline.

## Stack

| Layer | Choice |
|---|---|
| Frontend | React 19 · Vite 6 · TypeScript · Tailwind 4 |
| Backend | Python 3.12 · FastAPI · SQLAlchemy 2 (async) · Alembic |
| Database | PostgreSQL 16 |
| Vectors | Qdrant |
| Embeddings | fastembed (local — retrieval keeps working with no network) |
| LLM | Gemini or any OpenAI-compatible endpoint, selected by env |
| Documents | PyMuPDF · python-docx · python-pptx |

## Quick start

```bash
cp .env.example .env          # then set GEMINI_API_KEY and a fresh JWT_SECRET
docker compose up --build     # postgres, qdrant, api, web
docker compose exec api python -m app.seed
```

- Web: http://localhost:5173
- API docs: http://localhost:8000/docs
- Postgres: `localhost:5544` (host port 5544 to avoid colliding with a local Postgres)

Demo accounts (password `contentbridge`):

| Email | Role |
|---|---|
| `editor@contentbridge.io` | editor |
| `approver@contentbridge.io` | approver |

### Running on the host instead

```bash
docker compose up -d postgres qdrant

cd backend
uv venv --python 3.12 && uv pip install -e ".[dev]"
.venv/bin/alembic upgrade head
.venv/bin/python -m app.seed
.venv/bin/uvicorn app.main:app --reload

cd ../frontend && npm install && npm run dev
```

Generate a JWT secret with:
`python3 -c "import secrets; print(secrets.token_urlsafe(48))"`

## Layout

```
backend/app/
  api/            routers: auth, health (+ documents, jobs, outputs, verification, exports)
  models.py       15 tables; document_blocks.id is THE traceability primitive
  schemas/        pydantic contracts (FactSheet, ContentIR, Claim, Verdict)
  services/
    ingestion/    PDF/DOCX/PPTX -> Block[] with page, section, bbox
    indexing/     chunking, embeddings, Qdrant
    retrieval/    search that always returns provenance, never bare text
    sot/          fact extraction + normalization
    generation/   one generator; formats/ and audiences/ are config
    verification/ consistency.py (deterministic) + claims.py (LLM)
    rendering/    ContentIR -> pptx/docx/md/html
    llm/          provider abstraction
  pipeline/       the one pipeline
frontend/src/
  pages/          Documents, FactSheet, Studio, Review, Consistency, Approvals, Settings
  components/     DocumentViewer, EvidencePanel, CitationChip, VerdictBadge, ConsistencyMatrix
```

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Scaffold, schema, auth, health | **done** |
| 1 | Ingestion + traceability | next |
| 2 | RAG + Source of Truth | |
| 3 | One pipeline, Advisory + Summary | |
| 4 | Verification + consistency matrix | |
| 5 | Remaining outputs + pptx/docx renderers | |
| 6 | Audience profiles + Hindi/Marathi | |
| 7 | Review, approval gate, demo polish | |

Full architecture plan: `~/.claude/plans/async-mixing-storm.md`
