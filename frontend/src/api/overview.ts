import { apiClient } from './client'

export type TrendRange = '24h' | '7d' | '30d'

// ── metrics ──

export interface DefenseMetrics {
  today_alerts: number
  pending_events: number
  high_risk_pending: number
  today_blocked: number
  manual_required: number
  block_success_rate: number
}

export interface ProbeMetrics {
  total_assets: number
  enabled_assets: number
  running_tasks: number
  today_tasks: number
  total_findings: number
  high_findings: number
  medium_findings: number
}

export interface OverviewMetrics {
  defense: DefenseMetrics
  probe: ProbeMetrics
  generated_at: string
}

// ── trends ──

export interface TrendPoint {
  date: string
  count: number
}

export interface OverviewTrends {
  range: TrendRange
  alert_trend: TrendPoint[]
  high_alert_trend: TrendPoint[]
  task_trend: TrendPoint[]
}

// ── todos ──

export interface PendingEventItem {
  id: number
  ip: string
  source: string
  ai_score: number | null
  ai_reason: string | null
  status: string
  created_at: string
}

export interface FailedTaskItem {
  id: number
  event_id: number
  action: string
  state: string
  retry_count: number
  error_message: string | null
  updated_at: string
}

export interface HighFindingItem {
  id: number
  asset: string
  port: number | null
  service: string | null
  cve: string | null
  severity: string
  status: string
  created_at: string
}

export interface OverviewTodos {
  pending_events: PendingEventItem[]
  failed_tasks: FailedTaskItem[]
  high_findings: HighFindingItem[]
  counts: {
    pending_events: number
    manual_required: number
    high_findings_new: number
  }
}

// ── defense stats ──

export interface LevelCount {
  level: string
  count: number
}

export interface ServiceCount {
  service: string
  count: number
}

export interface TopIP {
  ip: string
  count: number
  max_score: number | null
}

export interface DefenseStats {
  range: TrendRange
  total: number
  high_total: number
  threat_level_dist: LevelCount[]
  service_dist: ServiceCount[]
  top_ips: TopIP[]
}

export interface ChainStatusItem {
  key: string
  name: string
  ok: boolean
  note: string
  metric?: string | null
}

export interface OverviewChainStatus {
  defense: ChainStatusItem[]
  probe: ChainStatusItem[]
  generated_at: string
}

let chainStatusEndpointAvailable: boolean | null = null

const createEmptyChainStatus = (): OverviewChainStatus => ({
  defense: [],
  probe: [],
  generated_at: new Date().toISOString(),
})

// ── API ──

export const overviewApi = {
  async getMetrics(): Promise<OverviewMetrics> {
    const res = await apiClient.get('/overview/metrics')
    return res as unknown as OverviewMetrics
  },

  async getTrends(range: TrendRange = '7d'): Promise<OverviewTrends> {
    const res = await apiClient.get('/overview/trends', { params: { range } })
    return res as unknown as OverviewTrends
  },

  async getTodos(): Promise<OverviewTodos> {
    const res = await apiClient.get('/overview/todos')
    return res as unknown as OverviewTodos
  },

  async getDefenseStats(range: TrendRange = '7d'): Promise<DefenseStats> {
    const res = await apiClient.get('/overview/defense-stats', { params: { range } })
    return res as unknown as DefenseStats
  },

  async getChainStatus(): Promise<OverviewChainStatus> {
    if (chainStatusEndpointAvailable === false) {
      return createEmptyChainStatus()
    }

    try {
      const res = await apiClient.get('/overview/chain-status')
      chainStatusEndpointAvailable = true
      return (res as unknown as OverviewChainStatus) ?? createEmptyChainStatus()
    } catch (error: any) {
      if (error?.response?.status === 404) {
        chainStatusEndpointAvailable = false
        return createEmptyChainStatus()
      }
      throw error
    }
  },
}
