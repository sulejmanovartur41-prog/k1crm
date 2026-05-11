import api from './client'

export interface Lesson {
  id: number
  group_name: string
  teacher_id: number
  datetime: string
  room: string | null
  capacity: number
}

export interface Booking {
  id: number
  lead_id: number
  lesson_id: number
  status: string
  intake_token: string | null
}

export const getLessons = () =>
  api.get<Lesson[]>('/schedule/lessons').then((r) => r.data)

export const createLesson = (data: Omit<Lesson, 'id'>) =>
  api.post<Lesson>('/schedule/lessons', data).then((r) => r.data)

export const getSlots = (lessonId: number) =>
  api.get(`/schedule/lessons/${lessonId}/slots`).then((r) => r.data)

export const createBooking = (data: { lead_id: number; lesson_id: number }) =>
  api.post<Booking>('/schedule/bookings', data).then((r) => r.data)

export const updateBooking = (bookingId: number, status: string) =>
  api.patch(`/schedule/bookings/${bookingId}`, null, { params: { status } }).then((r) => r.data)
