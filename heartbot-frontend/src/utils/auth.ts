import { http } from '@/utils/http'

export const loginApi = (open_id: string) => {
  return http.post('/auth/login', { open_id })
}

export const meApi = () => {
  return http.get('/me')
}

export const logoutApi = () => {
  return http.post('/logout')
}