import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Row, Col, Card, Statistic, Typography, Table, Button, Spin, Space } from 'antd'
import {
  DownloadOutlined, ArrowUpOutlined, ArrowDownOutlined,
  UserOutlined, WarningOutlined, TeamOutlined, FundOutlined,
} from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area, Legend, Cell,
} from 'recharts'
import { getDashboard, getOverdue } from '../../api/payments'
import ClientDetailDrawer from '../../components/ClientDetailDrawer'

const { Title } = Typography

const STATUS_LABELS: Record<string, string> = {
  new: 'Новые',
  calling: 'Звонок',
  called: 'Обзвонены',
  in_doubt: 'В раздумьях',
  enrolled: 'Записаны',
  refused: 'Отказ',
  archived: 'Архив',
}

const FUNNEL_COLORS: Record<string, string> = {
  new: '#1677ff',
  calling: '#fa8c16',
  called: '#fa8c16',
  in_doubt: '#faad14',
  enrolled: '#52c41a',
  refused: '#ff4d4f',
  archived: '#d9d9d9',
}

function exportToExcel(data: any[], filename: string) {
  import('xlsx').then((XLSX) => {
    const ws = XLSX.utils.json_to_sheet(data)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Данные')
    XLSX.writeFile(wb, `${filename}.xlsx`)
  })
}

export default function DashboardPage() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({ queryKey: ['dashboard'], queryFn: getDashboard })
  const { data: overdue = [] } = useQuery({ queryKey: ['overdue'], queryFn: getOverdue })
  const [drawerClientId, setDrawerClientId] = useState<number | null>(null)

  if (isLoading) return <Spin size="large" style={{ marginTop: 100, display: 'block', textAlign: 'center' }} />

  const revDelta = data?.revenue?.delta_pct ?? 0

  const overdueColumns = [
    {
      title: 'Ученик',
      dataIndex: 'client_id',
      render: (id: number) => (
        <Button type="link" style={{ padding: 0 }} onClick={() => setDrawerClientId(id)}>
          Клиент #{id}
        </Button>
      ),
    },
    {
      title: 'Сумма долга',
      dataIndex: 'amount',
      render: (v: number) => <span style={{ color: '#ff4d4f', fontWeight: 600 }}>{Number(v).toLocaleString('ru')} ₽</span>,
    },
    {
      title: 'Просрочено до',
      dataIndex: 'period_to',
      render: (d: string) => new Date(d).toLocaleDateString('ru'),
    },
    {
      title: '',
      render: (_: unknown, row: any) => (
        <Button size="small" onClick={() => setDrawerClientId(row.client_id)}>
          Открыть карточку
        </Button>
      ),
    },
  ]

  const funnelData = (data?.funnel ?? []).map(f => ({
    ...f,
    label: STATUS_LABELS[f.status] ?? f.status,
  }))

  return (
    <div>
      <Title level={3}>Дашборд</Title>

      {/* KPI */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={6}>
          <Card
            hoverable
            onClick={() => navigate('/admin/leads')}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Конверсия лидов"
              value={((data?.lead_conversion?.rate ?? 0) * 100).toFixed(1)}
              suffix="%"
              prefix={<FundOutlined style={{ color: '#1677ff' }} />}
            />
            <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
              {data?.lead_conversion?.converted} записаны из {data?.lead_conversion?.total} · <span style={{ color: '#1677ff' }}>Перейти к лидам →</span>
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card
            hoverable
            onClick={() => navigate('/admin/groups')}
            style={{ cursor: 'pointer' }}
          >
            <Statistic
              title="Активные ученики"
              value={data?.active_clients}
              prefix={<TeamOutlined style={{ color: '#52c41a' }} />}
            />
            <div style={{ fontSize: 12, color: '#1677ff', marginTop: 4 }}>Перейти к группам →</div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Выручка за месяц"
              value={data?.revenue?.current?.toLocaleString('ru')}
              suffix="₽"
              prefix={
                revDelta >= 0
                  ? <ArrowUpOutlined style={{ color: '#3f8600' }} />
                  : <ArrowDownOutlined style={{ color: '#cf1322' }} />
              }
            />
            <div style={{ fontSize: 12, color: revDelta >= 0 ? '#3f8600' : '#cf1322', marginTop: 4 }}>
              {revDelta >= 0 ? '+' : ''}{revDelta}% к прошлому месяцу
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card
            hoverable
            style={{ cursor: 'pointer', borderColor: (data?.overdue_count ?? 0) > 0 ? '#ff4d4f' : undefined }}
            onClick={() => document.getElementById('overdue-section')?.scrollIntoView({ behavior: 'smooth' })}
          >
            <Statistic
              title="Должники"
              value={data?.overdue_count ?? 0}
              valueStyle={{ color: (data?.overdue_count ?? 0) > 0 ? '#cf1322' : undefined }}
              prefix={<WarningOutlined style={{ color: '#ff4d4f' }} />}
            />
            <div style={{ fontSize: 12, color: '#ff4d4f', marginTop: 4 }}>
              {(data?.overdue_count ?? 0) > 0 ? 'Требуют внимания ↓' : 'Долгов нет'}
            </div>
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        {/* Funnel */}
        {funnelData.length > 0 && (
          <Col span={12}>
            <Card
              title="Воронка лидов"
              extra={<Button size="small" onClick={() => navigate('/admin/leads')}>Все лиды →</Button>}
            >
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={funnelData} style={{ cursor: 'pointer' }}
                  onClick={(e) => {
                    if (e?.activePayload?.[0]) {
                      const status = e.activePayload[0].payload.status
                      navigate(`/admin/leads?status=${status}`)
                    }
                  }}
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip
                    formatter={(v: number) => [v, 'Лидов']}
                    labelFormatter={(label) => label}
                  />
                  <Bar dataKey="count" name="Лидов" radius={[3, 3, 0, 0]}>
                    {funnelData.map((entry, i) => (
                      <Cell key={i} fill={FUNNEL_COLORS[entry.status] ?? '#1677ff'} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        )}

        {/* Attendance */}
        {data?.attendance_by_group && data.attendance_by_group.length > 0 && (
          <Col span={12}>
            <Card
              title="Посещаемость по группам (30 дней)"
              extra={<Button size="small" onClick={() => navigate('/admin/groups')}>Все группы →</Button>}
            >
              <ResponsiveContainer width="100%" height={220}>
                <AreaChart data={data.attendance_by_group}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="group" tick={{ fontSize: 11 }} />
                  <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
                  <Tooltip formatter={(v: number) => [`${(v * 100).toFixed(0)}%`, 'Посещаемость']} />
                  <Area type="monotone" dataKey="rate" stroke="#1677ff" fill="#bae0ff" name="Посещаемость" />
                </AreaChart>
              </ResponsiveContainer>
            </Card>
          </Col>
        )}
      </Row>

      {/* Weekly revenue */}
      {data?.weekly_revenue && data.weekly_revenue.length > 0 && (
        <Card title="Выручка по неделям" style={{ marginBottom: 24 }}>
          <ResponsiveContainer width="100%" height={200}>
            <LineChart data={data.weekly_revenue}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis tickFormatter={(v) => `${(v / 1000).toFixed(0)}т`} />
              <Tooltip formatter={(v: number) => [`${v.toLocaleString('ru')} ₽`, 'Выручка']} />
              <Legend formatter={() => 'Выручка, ₽'} />
              <Line type="monotone" dataKey="amount" stroke="#1677ff" name="Выручка" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Overdue table */}
      <Card
        id="overdue-section"
        title={
          <Space>
            <WarningOutlined style={{ color: '#ff4d4f' }} />
            Должники ({overdue.length})
          </Space>
        }
        extra={
          <Button
            icon={<DownloadOutlined />}
            size="small"
            onClick={() => exportToExcel(overdue, 'должники')}
          >
            Экспорт Excel
          </Button>
        }
      >
        <Table
          rowKey="id"
          columns={overdueColumns}
          dataSource={overdue}
          size="small"
          pagination={false}
          locale={{ emptyText: 'Должников нет' }}
          onRow={(record) => ({
            style: { cursor: 'pointer' },
            onClick: () => setDrawerClientId(record.client_id),
          })}
        />
      </Card>

      <ClientDetailDrawer
        clientId={drawerClientId}
        onClose={() => setDrawerClientId(null)}
      />
    </div>
  )
}
