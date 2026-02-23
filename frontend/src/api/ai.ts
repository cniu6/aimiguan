import { apiClient } from './client'

export const aiApi = {
  async chat(message: string, context?: { type: string; id: string }) {
    return apiClient.post('/ai/chat', {
      message,
      context_type: context?.type,
      context_id: context?.id
    })
  },

  async getSessions() {
    return apiClient.get('/ai/sessions')
  },

  async getSessionMessages(sessionId: number) {
    return apiClient.get(`/ai/sessions/${sessionId}/messages`)
  }
}