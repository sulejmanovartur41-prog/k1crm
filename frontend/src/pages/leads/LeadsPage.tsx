import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Table, Tag, Button, Select, Space, Typography, Card, Row, Col, Statistic, Modal, Form, Input, message,
} from 'antd'
import { PlusOutlined, PhoneOutlined, EyeOutlined } from '@ant-design/icons'
import { getLeads, getLeadsStats, createLead, Lead } from '../../api/leads'
import { getRole } from '../../auth'
import dayjs from 'dayjs'

const { Title } = Typography

const STATUS_COLORS: Record<string, string> = {
  new: 'blue',
  calling: 'orange',
  in_doubt: 'gold',
  enrolled: 'green',
  refused: 'red',
  archived: 'default',
}

const STATUS_LABELS: Record<string, string> = {
  new: 'Новый',
  calling: 'Звонок',
  in_doubt: 'В раздумьях',
  enrolled: 'Записан',
  refused: 'Отказ',
  archived: 'Архив',
}

const ROLE_BASE: Record<string, string> = { admin: '/admin', manager: '/manager', teacher: '/teacher' }

export default function LeadsPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const base = ROLE_BASE[getRole()] ?? '/admin'
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const [addOpen, setAddOpen] = useState(false)
  const [form] = Form.useForm()

  const { data: leads = [], isLoading } = useQuery({
    queryKey: ['leads', statusFilter],
    queryFn: () => getLeads({ status: statusFilter }),
  })

  const { data: stats } = useQuery({ queryKey: ['leads-stats'], queryFn: getLeadsStats })

  const createMutation = useMutation({
    mutationFn: createLead,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['leads'] })
      qc.invalidateQueries({ queryKey: ['leads-stats'] })
      setAddOpen(false)
      form.resetFields()
      message.success('Лид создан')
    },
  })

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Имя', dataIndex: 'name' },
    { title: 'Телефон', dataIndex: 'phone' },
    {
      title: 'Источник',
      dataIndex: 'source',
      render: (s: string) => <Tag>{s}</Tag>,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s] || s}</Tag>,
    },
    { title: 'Попыток', dataIndex: 'attempt_count', width: 90 },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      render: (d: string) => dayjs(d).format('DD.MM.YY HH:mm'),
    },
    {
      title: '',
      render: (_: unknown, row: Lead) => (
        <Space>
          <Button icon={<EyeOutlined />} size="small" onClick={() => navigate(`${base}/leads/${row.id}`)}>
            Открыть
          </Button>
          <Button icon={<PhoneOutlined />} size="small" href={`tel:${row.phone}`}>
            Звонок
          </Button>
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>Лиды / CRM</Title>

      {stats && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col>
            <Card size="small">
              <Statistic
                title="Всего лидов"
                value={Object.values((stats.by_status as Record<string, number>) ?? {}).reduce((a, b) => a + b, 0)}
              />
            </Card>
          </Col>
          <Col>
            <Card size="small">
              <Statistic title="Новых сегодня" value={stats.new_today ?? 0} />
            </Card>
          </Col>
          <Col>
            <Card size="small">
              <Statistic title="В обработке" value={(stats.by_status as Record<string, number> | undefined)?.calling ?? 0} />
            </Card>
          </Col>
        </Row>
      )}

      <Space style={{ marginBottom: 16 }}>
        <Select
          allowClear
          placeholder="Фильтр по статусу"
          style={{ width: 180 }}
          onChange={setStatusFilter}
          options={Object.entries(STATUS_LABELS).map(([v, l]) => ({ value: v, label: l }))}
        />
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setAddOpen(true)}>
          Добавить лид
        </Button>
      </Space>

      <Table
        rowKey="id"
        columns={columns}
        dataSource={leads}
        loading={isLoading}
        pagination={{ pageSize: 20 }}
        size="middle"
      />

      <Modal
        title="Новый лид"
        open={addOpen}
        onCancel={() => setAddOpen(false)}
        onOk={() => form.submit()}
        okText="Создать"
      >
        <Form form={form} layout="vertical" onFinish={(v) => createMutation.mutate(v)}>
          <Form.Item name="name" label="Имя" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="phone" label="Телефон" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="source" label="Источник" rules={[{ required: true }]} initialValue="phone">
            <Select options={['telegram', 'whatsapp', 'site', 'phone'].map((s) => ({ value: s, label: s }))} />
          </Form.Item>
          <Form.Item name="message_text" label="Сообщение">
            <Input.TextArea rows={3} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
