import axios from 'axios'

const BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export const api = axios.create({ baseURL: BASE })

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('fv_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('fv_token')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

export const authApi = {
  login: (username: string, password: string) => {
    const body = new URLSearchParams({ username, password })
    return api.post<{ access_token: string }>('/api/auth/login', body)
  },
  register: (username: string, password: string) =>
    api.post<{ access_token: string }>('/api/auth/register', { username, password }),
  me: () => api.get<{ username: string; role: string }>('/api/auth/me'),
}

export const inspectApi = {
  upload: (
    file: File,
    opts: { warehouse_id?: string; supplier_id?: string; storage_temp_c?: number; storage_humidity_pct?: number }
  ) => {
    const form = new FormData()
    form.append('file', file)
    if (opts.warehouse_id) form.append('warehouse_id', opts.warehouse_id)
    if (opts.supplier_id) form.append('supplier_id', opts.supplier_id)
    if (opts.storage_temp_c != null) form.append('storage_temp_c', String(opts.storage_temp_c))
    if (opts.storage_humidity_pct != null) form.append('storage_humidity_pct', String(opts.storage_humidity_pct))
    return api.post<InspectionResult>('/api/inspect', form)
  },
  history: (params?: { limit?: number; offset?: number; warehouse_id?: string }) =>
    api.get<InspectionRow[]>('/api/inspect/history', { params }),
  detail: (id: string) => api.get<InspectionDetail>(`/api/inspect/${id}`),
  overlayUrl: (id: string) => `${BASE}/api/inspect/overlay/${id}?token=${localStorage.getItem('fv_token')}`,
}

export const analyticsApi = {
  summary: (days = 30) => api.get<Analytics>('/api/analytics/summary', { params: { days } }),
  exportCsv: () => `${BASE}/api/analytics/export/csv`,
}

// ---- Types ---------------------------------------------------------------

export interface DefectFinding {
  label: string
  confidence: number
  area_ratio: number
  bbox: [number, number, number, number]
}

export interface InspectionItem {
  item_id: string
  product_type: string
  detection_confidence: number
  bbox: [number, number, number, number]
  defects: DefectFinding[]
  defect_coverage_pct: number
  quality_grade: string
  quality_score: number
  freshness_label: string
  freshness_pct: number
  shelf_life_days: number
  shelf_life_confidence: number
  decision: string
  decision_reasons: string[]
  explanation: string
}

export interface InspectionResult {
  inspection_id: string
  timestamp: string
  warehouse_id: string
  supplier_id: string | null
  items: InspectionItem[]
  overlay_url: string
  storage_temp_c: number
  storage_humidity_pct: number
}

export interface InspectionRow {
  inspection_id: string
  timestamp: string
  warehouse_id: string
  supplier_id: string | null
  item_count: number
  storage_temp_c: number
}

export interface InspectionDetail extends InspectionRow {
  items: InspectionItem[]
  overlay_path: string
}

export interface Analytics {
  total_inspections: number
  total_items: number
  avg_defect_coverage_pct: number
  rejected_count: number
  grade_distribution: Record<string, number>
  freshness_distribution: Record<string, number>
  decision_distribution: Record<string, number>
  recent_trend: Array<{ day: string; cnt: number; avg_quality: number }>
  by_supplier: Record<string, { total: number; avg_quality: number; rejected: number }>
  by_warehouse: Record<string, { total: number; avg_quality: number }>
}
