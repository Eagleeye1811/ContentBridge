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
| 1 | Ingestion + traceability | **done** |
| 2 | RAG + Source of Truth | **done** |
| 3 | One pipeline, Advisory + Summary | **done** |
| 4 | Verification + consistency matrix | **done** |
| 5 | Remaining outputs + pptx/docx renderers | next |
| 6 | Audience profiles + Hindi/Marathi | |
| 7 | Review, approval gate, demo polish | |

### What Phase 4 gives you

Two verification layers, deliberately split by reliability.

**Layer 1 — deterministic consistency.** No model, no network, instant. Because
every output cites the same fact ids and values were canonicalized at
extraction, checking agreement is a string comparison. The facts x outputs
matrix falls out of it:

```
fact                  source   advisory   ppt     summary
credentials_compromised  37       37 OK    37 OK    42 MISMATCH
incident_date      2026-03-11     OK       OK       OK
```

It is tuned to stay quiet. A figure it cannot attribute unambiguously is not
reported: reference codes (`CB/IR/2026/0412`), clock times (`02:14`), timezone
offsets and version strings are skipped outright, a value hidden inside a date
counts as present, and a mismatch is only attributed when exactly one figure in
the node is unaccounted for. A false alarm in front of judges costs more than
a miss.

Figures appearing in an output but in no fact are reported separately as
**unsourced** — the system flags them and never rewrites them.

**Layer 2 — claim adjudication.** Claims are atomized per node and judged
against the blocks they cite, with retrieval as a fallback so an uncited claim
still gets a hearing. Verdicts are supported / partial / unsupported /
contradicted. Verdicts are cached on `hash(claim + evidence)`, so re-verifying
after a small edit is nearly free.

**Trust score and the approval gate.** A weighted blend of verdicts, penalized
per open high-severity issue. Any contradicted claim blocks approval, and the
reason is shown rather than implied.

### What Phase 3 gives you

The shared spine is real. `generate()` is one function; Advisory and Executive
Summary differ only by a `FormatSpec` — allowed node kinds, a prompt fragment,
a node budget. Adding an output type is a config file.

- **ContentIR** is the format-neutral node tree the model emits. It never emits
  Markdown, DOCX or PPTX; renderers are pure functions of ContentIR, which is
  what makes export reproducible and editing uniform.
- **Facts are labelled `f0..fN`** in the prompt, exactly as blocks are during
  extraction. The model never sees a real UUID, so it cannot invent a valid
  citation.
- **Three hard rules are enforced in code, not prose.** Disallowed node kinds,
  invented citations and uncited non-heading nodes are rejected and retried
  once with the violation named. Anything still wrong is dropped — an
  unattributable claim never reaches a reviewer.
- **Reviewers edit ContentIR**, not rendered text, so every export stays
  consistent. Any edit clears the verification state.

```
POST /documents/{id}/outputs  {"types":["advisory","summary"],
                               "audience":"officer","languages":["en"]}
   -> one job, N outputs, all through the same generator
GET  /outputs/{id}            -> ContentIR + every cited fact, inline
GET  /outputs/{id}/export?format=markdown
```

### What Phase 2 gives you

Ingestion now continues into retrieval and a Source of Truth:

- **Chunking** groups consecutive blocks but never crosses a section boundary,
  and records the block ids it was built from.
- **Embeddings** run locally through fastembed, so retrieval keeps working with
  no network and no API key.
- **Qdrant** payloads carry `document_id`, `block_ids`, `page_no` and
  `section_path`, so a retrieval hit is citable on its own.
- **Fact extraction** labels blocks `b0..bN` in the prompt and requires every
  fact to cite those labels. Facts citing anything else are **dropped, not
  repaired** — this is the guard against hallucinated citations, and the real
  UUIDs are never shown to the model.
- **Normalization** canonicalizes values once, at birth: `18.4 lakh` becomes
  `1840000`, `११ मार्च` digits become ASCII, `11/03/2026` becomes `2026-03-11`.
  Phase 4 compares against `canonical_value` instead of diffing documents.
- **Facts are editable.** Correcting the Source of Truth is the highest-leverage
  human action in the system, so `PATCH /facts/{id}` exists from day one.

Without an LLM key the pipeline still parses, chunks, embeds and indexes; the
document lands at `indexed` and stays fully searchable. Set
`LLM_PROVIDER=stub` for an offline dry run that exercises the real extraction
code path with no network.

### What Phase 1 gives you

Upload a PDF, DOCX or PPTX and every extracted block records its page, section
path and — for PDF and PPTX — its bounding box. Open a document and clicking any
block highlights it on the rendered page, and vice versa. That block id is what
facts, claims and citations will point at for the rest of the build.

Sample sources live in `samples/` (regenerate with
`backend/.venv/bin/python scripts/make_samples.py`).

## Testing

```bash
cd backend && .venv/bin/python -m pytest tests -q   # parsers, chunking,
                                                    # normalization, citation guard
cd frontend && npm run build                        # typecheck + build
```

Try retrieval directly:

```bash
curl -G "localhost:8000/documents/$DOC/search" \
  --data-urlencode "q=how many credentials were compromised" \
  -H "Authorization: Bearer $TOKEN"
```

Full architecture plan: `~/.claude/plans/async-mixing-storm.md`
