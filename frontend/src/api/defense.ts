import { apiClient } from './client'

export const defenseApi = {
  async getPendingEvents() {
    return apiClient.get('/defense/events', { params: { status: 'PENDING' } })
  },

  async getEvents(status?: string) {
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