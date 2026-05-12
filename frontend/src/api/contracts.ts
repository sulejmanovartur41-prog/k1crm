import { message } from 'antd'
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

function triggerBlobDownload(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.style.display = 'none'
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url) }, 100)
}

export async function downloadContractPdf(contractId: number) {
  try {
    const res = await api.get(`/contracts/${contractId}/download`, { responseType: 'blob' })
    triggerBlobDownload(new Blob([res.data], { type: 'application/pdf' }), `contract_${contractId}.pdf`)
  } catch {
    message.error('Не удалось скачать PDF')
  }
}

export async function generateAndDownloadPdf(contractId: number) {
  try {
    message.loading({ content: 'Формируем PDF...', key: 'pdf' })
    const res = await api.post(`/contracts/${contractId}/generate-pdf`, null, { responseType: 'blob' })
    triggerBlobDownload(new Blob([res.data], { type: 'application/pdf' }), `contract_${contractId}.pdf`)
    message.success({ content: 'PDF готов', key: 'pdf' })
  } catch {
    message.error({ content: 'Ошибка формирования PDF', key: 'pdf' })
  }
}

// amount намеренно не передаётся: сервер берёт сумму из настроек.
export const submitIntake = (data: {
  intake_token: string
  child_name: string
  child_birth_date: string
  parent_name: string
  parent_phone: string
  passport_data: string
}) => api.post('/contracts/intake', data).then((r) => r.data)
