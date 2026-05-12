import { Layout, Typography, ConfigProvider, Segmented } from 'antd'
import { ReadOutlined } from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import UserMenu from './UserMenu'

const { Header, Content } = Layout
const { Title } = Typography

const PRIMARY = '#52c41a'

const TABS = [
  { value: '/teacher',            label: 'Сегодня' },
  { value: '/teacher/schedule',   label: 'Расписание' },
  { value: '/teacher/groups',     label: 'Группы' },
  { value: '/teacher/attendance', label: 'Журнал' },
]

export default function TeacherLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selected = TABS
    .map(t => t.value)
    .filter(v => location.pathname === v || location.pathname.startsWith(v + '/'))
    .sort((a, b) => b.length - a.length)[0] ?? '/teacher'

  return (
    <ConfigProvider theme={{ token: { colorPrimary: PRIMARY, borderRadius: 12 } }}>
      <Layout style={{ minHeight: '100vh', background: '#f6fff0' }}>
        <Header style={{
          background: '#fff',
          padding: '0 24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          boxShadow: '0 1px 2px rgba(0,0,0,0.04)',
          height: 64,
        }}>
          <Title level={4} style={{ margin: 0, color: PRIMARY }}>
            <ReadOutlined /> KiberOne · Преподаватель
          </Title>
          <UserMenu roleLabel="Преподаватель" />
        </Header>
        <div style={{ background: '#fff', padding: '16px 24px', borderBottom: '1px solid #f0f0f0' }}>
          <Segmented
            size="large"
            options={TABS}
            value={selected}
            onChange={(v) => navigate(String(v))}
            block
          />
        </div>
        <Content style={{ margin: 24 }}>
          <Outlet />
        </Content>
      </Layout>
    </ConfigProvider>
  )
}
