import { useEffect, useState } from 'react'
import { View, Text, FlatList, TouchableOpacity, Switch, StyleSheet, Alert, ActivityIndicator } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import axios from 'axios'
import { router } from 'expo-router'

const API_URL = 'http://10.0.2.2:8000/api/v1'  // Android emulator → host

const api = axios.create({ baseURL: API_URL })
api.interceptors.request.use(async (c) => {
  const token = await SecureStore.getItemAsync('token')
  if (token) c.headers.Authorization = `Bearer ${token}`
  return c
})

export default function TodayScreen() {
  const [lessons, setLessons] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    SecureStore.getItemAsync('token').then((t) => {
      if (!t) router.replace('/login')
    })
    api.get('/schedule/lessons').then((r) => {
      setLessons(r.data)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Мои занятия сегодня</Text>
      <FlatList
        data={lessons}
        keyExtractor={(item) => String(item.id)}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => router.push({ pathname: '/attendance', params: { lessonId: item.id, group: item.group_name } })}
          >
            <Text style={styles.group}>{item.group_name}</Text>
            <Text style={styles.time}>{new Date(item.datetime).toLocaleTimeString('ru', { hour: '2-digit', minute: '2-digit' })}</Text>
            {item.room && <Text style={styles.room}>Аудитория: {item.room}</Text>}
            <Text style={styles.action}>Начать перекличку →</Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={<Text style={styles.empty}>Занятий нет</Text>}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5', padding: 16 },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 16, color: '#1a1a2e' },
  card: { backgroundColor: '#fff', borderRadius: 12, padding: 16, marginBottom: 12, elevation: 2 },
  group: { fontSize: 16, fontWeight: '600' },
  time: { fontSize: 14, color: '#666', marginTop: 4 },
  room: { fontSize: 13, color: '#999', marginTop: 2 },
  action: { fontSize: 13, color: '#1677ff', marginTop: 8 },
  empty: { textAlign: 'center', color: '#999', marginTop: 40 },
})
