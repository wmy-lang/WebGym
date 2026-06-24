import { http } from './http'
import type { Paginated, PageQuery } from './types'

export interface ClassDefinition {
  id: number
  name: string
  description: string | null
  coach_id: number | null
  coach_name: string | null
  capacity: number
  duration_minutes: number
  is_active: boolean
}

export interface ClassCreatePayload {
  name: string
  description?: string | null
  coach_id?: number | null
  capacity?: number
  duration_minutes?: number
}

export type ClassUpdatePayload = Partial<ClassCreatePayload & { is_active: boolean }>

export interface ClassListQuery extends PageQuery {
  q?: string
  include_inactive?: boolean
}

export async function listClasses(q: ClassListQuery = {}): Promise<Paginated<ClassDefinition>> {
  const params: Record<string, any> = { ...q }
  if (q.include_inactive) params.include_inactive = 1
  else delete params.include_inactive
  const resp = await http.get<Paginated<ClassDefinition>>('/classes', { params })
  return resp.data
}

export async function createClass(payload: ClassCreatePayload): Promise<ClassDefinition> {
  const resp = await http.post<ClassDefinition>('/classes', payload)
  return resp.data
}

export async function updateClass(id: number, payload: ClassUpdatePayload): Promise<ClassDefinition> {
  const resp = await http.patch<ClassDefinition>(`/classes/${id}`, payload)
  return resp.data
}

export async function deactivateClass(id: number): Promise<void> {
  await http.delete(`/classes/${id}`)
}
