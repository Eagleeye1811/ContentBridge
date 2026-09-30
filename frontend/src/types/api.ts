export type Role = 'editor' | 'approver'

export interface User {
  id: string
  email: string
  name: string
  role: Role
  created_at: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: User
}

export interface HealthResponse {
  status: string
  database: boolean
  env: string
  llm_provider: string
  embedding_provider: string
}

export type DocumentStatus =
  | 'uploaded'
  | 'parsing'
  | 'parsed'
  | 'indexing'
  | 'indexed'
  | 'extracting'
  | 'ready'
  | 'failed'

export interface Doc {
  id: string
  filename: string
  mime: string
  size_bytes: number
  page_count: number
  source_lang: string
  status: DocumentStatus
  error: string | null
  created_at: string
}

/** Geometry in PDF points. The viewer converts these to page percentages. */
export interface BBox {
  x0: number
  y0: number
  x1: number
  y1: number
  page_width: number
  page_height: number
}

export interface Block {
  id: string
  page_no: number
  section_path: string
  order_idx: number
  block_type: 'heading' | 'paragraph' | 'list_item' | 'table' | 'caption' | 'footer' | 'slide_text'
  text: string
  bbox: BBox | null
}

export interface Job {
  id: string
  document_id: string
  kind: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  stage: string
  progress: number
  error: string | null
  created_at: string
  finished_at: string | null
}

export interface UploadResponse {
  document: Doc
  job: Job
}

export interface Evidence {
  block_id: string
  page_no: number
  section_path: string
  quote: string
  char_start: number | null
  char_end: number | null
  bbox: BBox | null
}

export type FactType = 'metric' | 'date' | 'entity' | 'finding' | 'recommendation' | 'risk'

export interface Fact {
  id: string
  key: string
  type: FactType
  statement: string
  canonical_value: string | null
  unit: string | null
  confidence: number
  edited_by_human: boolean
  evidence: Evidence[]
}

export interface FactSheet {
  id: string
  document_id: string
  version: number
  model: string
  created_at: string
  facts: Fact[]
}

export interface FactUpdate {
  statement?: string
  canonical_value?: string | null
  unit?: string | null
}

export interface SearchHit {
  text: string
  block_ids: string[]
  page_no: number
  section_path: string
  score: number
}

export type NodeKind =
  | 'heading'
  | 'paragraph'
  | 'bullets'
  | 'slide'
  | 'table'
  | 'callout'
  | 'quote'
  | 'post'

export interface IRNode {
  id: string
  kind: NodeKind
  text?: string | null
  items?: string[] | null
  level?: number | null
  title?: string | null
  notes?: string | null
  rows?: string[][] | null
  severity?: 'info' | 'low' | 'medium' | 'high' | 'critical' | null
  fact_ids: string[]
}

export interface ContentIR {
  title: string
  nodes: IRNode[]
}

export interface Output {
  id: string
  document_id: string
  fact_sheet_id: string
  type: string
  audience: string
  language: string
  status: 'draft' | 'verified' | 'in_review' | 'approved' | 'rejected' | 'exported'
  trust_score: number | null
  version: number
  model: string
  created_at: string
  title: string
  renderers: string[]
}

export interface OutputDetail extends Output {
  content_ir: ContentIR
  facts: Fact[]
}

export interface FormatInfo {
  key: string
  name: string
  description: string
  renderers: string[]
}

export interface Catalog {
  formats: FormatInfo[]
  audiences: { key: string; name: string }[]
  languages: Record<string, string>
}

export interface GenerateRequest {
  types: string[]
  audience: string
  languages: string[]
}

export type VerdictKind = 'supported' | 'partial' | 'unsupported' | 'contradicted'

export interface ClaimEvidence {
  block_id: string
  page_no: number
  section_path: string
  quote: string
  similarity: number | null
}

export interface Claim {
  id: string
  node_id: string
  text: string
  cited_fact_ids: string[]
  verdict: VerdictKind | null
  score: number | null
  rationale: string | null
  evidence: ClaimEvidence[]
}

export interface VerificationSummary {
  output_id: string
  status: string
  trust_score: number | null
  verified_at: string | null
  counts: Partial<Record<VerdictKind | 'unverified', number>>
  blocking_reasons: string[]
  claims: Claim[]
}

export interface MatrixCell {
  output_id: string
  stated: string | null
  agrees: boolean | null
  snippet: string
}

export interface MatrixRow {
  fact_id: string
  key: string
  statement: string
  expected: string | null
  unit: string | null
  has_mismatch: boolean
  cells: MatrixCell[]
}

export interface Unsourced {
  output_id: string
  value: string
  snippet: string
}

export interface Issue {
  id: string
  kind: 'value_mismatch' | 'unsourced_number'
  fact_id: string | null
  severity: 'low' | 'medium' | 'high'
  expected_value: string | null
  observed: Record<string, string>
  status: 'open' | 'resolved' | 'accepted'
  note: string | null
  created_at: string
}

export interface OutputColumn {
  id: string
  type: string
  audience: string
  language: string
  version: number
  trust_score: number | null
}

export interface ConsistencyReport {
  document_id: string
  outputs: OutputColumn[]
  rows: MatrixRow[]
  unsourced: Unsourced[]
  issues: Issue[]
}
