import { apiClient } from './client'

export const scanApi = {
  async getTasks(state?: string) {
    return apiClient.get('/scan/tasks', { params: { state } })
  },

  async getTask(taskId: number) {
    return apiClient.get(`/scan/tasks/${taskId}`)
  },

  async createTask(task: { target: string; target_type?: string; tool_name?: string }) {
    return apiClient.post('/scan/tasks', task)
  }
}