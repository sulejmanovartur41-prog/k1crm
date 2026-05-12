import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import {
  Button,
  Card,
  Col,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Row,
  Segmented,
  Space,
  Tag,
  Typography,
  message,
} from 'antd'
import { PlusOutlined, TeamOutlined, EnvironmentOutlined, UserOutlined } from '@ant-design/icons'
import {
  GroupListItem,
  GroupStatus,
  createGroup,
  listGroups,
} from '../../api/groups'
import { getRole } from '../../auth'

const { Title, Text } = Typography

const ROLE_BASE: Record<string, string> = {
  admin: '/admin',
  manager: '/manager',
  teacher: '/teacher',
}

export default function GroupsPage() {
  const role = getRole()
  const base = ROLE_BASE[role] ?? '/admin'
  const canManage = role === 'admin' || role === 'manager'

  const qc = useQueryClient()
  const [status, setStatus] = useState<GroupStatus>('active')
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const { data: groups = [], isLoading } = useQuery({
    queryKey: ['groups', status],
    queryFn: () => listGroups(status),
  })

  const createMutation = useMutation({
    mutationFn: createGroup,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['groups'] })
      setOpen(false)
      form.resetFields()
      message.success('Группа создана')
    },
    onError: (e: any) => {
      const detail = e?.response?.data?.detail ?? 'Не удалось создать группу'
      message.error(detail)
    },
  })

  return (
    <div>
      <Space style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={3} style={{ margin: 0 }}>Группы</Title>
        <Space>
          <Segmented
            value={status}
            onChange={(v) => setStatus(v as GroupStatus)}
            options={[
              { label: 'Активные', value: 'active' },
              { label: 'Архив', value: 'archived' },
            ]}
          />
          {canManage && (
            <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
              Новая группа
            </Button>
          )}
        </Space>
      </Space>

      {!isLoading && groups.length === 0 && (
        <Empty description={status === 'active' ? 'Активных групп пока нет' : 'Архив пуст'} />
      )}

      <Row gutter={[16, 16]}>
        {groups.map((g) => (
          <Col xs={24} sm={12} lg={8} xl={6} key={g.id}>
            <GroupCard group={g} base={base} />
          </Col>
        ))}
      </Row>

      <Modal
        title="Новая группа"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={() => form.submit()}
        okText="Создать"
        confirmLoading={createMutation.isPending}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={(v) => createMutation.mutate(v)}
          initialValues={{ capacity: 12 }}
        >
          <Form.Item name="name" label="Название" rules={[{ required: true, max: 100 }]}>
            <Input placeholder="Например: Scratch (7–9 лет)" />
          </Form.Item>
          <Form.Item name="level" label="Уровень / возрастная категория">
            <Input placeholder="Scratch 7-9" />
          </Form.Item>
          <Form.Item name="teacher_id" label="ID преподавателя">
            <InputNumber style={{ width: '100%' }} placeholder="оставьте пустым для вакансии" />
          </Form.Item>
          <Form.Item name="room" label="Аудитория">
            <Input placeholder="Кабинет 1" />
          </Form.Item>
          <Form.Item name="capacity" label="Вместимость" rules={[{ required: true }]}>
            <InputNumber style={{ width: '100%' }} min={1} max={100} />
          </Form.Item>
          <Form.Item name="color" label="Цвет (HEX)">
            <Input placeholder="#722ed1" />
          </Form.Item>
          <Form.Item name="description" label="Описание">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      </Modal>
    </div>
  )
}

function GroupCard({ group, base }: { group: GroupListItem; base: string }) {
  const fill = group.capacity > 0 ? Math.round((group.students_count / group.capacity) * 100) : 0
  const fillStatus = fill >= 100 ? 'exception' : fill >= 80 ? 'normal' : 'active'

  return (
    <Card
      hoverable
      styles={{ body: { padding: 16 } }}
      title={
        <Space align="center">
          <span
            style={{
              display: 'inline-block',
              width: 12,
              height: 12,
              borderRadius: '50%',
              background: group.color || '#bfbfbf',
            }}
          />
          <span>{group.name}</span>
        </Space>
      }
      extra={group.status === 'archived' ? <Tag>Архив</Tag> : null}
    >
      <Space direction="vertical" size={6} style={{ width: '100%' }}>
        {group.level && <Tag color={group.color || 'blue'}>{group.level}</Tag>}
        <Text type="secondary">
          <UserOutlined /> {group.teacher_name ?? 'Вакансия'}
        </Text>
        {group.room && (
          <Text type="secondary">
            <EnvironmentOutlined /> {group.room}
          </Text>
        )}
        <div>
          <Text type="secondary">
            <TeamOutlined /> {group.students_count} / {group.capacity}
          </Text>
          <Progress
            percent={fill}
            status={fillStatus}
            showInfo={false}
            size="small"
            style={{ marginTop: 4 }}
          />
        </div>
        <Link to={`${base}/groups/${group.id}`}>
          <Button type="link" style={{ padding: 0 }}>Открыть карточку →</Button>
        </Link>
      </Space>
    </Card>
  )
}
