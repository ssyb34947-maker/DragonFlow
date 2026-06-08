import api from './client'
import type { ApiResponse, DownloadTask, DataStats, PipelineStep, StockData, IndexData } from './client'

export const downloadApi = {
  startDownload: (params: {
    startDate: string
    endDate: string
    indexCode: string
    adjust: string
    force?: boolean
    sleep?: number
    skipFundamental?: boolean
    limit?: number
  }) => api.post<ApiResponse<DownloadTask>>('/download/start', params),

  getStatus: (taskId: string) => api.get<ApiResponse<DownloadTask>>(`/download/status/${taskId}`),

  getManifest: () => api.get<ApiResponse<Record<string, unknown>>>('/download/manifest'),
}

export const dataApi = {
  getStats: () => api.get<ApiResponse<DataStats>>('/data/stats'),

  getStockDaily: (params: {
    stockCode?: string
    startDate?: string
    endDate?: string
    limit?: number
  }) => api.get<ApiResponse<StockData[]>>('/data/stock-daily', { params }),

  getIndexDaily: (params: {
    indexCode?: string
    startDate?: string
    endDate?: string
  }) => api.get<ApiResponse<IndexData[]>>('/data/index-daily', { params }),

  getConstituents: () => api.get<ApiResponse<Array<{ stock_code: string; stock_name: string; industry?: string }>>>('/data/constituents'),

  getStockInfo: () => api.get<ApiResponse<Array<{ stock_code: string; stock_name: string; industry?: string; total_market_value?: string; float_market_value?: string }>>>('/data/stock-info'),

  getIndustryDistribution: () => api.get<ApiResponse<Array<{ name: string; value: number }>>>('/data/industry-distribution'),

  getCoverageReport: () => api.get<ApiResponse<Record<string, unknown>[]>>('/data/coverage'),
}

export const pipelineApi = {
  getSteps: () => api.get<ApiResponse<PipelineStep[]>>('/pipeline/steps'),

  runStep: (stepId: string) => api.post<ApiResponse<PipelineStep>>(`/pipeline/run/${stepId}`),

  runAll: () => api.post<ApiResponse<PipelineStep[]>>('/pipeline/run-all'),
}

export const processApi = {
  finalizePartial: () => api.post<ApiResponse<{ output_files: string[] }>>('/process/finalize'),

  synthesizeIndex: () => api.post<ApiResponse<{ output_files: string[] }>>('/process/synthesize-index'),

  synthesizeSpot: () => api.post<ApiResponse<{ output_files: string[] }>>('/process/synthesize-spot'),
}
