import { http } from './http'
import type { Paginated, PageQuery } from './types'

export type BookingStatus = 'booked' | 'cancelled' | 'attended' | 'no_show'
export type BookingSource = 'self' | 'admin'

export interface Booking {
  id: number
  member_id: number
  member_name: string | null
  session_id: number
  class_name: string | null
  start_at: string | null
  end_at: string | null
  card_id: number | null
  card_no: string | null
  status: BookingStatus
  source: BookingSource
  booked_at: string
  cancelled_at: string | null
  checked_in_at: string | null
}

export interface BookingCreatePayload {
  session_id: number
  member_id?: number
}

export interface BookingListQuery extends PageQuery {
  member_id?: number
  session_id?: number
  status?: BookingStatus
}

export async function listBookings(q: BookingListQuery = {}): Promise<Paginated<Booking>> {
  const resp = await http.get<Paginated<Booking>>('/bookings', { params: q })
  return resp.data
}

export async function createBooking(payload: BookingCreatePayload): Promise<Booking> {
  const resp = await http.post<Booking>('/bookings', payload)
  return resp.data
}

export async function cancelBooking(id: number): Promise<Booking> {
  const resp = await http.post<Booking>(`/bookings/${id}/cancel`)
  return resp.data
}

export async function getBooking(id: number): Promise<Booking> {
  const resp = await http.get<Booking>(`/bookings/${id}`)
  return resp.data
}
