import { apiClient } from './client'

export const reportApi = {
  async generate(reportType: string, scope?: string) {
    return apiClient.post('/report/generate', {
      report_type: reportType,
      scope
    })
  },

  async getReports() {
    return apiClient.get('/report/reports')
  },

  async getReport(reportId: number) {
    return apiClient.get(`/report/reports/${reportId}`)
  }
}