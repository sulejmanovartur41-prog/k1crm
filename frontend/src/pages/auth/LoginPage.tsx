import { Form, Input, Button, Card, Typography, message } from 'antd'
import { useNavigate } from 'react-router-dom'
import api from '../../api/client'

const { Title } = Typography

export default function LoginPage() {
  const navigate = useNavigate()

  const onFinish = async (values: { username: string; password: string }) => {
    try {
      const form = new URLSearchParams()
      form.append('username', values.username)
      form.append('password', values.password)
      const { data } = await api.post('/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      localStorage.setItem('token', data.access_token)
      localStorage.setItem('role', data.role)
      localStorage.setItem('name', data.name)
      navigate('/')
    } catch {
      message.error('Неверный логин или пароль')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh', background: '#f0f2f5' }}>
      <Card style={{ width: 380 }}>
        <Title level={3} style={{ textAlign: 'center', marginBottom: 24 }}>
          KiberOne CRM
        </Title>
        <Form onFinish={onFinish} layout="vertical">
          <Form.Item name="username" label="Логин" rules={[{ required: true }]}>
            <Input size="large" placeholder="admin / manager / teacher" />
          </Form.Item>
          <Form.Item name="password" label="Пароль" rules={[{ required: true }]}>
            <Input.Password size="large" />
          </Form.Item>
          <Button type="primary" htmlType="submit" block size="large">
            Войти
          </Button>
        </Form>
      </Card>
    </div>
  )
}
