import api from './client'

export type GroupStatus = 'active' | 'archived'

export interface Group {
  id: number
  name: string
  level: string | null
  teacher_id: number | null
  room: string | null
  capacity: number
  color: string | null
  status: GroupStatus
  description: string | null
  created_at: string
}

export interface GroupListItem extends Group {
  students_count: number
  teacher_name: string | null
}

export interface GroupStudent {
  id: number
  child_name: string
  child_birth_date: string | null
  parent_name: string
  parent_phone: string
  status: string
  attendance_rate: number | null
  payment_status: string | null
}

export interface GroupLessonItem {
  id: number
  datetime: string
  room: string | null
  capacity: number
}

export interface GroupDetail extends Group {
  teacher_name: string | null
  students: GroupStudent[]
  upcoming_lessons: GroupLessonItem[]
}

export interface GroupCreate {
  name: string
  level?: string | null
  teacher_id?: number | null
  room?: string | null
  capacity?: number
  color?: string | null
  description?: string | null
}

export type GroupUpdate = Partial<GroupCreate> & { status?: GroupStatus }

export const listGroups = (status?: GroupStatus) =>
  api.get<GroupListItem[]>('/groups', { params: status ? { status } : undefined }).then((r) => r.data)

export const getGroup = (id: number) =>
  api.get<GroupDetail>(`/groups/${id}`).then((r) => r.data)

export const createGroup = (data: GroupCreate) =>
  api.post<Group>('/groups', data).then((r) => r.data)

export const updateGroup = (id: number, data: GroupUpdate) =>
  api.patch<Group>(`/groups/${id}`, data).then((r) => r.data)

export const addStudentToGroup = (groupId: number, clientId: number) =>
  api.post<void>(`/groups/${groupId}/students/${clientId}`).then((r) => r.data)

export const removeStudentFromGroup = (groupId: number, clientId: number) =>
  api.delete<void>(`/groups/${groupId}/students/${clientId}`).then((r) => r.data)

export interface ScheduleGenRequest {
  weekdays: number[]
  time: string
  weeks: number
  start_date?: string
}

export const generateSchedule = (groupId: number, data: ScheduleGenRequest) =>
  api.post<{ created: number; skipped: string[] }>(`/groups/${groupId}/schedule`, data).then((r) => r.data)
