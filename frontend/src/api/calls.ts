import api from './client'

export interface CallTask {
  id: number
  lead_id: number
  attempts: number
  escalated: boolean
  completed: boolean
  next_call_at: string | null
}

export const getCallTasks = () =>
  api.get<CallTask[]>('/calls/tasks').then((r) => r.data)

export const getCallTask = (id: number) =>
  api.get<CallTask>(`/calls/tasks/${id}`).then((r) => r.data)

export const registerAttempt = (
  taskId: number,
  data: { result: string; outcome?: string; refusal_reason?: string }
) => api.post(`/calls/tasks/${taskId}/attempt`, data).then((r) => r.data)

export const initiateCall = (from_number: string, to_number: string) =>
  api.post('/calls/zadarma/initiate', { from_number, to_number }).then((r) => r.data)
