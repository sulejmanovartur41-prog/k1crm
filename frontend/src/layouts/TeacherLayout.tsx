import { Layout, Menu, Typography, Tag } from 'antd'
import {
  HomeOutlined,
  CalendarOutlined,
  TeamOutlined,
  CheckSquareOutlined,
} from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import UserMenu from './UserMenu'

const { Header, Sider, Content } = Layout
const { Text } = Typography

const MENU = [
  { key: '/teacher',            icon: <HomeOutlined />,         label: 'Расписание' },
  { key: '/teacher/groups',     icon: <TeamOutlined />,         label: 'Группы' },
  { key: '/teacher/attendance', icon: <CheckSquareOutlined />,  label: 'Журнал' },
  { key: '/teacher/schedule',   icon: <CalendarOutlined />,     label: 'Все занятия' },
]

export default function TeacherLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selected = MENU
    .map(m => m.key)
    .filter(k => location.pathname === k || location.pathname.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0] ?? '/teacher'

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider width={220} style={{ background: '#001529' }}>
        <div style={{ padding: '20px 16px 16px', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
          <Text style={{ color: '#fff', fontWeight: 700, fontSize: 16, display: 'block', lineHeight: 1.3 }}>
            KiberOne CRM
          </Text>
          <Text style={{ color: 'rgba(255,255,255,0.45)', fontSize: 11, letterSpacing: 1 }}>
            ПРЕПОДАВАТЕЛЬ
          </Text>
        </div>
        <Menu
          mode="inline"
          theme="dark"
          style={{ background: '#001529', borderRight: 0, paddingTop: 8 }}
          selectedKeys={[selected]}
          items={MENU}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid #f0f0f0',
          height: 56,
          lineHeight: '56px',
        }}>
          <Tag color="orange" style={{ margin: 0, fontWeight: 600 }}>Преподаватель</Tag>
          <UserMenu roleLabel="Преподаватель" />
        </Header>
        <Content style={{ margin: 24, padding: 24, background: '#fff', borderRadius: 6, minHeight: 280 }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  )
}
