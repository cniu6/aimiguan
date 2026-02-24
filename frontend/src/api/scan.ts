import { apiClient } from './client'

interface ScanTask {
  id: number
  target: string
  tool_name: string
  state: string
  created_at: string
}

export const scanApi = {
  async getTasks(state?: string): Promise<ScanTask[]> {
    return apiClient.get('/scan/tasks', { params: { state } })
  },

  async getTask(taskId: number): Promise<ScanTask> {
    return apiClient.get(`/scan/tasks/${taskId}`)
  },

  async createTask(task: { target: string; target_type?: string; tool_name?: string }) {
    return apiClient.post('/scan/tasks', task)
  }
}