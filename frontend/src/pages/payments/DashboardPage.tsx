import { useQuery } from '@tanstack/react-query'
import { Row, Col, Card, Statistic, Typography, Table, Button, Spin } from 'antd'
import { DownloadOutlined, ArrowUpOutlined, ArrowDownOutlined } from '@ant-design/icons'
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, AreaChart, Area, Legend,
} from 'recharts'
import { getDashboard, getOverdue } from '../../api/payments'

const { Title } = Typography

function exportToExcel(data: any[], filename: string) {
  import('xlsx').then((XLSX) => {
    const ws = XLSX.utils.json_to_sheet(data)
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, ws, 'Данные')
    XLSX.writeFile(wb, `${filename}.xlsx`)
  })
}

export default function DashboardPage() {
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: getDashboard,
  })

  const { data: overdue = [] } = useQuery({
    queryKey: ['overdue'],
    queryFn: getOverdue,
  })

  if (isLoading) return <Spin size="large" style={{ marginTop: 100, display: 'block', textAlign: 'center' }} />

  const revDelta = data?.revenue?.delta_pct ?? 0

  const overdueColumns = [
    { title: 'Клиент ID', dataIndex: 'client_id' },
    { title: 'Сумма', dataIndex: 'amount', render: (v: number) => `${Number(v).toLocaleString('ru')} ₽` },
    { title: 'Статус', dataIndex: 'status' },
    {
      title: 'Период до',
      dataIndex: 'period_to',
      render: (d: string) => new Date(d).toLocaleDateString('ru'),
    },
  ]

  return (
    <div>
      <Title level={3}>Дашборд руководителя</Title>

      {/* KPI cards */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
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
            <div style={{ fontSize: 12, color: revDelta >= 0 ? '#3f8600' : '#cf1322' }}>
              {revDelta >= 0 ? '+' : ''}{revDelta}% к прошлому месяцу
            </div>
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic title="Активные ученики" value={data?.active_clients} />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Должники"
              value={data?.overdue_count}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
        <Col span={6}>
          <Card>
            <Statistic
              title="Конверсия лидов"
              value={((data?.lead_conversion?.rate ?? 0) * 100).toFixed(1)}
              suffix="%"
            />
            <div style={{ fontSize: 12, color: '#666' }}>
              {data?.lead_conversion?.converted} из {data?.lead_conversion?.total}
            </div>
          </Card>
        </Col>
      </Row>

      {/* Funnel */}
      {data?.funnel && data.funnel.length > 0 && (
        <Card title="Воронка лидов" style={{ marginBottom: 24 }}>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={data.funnel}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="status" />
              <YAxis allowDecimals={false} />
              <Tooltip />
              <Bar dataKey="count" fill="#1677ff" name="Лидов" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Weekly revenue */}
      {data?.weekly_revenue && data.weekly_revenue.length > 0 && (
        <Card title="Выручка по неделям (последние 12 недель)" style={{ marginBottom: 24 }}>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.weekly_revenue}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="week" tick={{ fontSize: 11 }} />
              <YAxis />
              <Tooltip formatter={(v: number) => [`${v.toLocaleString('ru')} ₽`, 'Выручка']} />
              <Legend />
              <Line type="monotone" dataKey="amount" stroke="#52c41a" name="Выручка, ₽" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Attendance by group */}
      {data?.attendance_by_group && data.attendance_by_group.length > 0 && (
        <Card title="Посещаемость по группам (30 дней)" style={{ marginBottom: 24 }}>
          <ResponsiveContainer width="100%" height={200}>
            <AreaChart data={data.attendance_by_group}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="group" />
              <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} domain={[0, 1]} />
              <Tooltip formatter={(v: number) => [`${(v * 100).toFixed(0)}%`, 'Посещаемость']} />
              <Area type="monotone" dataKey="rate" stroke="#722ed1" fill="#d3adf7" name="Посещаемость" />
            </AreaChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* Overdue table */}
      <Card
        title="Должники"
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
        />
      </Card>
    </div>
  )
}
