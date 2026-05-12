import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Row, Col, Card, Statistic, List, Tag, Typography, Space, Button } from 'antd'
import { PhoneOutlined, UserAddOutlined, FileTextOutlined, RightOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import { getCallTasks } from '../../api/calls'
import { getLeads, getLeadsStats } from '../../api/leads'
import { getContracts } from '../../api/contracts'

const { Title, Text } = Typography

export default function ManagerHome() {
  const navigate = useNavigate()

  const { data: tasks = [] } = useQuery({ queryKey: ['call-tasks'], queryFn: getCallTasks })
  const { data: leads = [] } = useQuery({ queryKey: ['leads', 'new'], queryFn: () => getLeads({ status: 'new' }) })
  const { data: stats } = useQuery({ queryKey: ['leads-stats'], queryFn: getLeadsStats })
  const { data: contracts = [] } = useQuery({ queryKey: ['contracts'], queryFn: getContracts })

  const today = dayjs().startOf('day')
  const callsToday = tasks.filter(t => t.next_call_at && dayjs(t.next_call_at).isBefore(today.add(1, 'day')))
  const pendingContracts = contracts.filter(c => c.status === 'draft' || c.status === 'pending_signature')
  const newLeads = leads.slice(0, 5)

  return (
    <div>
      <Title level={3} style={{ marginBottom: 4 }}>Воронка продаж</Title>
      <Text type="secondary">{dayjs().format('dddd, D MMMM YYYY')}</Text>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Новых лидов сегодня"
              value={stats?.new_today ?? 0}
              prefix={<UserAddOutlined style={{ color: '#1677ff' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Звонки в работе"
              value={tasks.length}
              prefix={<PhoneOutlined style={{ color: '#fa8c16' }} />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Лиды в раздумьях"
              value={(stats?.by_status as Record<string, number>)?.in_doubt ?? 0}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Договора на подписи"
              value={pendingContracts.length}
              prefix={<FileTextOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col xs={24} lg={12}>
          <Card
            title="Звонки на сегодня"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/manager/leads')}>
                Все <RightOutlined />
              </Button>
            }
          >
            {callsToday.length === 0 && <Text type="secondary">Свободно. Все звонки на сегодня обработаны.</Text>}
            <List
              dataSource={callsToday.slice(0, 6)}
              renderItem={(t) => (
                <List.Item
                  actions={[
                    <Button
                      key="open"
                      size="small"
                      icon={<PhoneOutlined />}
                      onClick={() => navigate(`/manager/leads/${t.lead_id}`)}
                    >
                      Открыть
                    </Button>,
                  ]}
                >
                  <Space>
                    <Text strong>Лид #{t.lead_id}</Text>
                    <Tag color="orange">попытка {t.attempts + 1}</Tag>
                    {t.next_call_at && (
                      <Text type="secondary">{dayjs(t.next_call_at).format('HH:mm')}</Text>
                    )}
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card
            title="Свежие лиды"
            extra={
              <Button type="link" size="small" onClick={() => navigate('/manager/leads')}>
                Все <RightOutlined />
              </Button>
            }
          >
            {newLeads.length === 0 && <Text type="secondary">Новых лидов нет.</Text>}
            <List
              dataSource={newLeads}
              renderItem={(l) => (
                <List.Item
                  actions={[
                    <Button
                      key="open"
                      size="small"
                      onClick={() => navigate(`/manager/leads/${l.id}`)}
                    >
                      Открыть
                    </Button>,
                  ]}
                >
                  <Space direction="vertical" size={0}>
                    <Text strong>{l.name}</Text>
                    <Space size="small">
                      <Text type="secondary">{l.phone}</Text>
                      <Tag>{l.source}</Tag>
                    </Space>
                  </Space>
                </List.Item>
              )}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}
