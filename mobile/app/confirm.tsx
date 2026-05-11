import { View, Text, TouchableOpacity, StyleSheet } from 'react-native'
import { useLocalSearchParams, router } from 'expo-router'

export default function ConfirmScreen() {
  const { present, total } = useLocalSearchParams<{ present: string; total: string }>()
  return (
    <View style={styles.container}>
      <Text style={styles.emoji}>✅</Text>
      <Text style={styles.title}>Перекличка сохранена!</Text>
      <Text style={styles.count}>{present} из {total} присутствовало</Text>
      <TouchableOpacity style={styles.btn} onPress={() => router.replace('/')}>
        <Text style={styles.btnText}>На главную</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: '#f5f5f5', padding: 32 },
  emoji: { fontSize: 64, marginBottom: 16 },
  title: { fontSize: 24, fontWeight: 'bold', marginBottom: 8 },
  count: { fontSize: 18, color: '#666', marginBottom: 40 },
  btn: { backgroundColor: '#1677ff', borderRadius: 10, paddingVertical: 14, paddingHorizontal: 40 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
})
