import { http } from '@/utils/http'

export interface LoginResponse {
  token: string
}

export const loginApi = (open_id: string) => {
  return http.post<LoginResponse>('/auth/login', { open_id })
}

export const meApi = () => {
  return http.get('/me')
}

export const logoutApi = () => {
  return http.post('/logout')
}