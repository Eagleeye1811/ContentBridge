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
