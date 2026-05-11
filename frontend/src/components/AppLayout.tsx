import { Layout, Menu, Button, Typography } from 'antd'
import {
  UserOutlined,
  CalendarOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  BarChartOutlined,
  LogoutOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'

const { Header, Sider, Content } = Layout
const { Title } = Typography

const menuItems = [
  { key: '/leads', icon: <UserOutlined />, label: 'Лиды / CRM' },
  { key: '/schedule', icon: <CalendarOutlined />, label: 'Расписание' },
  { key: '/contracts', icon: <FileTextOutlined />, label: 'Договора' },
  { key: '/attendance', icon: <CheckSquareOutlined />, label: 'Посещаемость' },
  { key: '/dashboard', icon: <BarChartOutlined />, label: 'Дашборд' },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = () => {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220} theme="dark">
        <div style={{ padding: '16px', color: '#fff', textAlign: 'center' }}>
          <Title level={4} style={{ color: '#fff', margin: 0 }}>
            KiberOne CRM
          </Title>
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{ background: '#fff', padding: '0 24px', display: 'flex', justifyContent: 'flex-end', alignItems: 'center' }}>
          <Button icon={<LogoutOutlined />} onClick={handleLogout}>
            Выйти
          </Button>
        </Header>
        <Content style={{ margin: '24px', minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
