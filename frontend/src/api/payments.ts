import api from './client'

export interface Payment {
  id: number
  client_id: number
  amount: number
  period_from: string
  period_to: string
  paid_at: string | null
  status: string
  method: string | null
}

export interface DashboardData {
  revenue: { current: number; prev: number; delta_pct: number }
  active_clients: number
  overdue_count: number
  lead_conversion: { total: number; converted: number; rate: number }
  funnel: { status: string; count: number }[]
  weekly_revenue: { week: string; amount: number }[]
  attendance_by_group: { group: string; rate: number }[]
}

export const getPayments = (params?: { status?: string }) =>
  api.get<Payment[]>('/payments', { params }).then((r) => r.data)

export const getOverdue = () =>
  api.get<Payment[]>('/payments/overdue').then((r) => r.data)

export const getDashboard = () =>
  api.get<DashboardData>('/payments/dashboard').then((r) => r.data)

export const createPayment = (data: {
  client_id: number
  amount: number
  period_from: string
  period_to: string
  method: string
}) => api.post<Payment>('/payments', data).then((r) => r.data)

export const getClientPayments = (clientId: number) =>
  api.get<Payment[]>(`/payments/clients/${clientId}`).then((r) => r.data)
