import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Table, Tag, Button, Typography, Space, Badge } from 'antd'
import { CheckSquareOutlined, ArrowRightOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { getLessons, Lesson } from '../../api/schedule'

const { Title, Text } = Typography

export default function TeacherHome() {
  const navigate = useNavigate()

  const { data: lessons = [], isLoading } = useQuery({
    queryKey: ['lessons'],
    queryFn: getLessons,
  })

  const now = dayjs()
  const upcoming = lessons
    .filter(l => dayjs(l.datetime).isAfter(now.subtract(2, 'hour')))
    .sort((a, b) => dayjs(a.datetime).valueOf() - dayjs(b.datetime).valueOf())

  const columns: ColumnsType<Lesson> = [
    {
      title: 'Дата',
      dataIndex: 'datetime',
      width: 100,
      render: (d: string) => {
        const dt = dayjs(d)
        const isToday = dt.isSame(now, 'day')
        return (
          <Space direction="vertical" size={0}>
            <Text strong={isToday} style={{ color: isToday ? '#52c41a' : undefined }}>
              {dt.format('DD MMM')}
            </Text>
            <Text type="secondary" style={{ fontSize: 12 }}>{dt.format('ddd')}</Text>
          </Space>
        )
      },
    },
    {
      title: 'Время',
      dataIndex: 'datetime',
      width: 80,
      render: (d: string) => {
        const dt = dayjs(d)
        const isNow = dt.isAfter(now.subtract(2, 'hour')) && dt.isBefore(now.add(2, 'hour'))
        return (
          <Text strong style={{ fontSize: 16, color: isNow ? '#52c41a' : undefined }}>
            {dt.format('HH:mm')}
          </Text>
        )
      },
    },
    {
      title: 'Группа',
      dataIndex: 'group_name',
      render: (name: string, record) => (
        <Button
          type="link"
          style={{ padding: 0, fontWeight: 600 }}
          onClick={() => navigate(`/teacher/groups/${record.group_id}`)}
        >
          {name ?? `Группа #${record.group_id}`}
        </Button>
      ),
    },
    {
      title: 'Аудитория',
      dataIndex: 'room',
      width: 110,
      render: (r: string | null) => r ? <Tag>{r}</Tag> : <Text type="secondary">—</Text>,
    },
    {
      title: 'Мест',
      dataIndex: 'capacity',
      width: 70,
      align: 'center',
    },
    {
      title: '',
      key: 'action',
      width: 130,
      render: (_: unknown, record) => {
        const dt = dayjs(record.datetime)
        const isActive = dt.isAfter(now.subtract(3, 'hour')) && dt.isBefore(now.add(1, 'hour'))
        return (
          <Space>
            <Button
              size="small"
              type={isActive ? 'primary' : 'default'}
              icon={<CheckSquareOutlined />}
              onClick={() => navigate(`/teacher/attendance?lesson=${record.id}`)}
            >
              Перекличка
            </Button>
          </Space>
        )
      },
    },
  ]

  // Group lessons by date for display
  const todayCount = upcoming.filter(l => dayjs(l.datetime).isSame(now, 'day')).length

  return (
    <div>
      <Space style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <Title level={3} style={{ margin: 0 }}>Моё расписание</Title>
          <Text type="secondary" style={{ textTransform: 'capitalize' }}>
            {now.format('dddd, D MMMM YYYY')}
            {todayCount > 0 && (
              <> · <Badge count={todayCount} color="#52c41a" /> сегодня</>
            )}
          </Text>
        </div>
        <Button
          icon={<ArrowRightOutlined />}
          onClick={() => navigate('/teacher/groups')}
        >
          Мои группы
        </Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={upcoming}
        loading={isLoading}
        size="middle"
        pagination={false}
        rowClassName={(record) =>
          dayjs(record.datetime).isSame(now, 'day') ? 'ant-table-row-selected' : ''
        }
        locale={{ emptyText: 'Предстоящих занятий нет' }}
      />
    </div>
  )
}
