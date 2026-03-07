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
  api_base_url: string | null
  sync_interval: number
  enabled: boolean
}

export interface HFishConfigRequest {
  host_port: string
  api_key: string
  sync_interval: number
  enabled: boolean
  api_base_url?: string
}

// ── HFish 攻击日志 ──
export interface HFishLog {
  id: number
  attack_ip: string
  ip_location: string
  client_id: string
  client_name: string
  service_name: string
  service_port: string
  threat_level: string
  create_time_str: string
  create_time_timestamp: number
}

export interface HFishStats {
  total: number
  threat_stats: { level: string; count: number }[]
  service_stats: { name: string; count: number }[]
  ip_stats: { ip: string; count: number }[]
  time_stats: { date: string; count: number }[]
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
    return res as unknown as HFishConfig
  },

  async saveHFishConfig(config: HFishConfigRequest) {
    return apiClient.post('/defense/hfish/config', config)
  },

  async triggerHFishSync() {
    return apiClient.post('/defense/hfish/sync')
  },

  // ── HFish 攻击日志 ──
  async getHFishLogs(params?: {
    limit?: number
    offset?: number
    threat_level?: string
    service_name?: string
    days?: number
  }): Promise<{ total: number; items: HFishLog[] }> {
    const res = await apiClient.get('/defense/hfish/logs', { params })
    // 后端返回 { code:0, data: { total, items } }
    const d = res?.data ?? res
    if (d?.total !== undefined) return d
    if (Array.isArray(d)) return { total: d.length, items: d }
    return { total: 0, items: [] }
  },

  async getHFishStats(): Promise<HFishStats> {
    const res = await apiClient.get('/defense/hfish/stats')
    return res?.data ?? res
  },
}