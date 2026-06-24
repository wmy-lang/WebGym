import { http } from './http'

export type UserRole = 'admin' | 'staff' | 'member'

export interface CurrentUser {
  id: number
  username: string
  role: UserRole
  is_active: boolean
  real_name: string | null
  phone: string | null
}

export async function login(username: string, password: string): Promise<CurrentUser> {
  const resp = await http.post<{ user: CurrentUser }>('/auth/login', { username, password })
  return resp.data.user
}

export async function logout(): Promise<void> {
  await http.post('/auth/logout')
}

export async function fetchMe(): Promise<CurrentUser | null> {
  try {
    const resp = await http.get<{ user: CurrentUser }>('/auth/me')
    return resp.data.user
  } catch {
    return null
  }
}
