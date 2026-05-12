import api from './client'

export interface PaymentItem {
  id: number
  amount: number
  period_from: string
  period_to: string
  status: string
  method: string | null
  paid_at: string | null
}

export interface AttendanceItem {
  lesson_id: number
  lesson_datetime: string
  present: boolean
}

export interface ContractInfo {
  id: number
  status: string
  amount: number
  signed_at: string | null
  pdf_path: string | null
}

export interface ClientDetails {
  id: number
  child_name: string
  child_birth_date: string
  parent_name: string
  parent_phone: string
  passport_data: string | null
  status: string
  group_id: number | null
  created_at: string
  payments: PaymentItem[]
  attendance: AttendanceItem[]
  contract: ContractInfo | null
}

export const getClientDetails = (id: number) =>
  api.get<ClientDetails>(`/clients/${id}/details`).then((r) => r.data)
