import api from './client'

export interface AttendanceStudent {
  client_id: number
  child_name: string
  parent_name: string
  present: boolean | null
}

export const getLessonStudents = (lessonId: number) =>
  api.get<AttendanceStudent[]>(`/attendance/lessons/${lessonId}`).then((r) => r.data)

export const markAttendance = (
  lessonId: number,
  marks: { client_id: number; present: boolean }[]
) =>
  api.post(`/attendance/lessons/${lessonId}/mark`, { marks }).then((r) => r.data)

export const getClientAttendance = (clientId: number) =>
  api.get(`/attendance/clients/${clientId}`).then((r) => r.data)
