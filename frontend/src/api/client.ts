import { parseSseFrames } from '@/lib/sse'
import type {
  Block,
  Doc,
  Fact,
  FactSheet,
  FactUpdate,
  HealthResponse,
  Job,
  Catalog,
  ConsistencyReport,
  ContentIR,
  GenerateRequest,
  Output,
  OutputDetail,
  ApprovalState,
  AuditEntry,
  Issue,
  PendingOutput,
  SearchHit,
  TokenResponse,
  VerificationSummary,
  UploadResponse,
  User,
} from '@/types/api'

const BASE = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'
const TOKEN_KEY = 'contentbridge.token'

export const tokenStore = {
  get: () => localStorage.getItem(TOKEN_KEY),
  set: (t: string) => localStorage.setItem(TOKEN_KEY, t),
  clear: () => localStorage.removeItem(TOKEN_KEY),
}

export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message)
  }
}

function authHeader(): Record<string, string> {
  const token = tokenStore.get()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

async function failure(res: Response): Promise<ApiError> {
  let detail = res.statusText
  try {
    const body = await res.json()
    // FastAPI sends a string for HTTPException, an array for validation errors.
    detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
  } catch {
    /* keep statusText */
  }
  return new ApiError(res.status, detail)
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...authHeader(), ...init.headers },
  })
  if (!res.ok) throw await failure(res)
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T)
}

/** Fetch a protected binary endpoint as an object URL (an <img> cannot send headers). */
async function objectUrl(path: string): Promise<string> {
  const res = await fetch(`${BASE}${path}`, { headers: authHeader() })
  if (!res.ok) throw await failure(res)
  return URL.createObjectURL(await res.blob())
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  login: (email: string, password: string) =>
    request<TokenResponse>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: () => request<User>('/auth/me'),

  listDocuments: () => request<Doc[]>('/documents'),
  getDocument: (id: string) => request<Doc>(`/documents/${id}`),
  listBlocks: (id: string, page?: number) =>
    request<Block[]>(`/documents/${id}/blocks${page ? `?page=${page}` : ''}`),
  pageImageUrl: (id: string, page: number, dpi = 130) =>
    objectUrl(`/documents/${id}/pages/${page}/image?dpi=${dpi}`),

  uploadDocument: async (file: File): Promise<UploadResponse> => {
    const form = new FormData()
    form.append('file', file)
    // No Content-Type header: the browser must set the multipart boundary.
    const res = await fetch(`${BASE}/documents`, {
      method: 'POST',
      headers: authHeader(),
      body: form,
    })
    if (!res.ok) throw await failure(res)
    return (await res.json()) as UploadResponse
  },

  getFactSheet: (documentId: string) =>
    request<FactSheet>(`/documents/${documentId}/fact-sheet`),
  runExtraction: (documentId: string) =>
    request<Job>(`/documents/${documentId}/fact-sheet`, { method: 'POST' }),
  updateFact: (factId: string, patch: FactUpdate) =>
    request<Fact>(`/facts/${factId}`, { method: 'PATCH', body: JSON.stringify(patch) }),
  search: (documentId: string, q: string, limit = 8) =>
    request<SearchHit[]>(
      `/documents/${documentId}/search?q=${encodeURIComponent(q)}&limit=${limit}`,
    ),

  catalog: () => request<Catalog>('/catalog'),
  listOutputs: (documentId: string) => request<Output[]>(`/documents/${documentId}/outputs`),
  generate: (documentId: string, body: GenerateRequest) =>
    request<Job>(`/documents/${documentId}/outputs`, {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  getOutput: (id: string) => request<OutputDetail>(`/outputs/${id}`),
  updateOutput: (id: string, contentIr: ContentIR) =>
    request<OutputDetail>(`/outputs/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ content_ir: contentIr }),
    }),
  regenerate: (id: string) => request<Job>(`/outputs/${id}/regenerate`, { method: 'POST' }),
  exportUrl: (id: string, format: string, citations = false) =>
    objectUrl(`/outputs/${id}/export?format=${format}&citations=${citations}`),

  verifyOutput: (id: string) => request<Job>(`/outputs/${id}/verify`, { method: 'POST' }),
  getClaims: (id: string) => request<VerificationSummary>(`/outputs/${id}/claims`),
  consistency: (documentId: string) =>
    request<ConsistencyReport>(`/documents/${documentId}/consistency`),
  updateIssue: (issueId: string, status: string, note?: string) =>
    request<Issue>(`/consistency-issues/${issueId}`, {
      method: 'PATCH',
      body: JSON.stringify({ status, note }),
    }),

  approvalState: (id: string) => request<ApprovalState>(`/outputs/${id}/approval`),
  submitForReview: (id: string, note?: string) =>
    request<ApprovalState>(`/outputs/${id}/submit`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  approveOutput: (id: string, note?: string) =>
    request<ApprovalState>(`/outputs/${id}/approve`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  rejectOutput: (id: string, note: string) =>
    request<ApprovalState>(`/outputs/${id}/reject`, {
      method: 'POST',
      body: JSON.stringify({ note }),
    }),
  reviewQueue: () => request<PendingOutput[]>('/review-queue'),
  audit: (documentId: string) => request<AuditEntry[]>(`/documents/${documentId}/audit`),

  getJob: (id: string) => request<Job>(`/jobs/${id}`),

  /**
   * Stream job progress. EventSource cannot send an Authorization header, so
   * this reads the SSE frames off a fetch body instead.
   */
  streamJob: async (
    jobId: string,
    onProgress: (job: Job) => void,
    signal?: AbortSignal,
  ): Promise<Job> => {
    const res = await fetch(`${BASE}/jobs/${jobId}/stream`, { headers: authHeader(), signal })
    if (!res.ok || !res.body) throw await failure(res)

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let last: Job | null = null

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const { events, rest } = parseSseFrames(buffer)
      buffer = rest

      for (const { event, data } of events) {
        if (event === 'error') throw new ApiError(500, data)
        const job = JSON.parse(data) as Job
        last = job
        onProgress(job)
        if (event === 'done') {
          void reader.cancel()
          return job
        }
      }
    }
    if (!last) throw new ApiError(500, 'Stream closed before any progress arrived')
    return last
  },
}
