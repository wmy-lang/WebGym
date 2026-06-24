import { http } from './http'
import type { Paginated, PageQuery } from './types'

export type SessionStatus = 'scheduled' | 'cancelled' | 'finished'

export interface ClassSession {
  id: number
  class_def_id: number
  class_name: string | null
  coach_id: number | null
  coach_name: string | null
  start_at: string
  end_at: string
  capacity: number
  location: string | null
  status: SessionStatus
  booked_count: number
}

export interface SessionCreatePayload {
  class_def_id: number
  start_at: string
  end_at?: string | null
  coach_id?: number | null
  capacity?: number | null
  location?: string | null
}

export interface SessionUpdatePayload {
  start_at?: string
  end_at?: string
  coach_id?: number | null
  capacity?: number
  location?: string | null
}

export interface SessionListQuery extends PageQuery {
  from?: string
  to?: string
  class_def_id?: number
  coach_id?: number
  status?: SessionStatus
}

export async function listSessions(q: SessionListQuery = {}): Promise<Paginated<ClassSession>> {
  const resp = await http.get<Paginated<ClassSession>>('/sessions', { params: q })
  return resp.data
}

export async function createSession(payload: SessionCreatePayload): Promise<ClassSession> {
  const resp = await http.post<ClassSession>('/sessions', payload)
  return resp.data
}

export async function updateSession(id: number, payload: SessionUpdatePayload): Promise<ClassSession> {
  const resp = await http.patch<ClassSession>(`/sessions/${id}`, payload)
  return resp.data
}

export async function cancelSession(id: number): Promise<ClassSession> {
  const resp = await http.post<ClassSession>(`/sessions/${id}/cancel`)
  return resp.data
}

export async function finishSession(id: number): Promise<ClassSession> {
  const resp = await http.post<ClassSession>(`/sessions/${id}/finish`)
  return resp.data
}
