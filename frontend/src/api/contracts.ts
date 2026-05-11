import api from './client'

export interface Contract {
  id: number
  client_id: number
  amount: number
  status: string
  created_at: string
  pdf_path: string | null
}

export const getContracts = () =>
  api.get<Contract[]>('/contracts').then((r) => r.data)

export const getContract = (id: number) =>
  api.get<Contract>(`/contracts/${id}`).then((r) => r.data)

export const signContract = (id: number) =>
  api.post(`/contracts/${id}/sign`).then((r) => r.data)

export const submitIntake = (data: {
  intake_token: string
  child_name: string
  child_birth_date: string
  parent_name: string
  parent_phone: string
  passport_data: string
  amount?: number
}) => api.post('/contracts/intake', data).then((r) => r.data)
