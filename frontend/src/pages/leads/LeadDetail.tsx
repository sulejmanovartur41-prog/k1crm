import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card, Descriptions, Tag, Button, Modal, Form, Select, Input, Space,
  Typography, Table, message, Divider, Row, Col, Statistic,
} from 'antd'
import { PhoneOutlined, ArrowLeftOutlined, CalendarOutlined } from '@ant-design/icons'
import { getLead } from '../../api/leads'
import { getCallTasks, registerAttempt } from '../../api/calls'
import { getLessons, createBooking } from '../../api/schedule'
import dayjs from 'dayjs'

const { Title, Text } = Typography

const STATUS_COLORS: Record<string, string> = {
  new: 'blue', calling: 'orange', in_doubt: 'gold',
  enrolled: 'green', refused: 'red', archived: 'default',
}
const STATUS_LABELS: Record<string, string> = {
  new: 'Новый', calling: 'Звонок', in_doubt: 'В раздумьях',
  enrolled: 'Записан', refused: 'Отказ', archived: 'Архив',
}

export default function LeadDetail() {
  const { id } = useParams<{ id: string }>()
  const leadId = Number(id)
  const navigate = useNavigate()
  const qc = useQueryClient()

  const [callModalOpen, setCallModalOpen] = useState(false)
  const [bookingModalOpen, setBookingModalOpen] = useState(false)
  const [callForm] = Form.useForm()
  const [bookingForm] = Form.useForm()

  const { data: lead, isLoading } = useQuery({
    queryKey: ['lead', leadId],
    queryFn: () => getLead(leadId),
  })

  const { data: tasks = [] } = useQuery({
    queryKey: ['call-tasks'],
    queryFn: getCallTasks,
  })

  const { data: lessons = [] } = useQuery({
    queryKey: ['lessons'],
    queryFn: getLessons,
  })

  const leadTasks = tasks.filter((t) => t.lead_id === leadId)

  const attemptMutation = useMutation({
    mutationFn: (data: { taskId: number; result: string; outcome?: string; refusal_reason?: string }) =>
      registerAttempt(data.taskId, { result: data.result, outcome: data.outcome, refusal_reason: data.refusal_reason }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      qc.invalidateQueries({ queryKey: ['call-tasks'] })
      setCallModalOpen(false)
      callForm.resetFields()
      message.success('Результат звонка сохранён')
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || 'Ошибка при сохранении')
    },
  })

  const bookingMutation = useMutation({
    mutationFn: (lessonId: number) => createBooking({ lead_id: leadId, lesson_id: lessonId }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lead', leadId] })
      setBookingModalOpen(false)
      bookingForm.resetFields()
      message.success('Клиент записан на пробный урок')
    },
    onError: (err: any) => {
      message.error(err.response?.data?.detail || 'Ошибка при записи')
    },
  })

  // Клик «Позвонить» открывает форму результата звонка и подставляет tel:-ссылку.
  // Реальная инициация через Zadarma делается отдельным сценарием с
  // настроенным extension-ом — захардкоженное `from_number='office'` было
  // невалидно и убрано.
  const handleCall = () => {
    if (lead) {
      window.open(`tel:${lead.phone}`)
    }
    setCallModalOpen(true)
  }

  const handleAttemptSubmit = (values: any) => {
    const activeTask = leadTasks.find((t) => !t.completed)
    if (!activeTask) {
      message.error('Нет активной задачи на звонок')
      return
    }
    attemptMutation.mutate({ taskId: activeTask.id, ...values })
  }

  const taskColumns = [
    { title: 'ID задачи', dataIndex: 'id', width: 80 },
    { title: 'Попыток', dataIndex: 'attempts', width: 90 },
    {
      title: 'Следующий звонок',
      dataIndex: 'next_call_at',
      render: (d: string | null) => (d ? dayjs(d).format('DD.MM.YY HH:mm') : '—'),
    },
    {
      title: 'Статус',
      render: (_: unknown, row: any) =>
        row.completed ? (
          <Tag color="default">Завершена</Tag>
        ) : row.escalated ? (
          <Tag color="red">Эскалация</Tag>
        ) : (
          <Tag color="blue">Активна</Tag>
        ),
    },
  ]

  if (isLoading || !lead) return null

  const activeTask = leadTasks.find((t) => !t.completed)

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/leads')}>
          Назад к лидам
        </Button>
      </Space>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col span={16}>
          <Card
            title={<Title level={4} style={{ margin: 0 }}>{lead.name}</Title>}
            extra={<Tag color={STATUS_COLORS[lead.status]}>{STATUS_LABELS[lead.status] || lead.status}</Tag>}
          >
            <Descriptions column={2} size="small">
              <Descriptions.Item label="Телефон">
                <a href={`tel:${lead.phone}`}>{lead.phone}</a>
              </Descriptions.Item>
              <Descriptions.Item label="Источник">
                <Tag>{lead.source}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="Попыток звонка">{lead.attempt_count}</Descriptions.Item>
              <Descriptions.Item label="Создан">
                {dayjs(lead.created_at).format('DD.MM.YYYY HH:mm')}
              </Descriptions.Item>
              {lead.message_text && (
                <Descriptions.Item label="Сообщение" span={2}>
                  <Text type="secondary">{lead.message_text}</Text>
                </Descriptions.Item>
              )}
            </Descriptions>

            <Divider />

            <Space>
              <Button
                type="primary"
                icon={<PhoneOutlined />}
                onClick={handleCall}
                disabled={!activeTask}
              >
                Позвонить сейчас
              </Button>
              <Button
                icon={<CalendarOutlined />}
                onClick={() => setBookingModalOpen(true)}
                disabled={lead.status !== 'enrolled'}
              >
                Записать на урок
              </Button>
            </Space>
          </Card>
        </Col>

        <Col span={8}>
          <Card size="small">
            <Statistic title="Попыток звонка" value={lead.attempt_count} />
          </Card>
        </Col>
      </Row>

      <Card title="История задач на звонок">
        <Table
          rowKey="id"
          columns={taskColumns}
          dataSource={leadTasks}
          size="small"
          pagination={false}
        />
      </Card>

      {/* Call result modal */}
      <Modal
        title="Результат звонка"
        open={callModalOpen}
        onCancel={() => { setCallModalOpen(false); callForm.resetFields() }}
        onOk={() => callForm.submit()}
        okText="Сохранить"
        confirmLoading={attemptMutation.isPending}
      >
        <Form form={callForm} layout="vertical" onFinish={handleAttemptSubmit}>
          <Form.Item name="result" label="Результат" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'no_answer', label: 'Не дозвонился' },
                { value: 'answered', label: 'Дозвонился' },
              ]}
            />
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prev, cur) => prev.result !== cur.result}
          >
            {({ getFieldValue }) =>
              getFieldValue('result') === 'answered' && (
                <Form.Item name="outcome" label="Итог разговора" rules={[{ required: true }]}>
                  <Select
                    options={[
                      { value: 'enrolled', label: 'Записал на пробный урок' },
                      { value: 'in_doubt', label: 'В раздумьях' },
                      { value: 'refused', label: 'Отказ' },
                    ]}
                  />
                </Form.Item>
              )
            }
          </Form.Item>
          <Form.Item
            noStyle
            shouldUpdate={(prev, cur) => prev.outcome !== cur.outcome}
          >
            {({ getFieldValue }) =>
              getFieldValue('outcome') === 'refused' && (
                <Form.Item name="refusal_reason" label="Причина отказа" rules={[{ required: true }]}>
                  <Input.TextArea rows={2} />
                </Form.Item>
              )
            }
          </Form.Item>
        </Form>
      </Modal>

      {/* Booking modal */}
      <Modal
        title="Запись на пробный урок"
        open={bookingModalOpen}
        onCancel={() => { setBookingModalOpen(false); bookingForm.resetFields() }}
        onOk={() => bookingForm.submit()}
        okText="Записать"
        confirmLoading={bookingMutation.isPending}
      >
        <Form
          form={bookingForm}
          layout="vertical"
          onFinish={(v) => bookingMutation.mutate(v.lesson_id)}
        >
          <Form.Item name="lesson_id" label="Выберите занятие" rules={[{ required: true }]}>
            <Select
              options={lessons.map((l) => ({
                value: l.id,
                label: `${l.group_name} — ${dayjs(l.datetime).format('DD.MM.YY HH:mm')}${l.room ? ` (${l.room})` : ''}`,
              }))}
            />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
