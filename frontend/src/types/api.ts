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
