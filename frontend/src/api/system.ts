import { apiClient } from './client'

export interface SystemProfile {
  username: string
  email?: string | null
  full_name?: string | null
  role: string
  permissions: string[]
}

export const systemApi = {
  getProfile: (): Promise<SystemProfile> => apiClient.get('/system/profile') as any,
}
