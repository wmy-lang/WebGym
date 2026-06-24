import { http } from './http'
import type { Paginated, PageQuery } from './types'

export interface CardType {
  id: number
  name: string
  duration_days: number | null
  total_visits: number | null
  price: string
  is_active: boolean
}

export interface CardTypeCreatePayload {
  name: string
  duration_days?: number | null
  total_visits?: number | null
  price: string | number
}

export type CardTypeUpdatePayload = Partial<CardTypeCreatePayload & { is_active: boolean }>

export async function listCardTypes(q: PageQuery = {}): Promise<Paginated<CardType>> {
  const resp = await http.get<Paginated<CardType>>('/card-types', { params: q })
  return resp.data
}

export async function createCardType(payload: CardTypeCreatePayload): Promise<CardType> {
  const resp = await http.post<CardType>('/card-types', payload)
  return resp.data
}

export async function updateCardType(id: number, payload: CardTypeUpdatePayload): Promise<CardType> {
  const resp = await http.patch<CardType>(`/card-types/${id}`, payload)
  return resp.data
}

export async function deactivateCardType(id: number): Promise<void> {
  await http.delete(`/card-types/${id}`)
}
