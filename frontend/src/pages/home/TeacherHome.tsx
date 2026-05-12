import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Row, Col, Card, Typography, Empty, Button, Statistic, Space, Tag } from 'antd'
import { CheckSquareOutlined, ClockCircleOutlined, TeamOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getLessons, Lesson } from '../../api/schedule'

const { Title, Text } = Typography

export default function TeacherHome() {
  const navigate = useNavigate()

  const { data: lessons = [] } = useQuery({ queryKey: ['lessons'], queryFn: getLessons })

  const today = dayjs().startOf('day')
  const tomorrow = today.add(1, 'day')
  const todayLessons: Lesson[] = lessons
    .filter(l => dayjs(l.datetime).isAfter(today) && dayjs(l.datetime).isBefore(tomorrow))
    .sort((a, b) => dayjs(a.datetime).valueOf() - dayjs(b.datetime).valueOf())

  const nextLesson = todayLessons.find(l => dayjs(l.datetime).isAfter(dayjs()))

  return (
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>Сегодня</Title>
      <Text type="secondary" style={{ textTransform: 'capitalize' }}>
        {dayjs().format('dddd, D MMMM YYYY')}
      </Text>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="Уроков сегодня"
              value={todayLessons.length}
              prefix={<ClockCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12}>
          <Card>
            <Statistic
              title="Следующий урок"
              value={nextLesson ? dayjs(nextLesson.datetime).format('HH:mm') : '—'}
              suffix={nextLesson ? `· ${nextLesson.group_name}` : undefined}
              prefix={<TeamOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Card title="Уроки на сегодня" style={{ marginTop: 16 }}>
        {todayLessons.length === 0 ? (
          <Empty description="На сегодня уроков нет" />
        ) : (
          <Space direction="vertical" style={{ width: '100%' }} size="middle">
            {todayLessons.map(l => {
              const start = dayjs(l.datetime)
              const isPast = start.isBefore(dayjs())
              return (
                <Card
                  key={l.id}
                  size="small"
                  style={{ background: isPast ? '#fafafa' : '#fff', borderColor: isPast ? '#f0f0f0' : '#b7eb8f' }}
                >
                  <Row align="middle" gutter={16}>
                    <Col flex="80px">
                      <Title level={3} style={{ margin: 0, color: isPast ? '#999' : '#52c41a' }}>
                        {start.format('HH:mm')}
                      </Title>
                    </Col>
                    <Col flex="auto">
                      <Space direction="vertical" size={2}>
                        <Text strong style={{ fontSize: 16 }}>{l.group_name}</Text>
                        <Space size="small">
                          {l.room && <Tag>Ауд. {l.room}</Tag>}
                          <Tag color="default">мест {l.capacity}</Tag>
                          {isPast && <Tag color="default">завершён</Tag>}
                        </Space>
                      </Space>
                    </Col>
                    <Col>
                      <Button
                        type="primary"
                        icon={<CheckSquareOutlined />}
                        onClick={() => navigate(`/teacher/attendance?lesson=${l.id}`)}
                      >
                        Перекличка
                      </Button>
                    </Col>
                  </Row>
                </Card>
              )
            })}
          </Space>
        )}
      </Card>
    </div>
  )
}
