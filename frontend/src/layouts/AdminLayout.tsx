import { Layout, Menu, Typography, ConfigProvider, theme } from 'antd'
import {
  DashboardOutlined,
  UserOutlined,
  CalendarOutlined,
  FileTextOutlined,
  CheckSquareOutlined,
  SafetyCertificateOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import UserMenu from './UserMenu'

const { Header, Sider, Content } = Layout
const { Title, Text } = Typography

const PRIMARY = '#722ed1'

const MENU = [
  { key: '/admin',            icon: <DashboardOutlined />,        label: 'Дашборд' },
  { key: '/admin/leads',      icon: <UserOutlined />,             label: 'Лиды' },
  { key: '/admin/groups',     icon: <TeamOutlined />,             label: 'Группы' },
  { key: '/admin/schedule',   icon: <CalendarOutlined />,         label: 'Расписание' },
  { key: '/admin/contracts',  icon: <FileTextOutlined />,         label: 'Договора' },
  { key: '/admin/attendance', icon: <CheckSquareOutlined />,      label: 'Посещаемость' },
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selected = MENU
    .map(m => m.key)
    .filter(k => location.pathname === k || location.pathname.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0] ?? '/admin'

  return (
    <ConfigProvider theme={{ token: { colorPrimary: PRIMARY } }}>
      <Layout style={{ minHeight: '100vh' }}>
        <Sider
          width={240}
          style={{ background: '#1a1325' }}
        >
          <div style={{ padding: '20px 16px', borderBottom: '1px solid #2d2240' }}>
            <Title level={4} style={{ color: '#fff', margin: 0, lineHeight: 1.2 }}>
              KiberOne CRM
            </Title>
            <Text style={{ color: PRIMARY, fontSize: 11, letterSpacing: 1.5, fontWeight: 600 }}>
              ADMIN PANEL
            </Text>
          </div>
          <Menu
            mode="inline"
            theme="dark"
            style={{ background: '#1a1325', borderRight: 0, paddingTop: 12 }}
            selectedKeys={[selected]}
            items={MENU}
            onClick={({ key }) => navigate(key)}
          />
        </Sider>
        <Layout>
          <Header style={{
            background: '#fff',
            padding: '0 32px',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            borderBottom: `3px solid ${PRIMARY}`,
          }}>
            <Title level={5} style={{ margin: 0, color: PRIMARY }}>
              <SafetyCertificateOutlined /> Администратор
            </Title>
            <UserMenu roleLabel="Администратор" />
          </Header>
          <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 8 }}>
            <Outlet />
          </Content>
        </Layout>
      </Layout>
    </ConfigProvider>
  )
}
