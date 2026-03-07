import { apiClient } from './client'

export interface ScanTask {
  id: number
  target: string
  target_type: string
  tool_name: string
  profile?: string
  state: string
  priority: number
  timeout_seconds?: number
  error_message?: string
  started_at?: string
  ended_at?: string
  created_at: string
}

export interface ScanFinding {
  id: number
  scan_task_id: number
  asset: string
  port?: number
  service?: string
  severity: 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  status: 'NEW' | 'CONFIRMED' | 'FALSE_POSITIVE' | 'FIXED' | 'IGNORED'
  cve?: string
  evidence?: string
  created_at: string
}

export interface Asset {
  id: number
  target: string
  target_type: 'IP' | 'CIDR' | 'DOMAIN'
  tags?: string
  priority: number
  enabled: boolean
  description?: string
  created_at: string
}

export interface ScanProfile {
  key: string
  name: string
  description: string
  estimated_seconds: number
  risk_level: 'low' | 'medium' | 'high'
  available: boolean
}

export interface PagedResult<T> {
  total: number
  page: number
  page_size: number
  items: T[]
}

export interface CreateTaskRequest {
  target: string
  target_type?: string
  tool_name?: string
  profile?: string
  script_set?: string
  asset_id?: number
  timeout_seconds?: number
}

export interface CreateAssetRequest {
  target: string
  target_type: string
  tags?: string
  priority?: number
  enabled?: boolean
  description?: string
}

export const scanApi = {
  // ===== Profiles =====
  async getProfiles(): Promise<ScanProfile[]> {
    const response = await apiClient.get('/scan/profiles')
    return response.data || []
  },

  // ===== 资产管理 =====
  async getAssets(params?: {
    target_type?: string
    enabled?: boolean
    keyword?: string
    page?: number
    page_size?: number
  }): Promise<PagedResult<Asset>> {
    const response = await apiClient.get('/scan/assets', { params })
    return response.data || { total: 0, page: 1, page_size: 20, items: [] }
  },

  async getAsset(assetId: number): Promise<Asset> {
    const response = await apiClient.get(`/scan/assets/${assetId}`)
    return response.data
  },

  async createAsset(asset: CreateAssetRequest) {
    return apiClient.post('/scan/assets', asset)
  },

  async updateAsset(assetId: number, asset: Partial<CreateAssetRequest>) {
    return apiClient.put(`/scan/assets/${assetId}`, asset)
  },

  async toggleAsset(assetId: number): Promise<{ enabled: boolean }> {
    const response = await apiClient.patch(`/scan/assets/${assetId}/toggle`)
    return response.data
  },

  async deleteAsset(assetId: number) {
    return apiClient.delete(`/scan/assets/${assetId}`)
  },

  // ===== 扫描任务 =====
  async getTasks(params?: {
    state?: string
    profile?: string
    target?: string
    page?: number
    page_size?: number
  }): Promise<PagedResult<ScanTask>> {
    const response = await apiClient.get('/scan/tasks', { params })
    return response.data || { total: 0, page: 1, page_size: 20, items: [] }
  },

  async getTask(taskId: number): Promise<{ task: ScanTask; findings: ScanFinding[] }> {
    const response = await apiClient.get(`/scan/tasks/${taskId}`)
    return response.data
  },

  async getTaskStatus(taskId: number): Promise<{ task_id: number; state: string; memory_status?: string }> {
    const response = await apiClient.get(`/scan/tasks/${taskId}/status`)
    return response.data
  },

  async createTask(task: CreateTaskRequest) {
    return apiClient.post('/scan/tasks', task)
  },

  async cancelTask(taskId: number) {
    return apiClient.post(`/scan/tasks/${taskId}/cancel`)
  },

  // ===== 扫描发现 =====
  async getFindings(params?: {
    severity?: string
    status?: string
    scan_task_id?: number
    asset?: string
    page?: number
    page_size?: number
  }): Promise<PagedResult<ScanFinding>> {
    const response = await apiClient.get('/scan/findings', { params })
    return response.data || { total: 0, page: 1, page_size: 20, items: [] }
  },

  async updateFindingStatus(findingId: number, status: string) {
    return apiClient.put(`/scan/findings/${findingId}/status?status=${status}`)
  },

  // ── Nmap 配置 ──
  async getNmapConfig(): Promise<{ nmap_path: string | null; ip_ranges: string[]; scan_interval: number; enabled: boolean }> {
    const res = await apiClient.get('/scan/nmap/config')
    return res as unknown as { nmap_path: string | null; ip_ranges: string[]; scan_interval: number; enabled: boolean }
  },

  async saveNmapConfig(config: {
    nmap_path: string
    ip_ranges: string[]
    scan_interval: number
    enabled: boolean
    vuln_scripts_by_tag?: Record<string, string[]>
  }) {
    return apiClient.post('/scan/nmap/config', config)
  },

  async triggerNmapScan(target?: string, profile?: string) {
    const params: Record<string, string> = {}
    if (target) params.target = target
    if (profile) params.profile = profile
    return apiClient.post('/scan/nmap/scan', null, { params })
  },

  async getWin7Hosts(taskId: number) {
    const res = await apiClient.get(`/scan/tasks/${taskId}/win7-hosts`)
    return res
  },

  // ── Nmap 扫描主机结果 ──
  async getNmapHosts(params?: {
    scan_id?: number
    state?: string
    limit?: number
    offset?: number
  }): Promise<{ total: number; items: NmapHost[] }> {
    const res = await apiClient.get('/scan/nmap/hosts', { params })
    const d = res?.data ?? res
    if (d?.total !== undefined) return d
    if (Array.isArray(d)) return { total: d.length, items: d }
    return { total: 0, items: [] }
  },

  async getNmapScans(): Promise<NmapScan[]> {
    const res = await apiClient.get('/scan/nmap/scans')
    const d = res?.data ?? res
    return Array.isArray(d) ? d : (d?.items ?? [])
  },

  async getNmapStats(scan_id?: number): Promise<NmapStats> {
    const res = await apiClient.get('/scan/nmap/stats', { params: scan_id ? { scan_id } : {} })
    return res?.data ?? res
  },

  async getNmapHostByIp(ip: string, scan_id?: number): Promise<NmapHost | null> {
    const res = await apiClient.get(`/scan/nmap/host/${ip}`, { params: scan_id ? { scan_id } : {} })
    return res?.data ?? null
  },

  // ── Nmap 自动发现资产 ──
  async getDiscoveredAssets(params?: {
    mac?: string
    ip?: string
    limit?: number
    offset?: number
  }): Promise<{ total: number; items: DiscoveredAsset[] }> {
    const res = await apiClient.get('/scan/nmap/assets', { params })
    const d = res?.data ?? res
    if (d?.total !== undefined) return d
    if (Array.isArray(d)) return { total: d.length, items: d }
    return { total: 0, items: [] }
  },

  async getAssetIpHistory(assetIp: string): Promise<AssetIpHistory[]> {
    const res = await apiClient.get(`/scan/nmap/assets/${assetIp}/ips`)
    const d = res?.data ?? res
    return Array.isArray(d?.history) ? d.history : []
  },

  // ── 漏洞统计 ──
  async getVulnStats(): Promise<VulnStats> {
    const res = await apiClient.get('/scan/nmap/vuln/stats')
    return res?.data ?? res
  },

  async triggerVulnScan(): Promise<{ success: boolean; message: string }> {
    const res = await apiClient.post('/scan/nmap/vuln/scan')
    const record = res as unknown as Record<string, unknown> | null | undefined
    const message = typeof record?.message === 'string'
      ? String(record.message)
      : '扫描已启动'
    return { success: true, message }
  },
}

// ── Nmap 相关类型定义（与后端 ScanFinding 字段对齐）──

export interface NmapHost {
  id: number
  scan_task_id: number
  ip: string
  mac_address: string
  vendor: string
  hostname: string
  state: string
  os_type: string
  os_accuracy: string
  open_ports: number[]
  services: { port: number; protocol?: string; service: string; product?: string; version?: string; extrainfo?: string }[]
  scanned_at: string | null
}

export interface NmapScan {
  id: number
  target: string
  profile: string | null
  state: string
  started_at: string | null
  ended_at: string | null
  created_at: string
}

export interface NmapStats {
  total: number
  online: number
  offline: number
  os_dist: { os: string; count: number }[]
}

export interface DiscoveredAsset {
  id: number
  current_ip: string
  mac_address: string | null
  vendor: string | null
  hostname: string | null
  state: string
  os_type: string | null
  open_ports: number[]
  last_seen: string | null
  scan_task_id: number
}

export interface AssetIpHistory {
  id: number
  ip: string
  scan_task_id: number | null
  state: string | null
  seen_time: string | null
}

export interface VulnStats {
  total: number
  high: number
  medium: number
  low: number
  confirmed: number
  false_positive: number
  affected_assets: number
}
