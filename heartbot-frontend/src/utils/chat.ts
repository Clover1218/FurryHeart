import { http } from '@/utils/http'

export const chatApi = (input: string) => {
  return http.post('/chat', { input })
}

export const getHistoryApi = (input: string) => {
  return http.get(`/chat/history?cursor=${input}&limit=20`, )
}
