import { http } from '@/utils/http'

export interface ChatResponse {
  reply: string
}

export interface HistoryResponse {
  messages: { role: string; text: string }[]
  next_cursor: string
}

export const chatApi = (input: string) => {
  return http.post<ChatResponse>('/chat', { input })
}

export const getHistoryApi = (input: string) => {
  return http.get<HistoryResponse>(`/chat/history?cursor=${input}&limit=20`)
}
