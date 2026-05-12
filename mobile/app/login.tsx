import { useState } from 'react'
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import { router } from 'expo-router'
import { api } from '../api'

export default function LoginScreen() {
  const [login, setLogin] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const handleLogin = async () => {
    setLoading(true)
    try {
      const form = new URLSearchParams()
      form.append('username', login)
      form.append('password', password)
      const { data } = await api.post('/auth/login', form.toString(), {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      await SecureStore.setItemAsync('token', data.access_token)
      router.replace('/')
    } catch {
      Alert.alert('Ошибка', 'Неверный логин или пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <View style={styles.container}>
      <Text style={styles.title}>KiberOne</Text>
      <Text style={styles.subtitle}>Приложение преподавателя</Text>
      <TextInput style={styles.input} placeholder="Логин" value={login} onChangeText={setLogin} autoCapitalize="none" />
      <TextInput style={styles.input} placeholder="Пароль" value={password} onChangeText={setPassword} secureTextEntry />
      <TouchableOpacity style={styles.btn} onPress={handleLogin} disabled={loading}>
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.btnText}>Войти</Text>}
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 32, backgroundColor: '#1a1a2e' },
  title: { fontSize: 32, fontWeight: 'bold', color: '#fff', textAlign: 'center' },
  subtitle: { fontSize: 14, color: '#aaa', textAlign: 'center', marginBottom: 40 },
  input: { backgroundColor: '#fff', borderRadius: 8, padding: 14, marginBottom: 12, fontSize: 16 },
  btn: { backgroundColor: '#1677ff', borderRadius: 8, padding: 16, alignItems: 'center', marginTop: 8 },
  btnText: { color: '#fff', fontSize: 16, fontWeight: '600' },
})
