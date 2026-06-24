import { http } from './http'
import type { Paginated, PageQuery } from './types'

export interface Attendance {
  id: number
  booking_id: number
  member_id: number | null
  member_name: string | null
  session_id: number | null
  class_name: string | null
  checked_in_at: string
  checked_in_by: number | null
}

export interface AttendanceListQuery extends PageQuery {
  member_id?: number
  session_id?: number
}

export async function listAttendance(q: AttendanceListQuery = {}): Promise<Paginated<Attendance>> {
  const resp = await http.get<Paginated<Attendance>>('/attendance', { params: q })
  return resp.data
}

export async function checkIn(booking_id: number): Promise<Attendance> {
  const resp = await http.post<Attendance>('/attendance', { booking_id })
  return resp.data
}
