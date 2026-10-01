# ContentBridge

**SIH 2026 · PS 26154 — Gen AI Platform for Automated Content Transformation**

Add an authoritative source — a document, an image or pasted text. Get nine verified outputs —
advisory, deck, executive summary, official email, LinkedIn post, press release, report,
infographic package and video package — in English, Hindi and Marathi,
each one traceable back to a page and a line of the source.

## The core idea

Every output type walks **one** pipeline. There is no separate AI pipeline per format.

```
Source ──▶ Parse ──▶ Blocks (page, section, bbox)       ── traceability anchors
(PDF · DOCX · PPTX · text · image/OCR)
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

Adding another output type is a config file, not a pipeline.

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
  pages/          Sources, OutputReview, Approvals, Login
    workspace/    one source: Document, Key facts, one section per format, Numbers check
  components/     CreateForm (per-format options), OutputList, AccuracyPanel, ApprovalPanel,
                  DownloadPanel, ContentIRView, ContentEditor, DocumentViewer, ui
```

## Status

| Phase | Scope | State |
|---|---|---|
| 0 | Scaffold, schema, auth, health | **done** |
| 1 | Ingestion + traceability | **done** |
| 2 | RAG + Source of Truth | **done** |
| 3 | One pipeline, Advisory + Summary | **done** |
| 4 | Verification + consistency matrix | **done** |
| 5 | Remaining outputs + pptx/docx renderers | **done** |
| 6 | Audience profiles + Hindi/Marathi | **done** |
| 7 | Review, approval gate, demo polish | **done** |
| 8 | PS 26154 alignment: controls, LinkedIn/infographic/video, text + image sources | **done** |

### What the PS 26154 alignment gives you

Everything rides the existing spine; no new pipeline.

- **One section per output format.** Each has its own options declared in its
  FormatSpec (`options=`: slide count, video length, infographic layout, ...)
  and lists everything created in that format. Options become prompt lines and
  node budgets via `apply_options`, so the generator is unchanged.
- **Seven controls** — output type, target audience, language, tone,
  detail level, communication objective, content style. Tone, detail,
  objective and style are prompt configuration in
  `services/generation/controls.py`, like audiences: they change wording and
  emphasis, never facts, and the generator's hard rules still apply. Each
  output stores the controls it was made with, so regenerating reproduces them.
- **LinkedIn Post** replaces the generic social post (`social` still resolves
  for outputs stored before the rename).
- **Infographic Package** — headline, `panel` nodes (data points, caption and a
  visual recommendation per panel), optional takeaway callout. HTML export lays
  the panels out as a grid.
- **Video Package** — `scene` nodes carrying narration, on-screen text and
  visual direction: together the script and the storyboard. **Subtitles (.srt)
  are rendered from the narration**, never written separately, so they cannot
  say anything verification did not check. No video file is produced.
- Visual direction (`notes` on panels and scenes) is not judged as a claim;
  narration, captions and data points are. Any figure that strays into visual
  notes is still caught by the consistency check.
- **Text and image sources.** Pasted text and `.txt`/`.md` files become blocks
  with section paths. Images (`.png`/`.jpg`) are read by Tesseract OCR, and
  every paragraph keeps its box on the image, so the source viewer highlights
  it just like a PDF. Both then go through indexing → Fact Sheet → generation
  unchanged. On the host, install Tesseract (`brew install tesseract`); the
  Docker image includes it with Hindi and Marathi data.

### What Phase 7 gives you

The human step, with teeth.

```
Generate -> Verify -> Submit -> Approve -> Export
```

- **The gate refuses, and says why.** An output with a contradicted claim or an
  unresolved high-severity mismatch cannot be approved; the reason is returned
  rather than implied. An unverified output is blocked too, since it has no
  claims to judge and would otherwise pass vacuously.
- **Separation of duties.** Only an `approver` may approve, and not even their
  own work can skip the queue. An approver can see anything submitted for
  review, which is what makes two roles mean anything.
- **Rejection always stays available.** Refusing bad work is never gated on the
  work being good — but a rejection needs a reason the editor can act on.
- **Editing invalidates verification completely.** The trust score, the
  `verified_at` stamp and the stored claims are all cleared, so nothing can be
  approved on evidence describing text that no longer exists.
- **Approved outputs are locked.** Regenerate to make a new version.
- Every action lands in an audit trail: who, what, when.

The approval rules live in `app/services/review/policy.py` as pure functions,
tested exhaustively across every state and role rather than sampled.

### Demo

```bash
make demo        # or: python scripts/demo.py --types advisory,summary --languages en,hi
```

Upload → facts → generate → verify → consistency → submit → approve → export →
audit, printed step by step. It exits non-zero if any step fails, so it doubles
as an integration check.

### What Phase 6 gives you

**7 formats x 5 audiences x 3 languages = 105 combinations, one generator.**

Audiences change register and emphasis only. Every profile carries the same
closing instruction — never drop a figure, soften a finding, or add
reassurance the facts do not support — and a test asserts it is there.

Multilingual is more than a prompt line. Four things had to be real:

- **Digits.** `३७` and `37` canonicalize to the same value, so a Hindi output
  agrees with an English source instead of looking like a mismatch. A wrong
  figure is still caught: `४२` against a source of `37` is flagged.
- **Dates.** Devanagari month names parse, so `११ मार्च २०२६` and
  `11 March 2026` both reduce to `2026-03-11`.
- **Sentences.** Devanagari ends a sentence with a danda (`।`), not a full
  stop. Without handling it, a Hindi paragraph arrives as one unverifiable
  claim.
- **Script.** Asking for Marathi and silently receiving English is a failure a
  reviewer would have to catch by eye, so generation checks the script and
  refuses rather than shipping English under a Marathi label.

The claim judge is told the claim and its evidence may be in different
languages, and to compare figures by value rather than by spelling.

### What Phase 5 gives you

All seven output types, and real files.

| Output | ContentIR shape | Exports as |
|---|---|---|
| Advisory | heading, paragraph, bullets, callout | docx, md, html, txt |
| Presentation | `slide` only | **pptx**, md, html |
| Executive Summary | heading, paragraph, bullets | docx, md, html |
| Official Email | heading, paragraph, bullets | txt, html, md |
| LinkedIn Post | `post` only | txt, md |
| Press Release | heading, paragraph, quote | docx, md, html |
| Report | heading, paragraph, bullets, table | docx, md, html |

Every one of them is the same `generate()` call with a different FormatSpec.
A test asserts that, and another asserts that every renderer a spec promises
actually exists.

**Decks are drawn in code, not filled into a template.** A `.potx` would be a
binary asset nobody in the repo can diff or edit; drawing each slide gives
exact control over spacing and keeps the deck's look reviewable. Bullets are
capped per slide and long detail goes to speaker notes, because a slide is a
prompt for a speaker rather than a document.

**Word documents use Word's own styles** (Title, Heading, List Bullet, Table
Grid), so they open looking normal and stay editable.

Any export can carry a **Sources appendix** listing every fact it used with
page and section. Renderers stay pure: they are handed resolved citation
strings, they never look anything up.

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
