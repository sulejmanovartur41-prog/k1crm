import api from './client'

export interface Lead {
  id: number
  name: string
  phone: string
  source: string
  status: string
  attempt_count: number
  escalated: boolean
  message_text?: string
  created_at: string
}

export const getLeads = (params?: { status?: string; source?: string }) =>
  api.get<Lead[]>('/leads', { params }).then((r) => r.data)

export const getLead = (id: number) =>
  api.get<Lead>(`/leads/${id}`).then((r) => r.data)

export const createLead = (data: Partial<Lead>) =>
  api.post<Lead>('/leads', data).then((r) => r.data)

export const updateLeadStatus = (id: number, status: string, refusal_reason?: string) =>
  api.patch(`/leads/${id}/status`, { status, refusal_reason }).then((r) => r.data)

export const getLeadsStats = () =>
  api.get('/leads/stats').then((r) => r.data)
