import { useEffect, useState } from 'react'
import { View, Text, FlatList, Switch, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native'
import { useLocalSearchParams, router } from 'expo-router'
import { api } from '../api'

export default function AttendanceScreen() {
  const { lessonId, group } = useLocalSearchParams<{ lessonId: string; group: string }>()
  const [students, setStudents] = useState<any[]>([])
  const [marks, setMarks] = useState<Record<number, boolean>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api.get(`/attendance/lessons/${lessonId}`).then((r) => {
      setStudents(r.data)
      const init: Record<number, boolean> = {}
      r.data.forEach((s: any) => { init[s.client_id] = s.present ?? false })
      setMarks(init)
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [lessonId])

  const handleSave = async () => {
    setSaving(true)
    try {
      await api.post(`/attendance/lessons/${lessonId}/mark`, {
        marks: Object.entries(marks).map(([id, present]) => ({ client_id: Number(id), present })),
      })
      const present = Object.values(marks).filter(Boolean).length
      router.push({ pathname: '/confirm', params: { present, total: students.length } })
    } catch {
      Alert.alert('Ошибка', 'Не удалось сохранить перекличку')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <ActivityIndicator style={{ flex: 1 }} size="large" />

  return (
    <View style={styles.container}>
      <Text style={styles.title}>{group}</Text>
      <Text style={styles.subtitle}>Отметьте присутствующих</Text>
      <FlatList
        data={students}
        keyExtractor={(item) => String(item.client_id)}
        renderItem={({ item }) => (
          <View style={styles.row}>
            <View>
              <Text style={styles.name}>{item.child_name}</Text>
              <Text style={styles.parent}>{item.parent_name}</Text>
            </View>
            <Switch
              value={marks[item.client_id] ?? false}
              onValueChange={(v) => setMarks((m) => ({ ...m, [item.client_id]: v }))}
              trackColor={{ true: '#52c41a' }}
            />
          </View>
        )}
      />
      <TouchableOpacity style={styles.btn} onPress={handleSave} disabled={saving}>
        <Text style={styles.btnText}>{saving ? 'Сохранение...' : 'Сохранить перекличку'}</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f5f5f5', padding: 16 },
  title: { fontSize: 20, fontWeight: 'bold', marginBottom: 4 },
  subtitle: { fontSize: 14, color: '#666', marginBottom: 16 },
  row: { backgroundColor: '#fff', borderRadius: 10, padding: 14, marginBottom: 8, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  name: { fontSize: 15, fontWeight: '500' },
  parent: { fontSize: 13, color: '#999' },
  btn: { backgroundColor: '#1677ff', borderRadius: 10, padding: 16, alignItems: 'center', marginTop: 16 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
})
