import { apiClient } from './client'

export interface ThreatEvent {
  id: number
  ip: string
  source: string
  ai_score: number
  ai_reason: string
  status: string
  created_at: string
}

export interface HFishConfig {
  host_port: string | null
  sync_interval: number
  enabled: boolean
}

export interface HFishConfigRequest {
  host_port: string
  api_key: string
  sync_interval: number
  enabled: boolean
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
  },

  // ── HFish 配置 ──
  async getHFishConfig(): Promise<HFishConfig> {
    const res = await apiClient.get('/defense/hfish/config')
    return res.data
  },

  async saveHFishConfig(config: HFishConfigRequest) {
    return apiClient.post('/defense/hfish/config', config)
  },

  async triggerHFishSync() {
    return apiClient.post('/defense/hfish/sync')
  },
}