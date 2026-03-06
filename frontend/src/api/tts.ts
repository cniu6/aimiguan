import { apiClient } from './client'

export interface TTSTask {
  id: number
  source_type: string
  source_id: number | null
  text_preview: string
  text_content?: string
  voice_model: string
  audio_path: string | null
  state: string
  error_message: string | null
  trace_id: string
  created_at: string
  updated_at: string
}

export interface TTSListResponse {
  total: number
  page: number
  page_size: number
  items: TTSTask[]
}

export const ttsApi = {
  async createTask(text: string, voiceModel?: string, sourceType?: string, sourceId?: number) {
    return apiClient.post('/tts/tasks', {
      text,
      voice_model: voiceModel ?? 'local-tts-v1',
      source_type: sourceType,
      source_id: sourceId,
    })
  },

  async listTasks(params?: { state?: string; page?: number; page_size?: number }): Promise<TTSListResponse> {
    const res = await apiClient.get('/tts/tasks', { params })
    return (res as any)?.data ?? res as any
  },

  async getTask(taskId: number): Promise<TTSTask> {
    const res = await apiClient.get(`/tts/tasks/${taskId}`)
    return (res as any)?.data ?? res as any
  },

  async processTask(taskId: number) {
    return apiClient.post(`/tts/tasks/${taskId}/process`)
  },
}
