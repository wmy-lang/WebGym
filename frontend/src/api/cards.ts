import { http } from './http'
import type { Paginated, PageQuery } from './types'

export type CardStatus = 'active' | 'frozen' | 'expired' | 'cancelled'

export interface Card {
  id: number
  card_no: string
  member_id: number
  member_name: string | null
  card_type_id: number
  card_type_name: string | null
  start_date: string
  end_date: string | null
  remaining_visits: number | null
  status: CardStatus
  issued_by: number | null
  issued_at: string
  frozen_at: string | null
}

export interface CardIssuePayload {
  member_id: number
  card_type_id: number
  start_date?: string | null
}

export interface CardListQuery extends PageQuery {
  member_id?: number
  status?: CardStatus
}

export async function listCards(q: CardListQuery = {}): Promise<Paginated<Card>> {
  const resp = await http.get<Paginated<Card>>('/cards', { params: q })
  return resp.data
}

export async function issueCard(payload: CardIssuePayload): Promise<Card> {
  const resp = await http.post<Card>('/cards', payload)
  return resp.data
}

export async function renewCard(id: number): Promise<Card> {
  const resp = await http.post<Card>(`/cards/${id}/renew`)
  return resp.data
}

export async function freezeCard(id: number): Promise<Card> {
  const resp = await http.post<Card>(`/cards/${id}/freeze`)
  return resp.data
}

export async function unfreezeCard(id: number): Promise<Card> {
  const resp = await http.post<Card>(`/cards/${id}/unfreeze`)
  return resp.data
}

export async function cancelCard(id: number): Promise<Card> {
  const resp = await http.post<Card>(`/cards/${id}/cancel`)
  return resp.data
}

export async function sweepExpiredCards(): Promise<{ affected: number }> {
  const resp = await http.post<{ affected: number }>('/cards/sweep-expired')
  return resp.data
}
