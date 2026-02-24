import { apiClient } from './client'

interface ChatContext {
  type?: string
  id?: string
}

interface ChatResponse {
  message: string
  context?: ChatContext
}

interface SessionMessage {
  role: string
  content: string
  created_at: string
}

export const aiApi = {
  async chat(message: string, context?: { type: string; id: string }): Promise<ChatResponse> {
    return apiClient.post('/ai/chat', {
      message,
      context_type: context?.type,
      context_id: context?.id
    })
  },

  async getSessions() {
    return apiClient.get('/ai/sessions')
  },

  async getSessionMessages(sessionId: number): Promise<SessionMessage[]> {
    return apiClient.get(`/ai/sessions/${sessionId}/messages`)
  }
}