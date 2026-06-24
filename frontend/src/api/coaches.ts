import { http } from './http'
import type { Paginated, PageQuery } from './types'
import type { Gender } from './members'

export interface Coach {
  id: number
  name: string
  gender: Gender | null
  phone: string | null
  specialty: string | null
  bio: string | null
  hired_at: string | null
  is_active: boolean
  created_at: string
}

export interface CoachCreatePayload {
  name: string
  gender?: Gender | null
  phone?: string | null
  specialty?: string | null
  bio?: string | null
  hired_at?: string | null
}

export type CoachUpdatePayload = Partial<CoachCreatePayload & { is_active: boolean }>

export interface CoachListQuery extends PageQuery {
  q?: string
  include_inactive?: boolean
}

export async function listCoaches(q: CoachListQuery = {}): Promise<Paginated<Coach>> {
  const params: Record<string, any> = { ...q }
  if (q.include_inactive) params.include_inactive = 1
  else delete params.include_inactive
  const resp = await http.get<Paginated<Coach>>('/coaches', { params })
  return resp.data
}

export async function createCoach(payload: CoachCreatePayload): Promise<Coach> {
  const resp = await http.post<Coach>('/coaches', payload)
  return resp.data
}

export async function updateCoach(id: number, payload: CoachUpdatePayload): Promise<Coach> {
  const resp = await http.patch<Coach>(`/coaches/${id}`, payload)
  return resp.data
}

export async function deactivateCoach(id: number): Promise<void> {
  await http.delete(`/coaches/${id}`)
}
