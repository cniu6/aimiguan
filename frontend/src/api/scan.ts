import { apiClient } from './client'

export interface ScanTask {
  id: number
  target: string
  target_type: string
  tool_name: string
  profile?: string
  state: string
  priority: number
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
  severity: 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW' | 'INFO'
  status: 'NEW' | 'CONFIRMED' | 'FALSE_POSITIVE' | 'FIXED' | 'IGNORED'
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

export interface CreateTaskRequest {
  target: string
  target_type?: string
  tool_name?: string
  profile?: string
  script_set?: string
  asset_id?: number
}

export interface CreateAssetRequest {
  target: string
  target_type: string
  tags?: string
  priority?: number
  description?: string
}

export const scanApi = {
  // ===== 资产管理 =====
  async getAssets(params?: { target_type?: string; enabled?: boolean }): Promise<Asset[]> {
    const response = await apiClient.get('/scan/assets', { params })
    return response.data || []
  },

  async getAsset(assetId: number): Promise<Asset> {
    const response = await apiClient.get(`/scan/assets/${assetId}`)
    return response.data
  },

  async createAsset(asset: CreateAssetRequest) {
    return apiClient.post('/scan/assets', asset)
  },

  async updateAsset(assetId: number, asset: CreateAssetRequest) {
    return apiClient.put(`/scan/assets/${assetId}`, asset)
  },

  async deleteAsset(assetId: number) {
    return apiClient.delete(`/scan/assets/${assetId}`)
  },

  // ===== 扫描任务 =====
  async getTasks(state?: string, limit?: number): Promise<ScanTask[]> {
    const response = await apiClient.get('/scan/tasks', { params: { state, limit } })
    return Array.isArray(response) ? response : []
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
    severity?: string; 
    status?: string; 
    scan_task_id?: number;
    limit?: number;
  }): Promise<ScanFinding[]> {
    const response = await apiClient.get('/scan/findings', { params })
    return response.data || []
  },

  async updateFindingStatus(findingId: number, status: string) {
    return apiClient.put(`/scan/findings/${findingId}/status?status=${status}`)
  }
}
