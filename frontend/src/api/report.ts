import { apiClient } from './client'

interface ReportItem {
  id: number
  report_type: string
  summary: string
  created_at: string
}

export const reportApi = {
  async generate(reportType: string, scope?: string) {
    return apiClient.post('/report/generate', {
      report_type: reportType,
      scope
    })
  },

  async getReports(): Promise<ReportItem[]> {
    return apiClient.get('/report/reports')
  },

  async getReport(reportId: number): Promise<ReportItem> {
    return apiClient.get(`/report/reports/${reportId}`)
  }
}