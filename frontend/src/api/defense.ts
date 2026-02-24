import { apiClient } from './client'

interface ThreatEvent {
  id: number
  ip: string
  source: string
  ai_score: number
  ai_reason: string
  status: string
  created_at: string
}

export const defenseApi = {
  async getPendingEvents(): Promise<ThreatEvent[]> {
    return apiClient.get('/defense/events', { params: { status: 'PENDING' } })
  },

  async getEvents(status?: string): Promise<ThreatEvent[]> {
    return apiClient.get('/defense/events', { params: { status } })
  },

  async approveEvent(eventId: number, reason: string) {
    return apiClient.post(`/defense/events/${eventId}/approve`, { reason })
  },

  async rejectEvent(eventId: number, reason: string) {
    return apiClient.post(`/defense/events/${eventId}/reject`, { reason })
  },

  async submitAlert(alert: { ip: string; source: string; attack_type?: string }) {
    return apiClient.post('/defense/alerts', alert)
  }
}