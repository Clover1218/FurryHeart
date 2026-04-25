import { http } from '@/utils/http'

export interface ConfigUIResponse {
  token: string
}

export const configUIApi = () => {
  return http.get<any>('/config/ui')
}

export const configUserUpdateApi = (diff:any) => {
  return http.post('/config/user/update',diff)
}
