import { http } from './http'
import type { Paginated, PageQuery } from './types'

export type Gender = 'male' | 'female' | 'other'

export interface Member {
  id: number
  username: string
  role: 'member'
  is_active: boolean
  real_name: string | null
  phone: string | null
  gender: Gender | null
  birthday: string | null
  emergency_contact: string | null
  note: string | null
  created_at: string
  last_login_at: string | null
}

export interface MemberCreatePayload {
  username: string
  password: string
  real_name: string
  phone: string
  gender?: Gender | null
  birthday?: string | null
  id_card?: string | null
  emergency_contact?: string | null
  note?: string | null
}

export type MemberUpdatePayload = Partial<{
  real_name: string
  phone: string
  gender: Gender | null
  birthday: string | null
  emergency_contact: string | null
  note: string | null
  is_active: boolean
}>

export interface MemberListQuery extends PageQuery {
  q?: string
  include_inactive?: boolean
}

export async function listMembers(q: MemberListQuery = {}): Promise<Paginated<Member>> {
  const params: Record<string, any> = { ...q }
  if (q.include_inactive) params.include_inactive = 1
  else delete params.include_inactive
  const resp = await http.get<Paginated<Member>>('/members', { params })
  return resp.data
}

export async function createMember(payload: MemberCreatePayload): Promise<Member> {
  const resp = await http.post<Member>('/members', payload)
  return resp.data
}

export async function updateMember(id: number, payload: MemberUpdatePayload): Promise<Member> {
  const resp = await http.patch<Member>(`/members/${id}`, payload)
  return resp.data
}

export async function deactivateMember(id: number): Promise<void> {
  await http.delete(`/members/${id}`)
}

export async function getMember(id: number): Promise<Member> {
  const resp = await http.get<Member>(`/members/${id}`)
  return resp.data
}
