import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

export interface ApiResponse<T> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface DownloadTask {
  id: string
  status: 'pending' | 'running' | 'success' | 'error'
  progress: number
  stage: string
  message: string
  startTime?: string
  endTime?: string
}

export interface DataStats {
  nConstituents: number
  nStockDaily: number
  nIndexDaily: number
  nStockInfo: number
  nFundamental: number
  coverageRatio: number
  dateRange: { start: string; end: string }
}

export interface PipelineStep {
  id: string
  name: string
  description: string
  status: 'pending' | 'running' | 'success' | 'error' | 'skipped'
  progress: number
  output?: string[]
  logs: string[]
}

export interface StockData {
  date: string
  stock_code: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount: number
  pct_change?: number
  turnover_rate?: number
  [key: string]: unknown
}

export interface IndexData {
  date: string
  open: number
  close: number
  high: number
  low: number
  volume: number
  amount: number
  [key: string]: unknown
}

export default api
