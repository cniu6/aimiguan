import { apiClient } from './client'

export interface SystemProfile {
  username: string
  email?: string | null
  full_name?: string | null
  role: string
  permissions: string[]
}

export interface SetModeRequest {
  mode: 'ACTIVE' | 'PASSIVE'
  reason?: string
}

export interface SystemModeResponse {
  mode: 'ACTIVE' | 'PASSIVE'
  reason?: string | null
  operator?: string | null
  updated_at: string
}

export const systemApi = {
  getProfile: (): Promise<SystemProfile> => apiClient.get('/system/profile') as any,
  getMode: (): Promise<SystemModeResponse> => apiClient.get('/system/mode') as any,
  setMode: (data: SetModeRequest): Promise<SystemModeResponse> =>
    apiClient.post('/system/mode', data) as any,
}
