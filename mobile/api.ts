// Общий axios-клиент для мобильного приложения.
// Базовый URL — из env (EXPO_PUBLIC_API_URL), с fallback на Android-эмулятор для dev.
// При 401 — чистим токен и редиректим на /login.

import axios from 'axios'
import * as SecureStore from 'expo-secure-store'
import { router } from 'expo-router'

const API_URL =
  process.env.EXPO_PUBLIC_API_URL?.replace(/\/$/, '') ?? 'http://10.0.2.2:8000/api/v1'

export const api = axios.create({ baseURL: API_URL })

api.interceptors.request.use(async (c) => {
  const token = await SecureStore.getItemAsync('token')
  if (token) c.headers.Authorization = `Bearer ${token}`
  return c
})

api.interceptors.response.use(
  (r) => r,
  async (err) => {
    if (err.response?.status === 401) {
      await SecureStore.deleteItemAsync('token').catch(() => {})
      router.replace('/login')
    }
    return Promise.reject(err)
  },
)

export const API_BASE_URL = API_URL
