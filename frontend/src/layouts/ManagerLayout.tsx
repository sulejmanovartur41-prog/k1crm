import { Layout, Menu, Typography, Button, ConfigProvider } from 'antd'
import { PlusOutlined, FundOutlined } from '@ant-design/icons'
import { Outlet, useNavigate, useLocation } from 'react-router-dom'
import UserMenu from './UserMenu'

const { Header, Content } = Layout
const { Title } = Typography

const PRIMARY = '#1677ff'

const MENU = [
  { key: '/manager',           label: 'Воронка' },
  { key: '/manager/leads',     label: 'Лиды' },
  { key: '/manager/groups',    label: 'Группы' },
  { key: '/manager/schedule',  label: 'Расписание' },
  { key: '/manager/contracts', label: 'Договора' },
]

export default function ManagerLayout() {
  const navigate = useNavigate()
  const location = useLocation()

  const selected = MENU
    .map(m => m.key)
    .filter(k => location.pathname === k || location.pathname.startsWith(k + '/'))
    .sort((a, b) => b.length - a.length)[0] ?? '/manager'

  return (
    <ConfigProvider theme={{ token: { colorPrimary: PRIMARY } }}>
      <Layout style={{ minHeight: '100vh', background: '#f5f7fa' }}>
        <Header style={{
          background: `linear-gradient(90deg, ${PRIMARY} 0%, #4096ff 100%)`,
          padding: '0 32px',
          display: 'flex',
          alignItems: 'center',
          gap: 32,
          height: 64,
        }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: 12 }}>
            <Title level={4} style={{ color: '#fff', margin: 0 }}>
              <FundOutlined /> KiberOne
            </Title>
            <span style={{ color: 'rgba(255,255,255,0.75)', fontSize: 12, letterSpacing: 1 }}>
              · ОТДЕЛ ПРОДАЖ
            </span>
          </div>
          <Menu
            mode="horizontal"
            theme="dark"
            selectedKeys={[selected]}
            items={MENU}
            onClick={({ key }) => navigate(key)}
            style={{
              flex: 1,
              background: 'transparent',
              borderBottom: 'none',
              fontSize: 14,
            }}
          />
          <Button
            type="default"
            icon={<PlusOutlined />}
            onClick={() => navigate('/manager/leads?new=1')}
          >
            Новый лид
          </Button>
          <UserMenu roleLabel="Менеджер" invertedText />
        </Header>
        <Content style={{ margin: '24px 32px' }}>
          <Outlet />
        </Content>
      </Layout>
    </ConfigProvider>
  )
}
