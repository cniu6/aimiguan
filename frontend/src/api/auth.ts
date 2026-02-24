import { apiClient } from './client'

export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  token_type: string
  user: {
    username: string
    role: string
  }
}

export interface UserInfo {
  username: string
  role: string
}

export const authApi = {
  login: (data: LoginRequest): Promise<TokenResponse> => 
    apiClient.post('/auth/login', data) as any,
  
  logout: () => 
    apiClient.post('/auth/logout'),
  
  refresh: (): Promise<TokenResponse> => 
    apiClient.post('/auth/refresh') as any,
  
  getProfile: (): Promise<UserInfo> => 
    apiClient.get('/auth/profile') as any
}
