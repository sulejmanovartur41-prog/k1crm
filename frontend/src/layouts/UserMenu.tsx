import { Button, Space, Typography } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { getName, logout } from '../auth'

const { Text } = Typography

interface Props {
  roleLabel: string
  invertedText?: boolean
}

export default function UserMenu({ roleLabel, invertedText = false }: Props) {
  const navigate = useNavigate()
  const name = getName()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const textStyle = invertedText ? { color: 'rgba(255,255,255,0.85)' } : undefined

  return (
    <Space size="middle">
      <Text style={textStyle}>
        {name} · <Text strong style={textStyle}>{roleLabel}</Text>
      </Text>
      <Button icon={<LogoutOutlined />} onClick={handleLogout}>
        Выйти
      </Button>
    </Space>
  )
}
