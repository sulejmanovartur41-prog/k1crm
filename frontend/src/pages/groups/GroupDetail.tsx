import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Button,
  Card,
  Col,
  Form,
  InputNumber,
  Modal,
  Progress,
  Row,
  Select,
  Space,
  Statistic,
  Table,
  Tabs,
  Tag,
  TimePicker,
  Tooltip,
  Typography,
  message,
} from 'antd'
import {
  ArrowLeftOutlined,
  CalendarOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  SettingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { getGroup, generateSchedule, GroupStudent, GroupLessonItem } from '../../api/groups'
import { getRole } from '../../auth'
import ClientDetailDrawer from '../../components/ClientDetailDrawer'

const { Title, Text } = Typography

const WEEKDAY_OPTIONS = [
  { label: 'Пн', value: 1 },
  { label: 'Вт', value: 2 },
  { label: 'Ср', value: 3 },
  { label: 'Чт', value: 4 },
  { label: 'Пт', value: 5 },
  { label: 'Сб', value: 6 },
  { label: 'Вс', value: 7 },
]

const STATUS_TAG: Record<string, { color: string; label: string }> = {
  active:   { color: 'green',   label: 'Активен' },
  inactive: { color: 'default', label: 'Неактивен' },
  frozen:   { color: 'blue',    label: 'Заморожен' },
}

const PAY_TAG: Record<string, { color: string; label: string }> = {
  paid:    { color: 'green',  label: 'Оплачен' },
  pending: { color: 'orange', label: 'Ожидает' },
  overdue: { color: 'red',    label: 'Просрочен' },
  blocked: { color: 'red',    label: 'Заблокирован' },
}

function calcAge(birthDate: string | null): number | null {
  if (!birthDate) return null
  return dayjs().diff(dayjs(birthDate), 'year')
}

export default function GroupDetail() {
  const { id } = useParams<{ id: string }>()
  const groupId = Number(id)
  const navigate = useNavigate()
  const role = getRole()
  const qc = useQueryClient()

  const [selectedClientId, setSelectedClientId] = useState<number | null>(null)
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false)
  const [form] = Form.useForm()

  const { data: group, isLoading } = useQuery({
    queryKey: ['group', groupId],
    queryFn: () => getGroup(groupId),
  })

  const scheduleMutation = useMutation({
    mutationFn: (values: any) =>
      generateSchedule(groupId, {
        weekdays: values.weekdays,
        time: dayjs(values.time).format('HH:mm'),
        weeks: values.weeks,
      }),
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['group', groupId] })
      message.success(`Создано ${result.created} занятий, пропущено ${result.skipped.length}`)
      setScheduleModalOpen(false)
      form.resetFields()
    },
    onError: (e: any) => message.error(e?.response?.data?.detail ?? 'Ошибка генерации'),
  })

  if (isLoading || !group) {
    return <Card loading style={{ minHeight: 400 }} />
  }

  // KPI calculations
  const totalStudents = group.students.length
  const avgAge = totalStudents > 0
    ? Math.round(
        group.students.reduce((sum, s) => sum + (calcAge(s.child_birth_date) ?? 0), 0) / totalStudents
      )
    : null

  // attendance_rate is a 0-1 fraction from the backend
  const studentsWithAtt = group.students.filter(s => s.attendance_rate !== null)
  const avgAttendance = studentsWithAtt.length > 0
    ? Math.round(studentsWithAtt.reduce((sum, s) => sum + (s.attendance_rate ?? 0), 0) / studentsWithAtt.length * 100)
    : null

  const paidCount = group.students.filter(s => s.payment_status === 'paid').length
  const payRate = totalStudents > 0 ? Math.round((paidCount / totalStudents) * 100) : 0

  const studentColumns: ColumnsType<GroupStudent> = [
    {
      title: 'Ученик',
      dataIndex: 'child_name',
      render: (name: string, record) => (
        <Button type="link" style={{ padding: 0, fontWeight: 600 }} onClick={() => setSelectedClientId(record.id)}>
          {name}
        </Button>
      ),
    },
    {
      title: 'Возраст',
      dataIndex: 'child_birth_date',
      width: 80,
      align: 'center',
      render: (d: string | null) => {
        const age = calcAge(d)
        return age !== null ? `${age} лет` : <Text type="secondary">—</Text>
      },
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      width: 110,
      render: (s: string) => {
        const t = STATUS_TAG[s]
        return t ? <Tag color={t.color}>{t.label}</Tag> : <Tag>{s}</Tag>
      },
    },
    {
      title: 'Посещаемость (30д)',
      dataIndex: 'attendance_rate',
      width: 170,
      render: (rate: number | null) => {
        if (rate === null) return <Text type="secondary">нет данных</Text>
        const pct = Math.round(rate * 100)
        const color = pct >= 80 ? '#52c41a' : pct >= 50 ? '#faad14' : '#ff4d4f'
        return (
          <Tooltip title={`${pct}%`}>
            <Progress percent={pct} size="small" strokeColor={color} style={{ width: 120 }} />
          </Tooltip>
        )
      },
    },
    {
      title: 'Оплата',
      dataIndex: 'payment_status',
      width: 110,
      render: (s: string | null) => {
        if (!s) return <Text type="secondary">—</Text>
        const t = PAY_TAG[s]
        return t ? <Tag color={t.color}>{t.label}</Tag> : <Tag>{s}</Tag>
      },
    },
    {
      title: 'Родитель',
      dataIndex: 'parent_name',
      render: (name: string, record) => (
        <Space direction="vertical" size={0}>
          <Text>{name}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{record.parent_phone}</Text>
        </Space>
      ),
    },
  ]

  const lessonColumns: ColumnsType<GroupLessonItem> = [
    {
      title: 'Дата',
      dataIndex: 'datetime',
      render: (d: string) => dayjs(d).format('DD MMM YYYY'),
    },
    {
      title: 'Время',
      dataIndex: 'datetime',
      width: 80,
      render: (d: string) => dayjs(d).format('HH:mm'),
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
  ]

  const canManage = role === 'admin' || role === 'manager'
  const base = role === 'teacher' ? '/teacher' : role === 'manager' ? '/manager' : '/admin'

  return (
    <div>
      {/* Header */}
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`${base}/groups`)}>
          Группы
        </Button>
      </Space>

      <Card style={{ marginBottom: 16, borderLeft: `4px solid ${group.color || '#722ed1'}` }}>
        <Row align="middle" gutter={16}>
          <Col flex="auto">
            <Space align="center" size="middle">
              <span
                style={{
                  display: 'inline-block',
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  background: group.color || '#722ed1',
                  flexShrink: 0,
                }}
              />
              <Title level={2} style={{ margin: 0 }}>{group.name}</Title>
              {group.level && <Tag color={group.color || 'purple'} style={{ fontSize: 14 }}>{group.level}</Tag>}
              {group.status === 'archived' && <Tag>Архив</Tag>}
            </Space>
            <Space style={{ marginTop: 8 }} size="large">
              {group.teacher_name && (
                <Text type="secondary"><UserOutlined /> {group.teacher_name}</Text>
              )}
              {group.room && (
                <Text type="secondary"><CalendarOutlined /> Ауд. {group.room}</Text>
              )}
              {group.description && (
                <Text type="secondary">{group.description}</Text>
              )}
            </Space>
          </Col>
          {canManage && (
            <Col>
              <Button
                icon={<SettingOutlined />}
                onClick={() => setScheduleModalOpen(true)}
              >
                Расписание
              </Button>
            </Col>
          )}
        </Row>
      </Card>

      {/* KPI */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="Учеников"
              value={totalStudents}
              suffix={`/ ${group.capacity}`}
              prefix={<TeamOutlined style={{ color: group.color || '#722ed1' }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="Посещаемость (30д)"
              value={avgAttendance ?? '—'}
              suffix={avgAttendance !== null ? '%' : undefined}
              prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="Оплачено"
              value={payRate}
              suffix="%"
              prefix={<CloseCircleOutlined style={{ color: payRate >= 80 ? '#52c41a' : '#faad14' }} />}
            />
          </Card>
        </Col>
        <Col xs={12} sm={6}>
          <Card>
            <Statistic
              title="Средний возраст"
              value={avgAge ?? '—'}
              suffix={avgAge !== null ? 'лет' : undefined}
              prefix={<UserOutlined style={{ color: '#1677ff' }} />}
            />
          </Card>
        </Col>
      </Row>

      {/* Tabs */}
      <Card>
        <Tabs
          defaultActiveKey="students"
          items={[
            {
              key: 'students',
              label: <><TeamOutlined /> Ученики ({totalStudents})</>,
              children: (
                <Table
                  rowKey="id"
                  columns={studentColumns}
                  dataSource={group.students}
                  size="middle"
                  pagination={false}
                  locale={{ emptyText: 'Учеников в группе нет' }}
                  onRow={(record) => ({
                    style: { cursor: 'pointer' },
                    onClick: () => setSelectedClientId(record.id),
                  })}
                />
              ),
            },
            {
              key: 'schedule',
              label: <><CalendarOutlined /> Расписание ({group.upcoming_lessons.length})</>,
              children: (
                <>
                  {canManage && (
                    <div style={{ marginBottom: 12 }}>
                      <Button
                        icon={<SettingOutlined />}
                        onClick={() => setScheduleModalOpen(true)}
                      >
                        Сгенерировать расписание
                      </Button>
                    </div>
                  )}
                  <Table
                    rowKey="id"
                    columns={lessonColumns}
                    dataSource={group.upcoming_lessons}
                    size="middle"
                    pagination={false}
                    locale={{ emptyText: 'Предстоящих занятий нет' }}
                  />
                </>
              ),
            },
          ]}
        />
      </Card>

      {/* Client Drawer */}
      <ClientDetailDrawer
        clientId={selectedClientId}
        onClose={() => setSelectedClientId(null)}
      />

      {/* Schedule Generator Modal */}
      <Modal
        title="Сгенерировать расписание"
        open={scheduleModalOpen}
        onCancel={() => { setScheduleModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
        okText="Создать"
        confirmLoading={scheduleMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(v) => scheduleMutation.mutate(v)}
          initialValues={{ weeks: 8 }}
        >
          <Form.Item name="weekdays" label="Дни недели" rules={[{ required: true, type: 'array', min: 1 }]}>
            <Select
              mode="multiple"
              options={WEEKDAY_OPTIONS}
              placeholder="Выберите дни"
            />
          </Form.Item>
          <Form.Item name="time" label="Время урока" rules={[{ required: true }]}>
            <TimePicker format="HH:mm" minuteStep={5} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="weeks" label="Количество недель" rules={[{ required: true }]}>
            <InputNumber min={1} max={52} style={{ width: '100%' }} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
