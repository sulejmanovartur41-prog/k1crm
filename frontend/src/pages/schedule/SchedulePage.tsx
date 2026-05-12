import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Table, Button, Modal, Form, Input, InputNumber, DatePicker, Select, Typography, message, Space } from 'antd'
import { PlusOutlined } from '@ant-design/icons'
import { useState } from 'react'
import api from '../../api/client'
import { listGroups } from '../../api/groups'
import dayjs from 'dayjs'

const { Title } = Typography

export default function SchedulePage() {
  const qc = useQueryClient()
  const [open, setOpen] = useState(false)
  const [form] = Form.useForm()

  const { data: lessons = [], isLoading } = useQuery({
    queryKey: ['lessons'],
    queryFn: () => api.get('/schedule/lessons').then((r) => r.data),
  })

  const { data: groups = [] } = useQuery({
    queryKey: ['groups', 'active'],
    queryFn: () => listGroups('active'),
  })

  const createMutation = useMutation({
    mutationFn: (v: any) =>
      api.post('/schedule/lessons', { ...v, datetime: v.datetime.toISOString() }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['lessons'] })
      setOpen(false)
      form.resetFields()
      message.success('Занятие создано')
    },
  })

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Группа', dataIndex: 'group_name' },
    { title: 'Дата/время', dataIndex: 'datetime', render: (d: string) => dayjs(d).format('DD.MM.YY HH:mm') },
    { title: 'Аудитория', dataIndex: 'room' },
    { title: 'Мест', dataIndex: 'capacity' },
  ]

  return (
    <div>
      <Title level={3}>Расписание занятий</Title>
      <Space style={{ marginBottom: 16 }}>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setOpen(true)}>
          Добавить занятие
        </Button>
      </Space>
      <Table rowKey="id" columns={columns} dataSource={lessons} loading={isLoading} size="middle" />
      <Modal title="Новое занятие" open={open} onCancel={() => setOpen(false)} onOk={() => form.submit()} okText="Создать">
        <Form form={form} layout="vertical" onFinish={(v) => createMutation.mutate(v)}>
          <Form.Item name="group_id" label="Группа" rules={[{ required: true }]}>
            <Select
              options={groups.map(g => ({ value: g.id, label: g.name }))}
              placeholder="Выберите группу"
              showSearch
              optionFilterProp="label"
            />
          </Form.Item>
          <Form.Item name="teacher_id" label="ID преподавателя" rules={[{ required: true }]}><InputNumber style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="datetime" label="Дата и время" rules={[{ required: true }]}><DatePicker showTime style={{ width: '100%' }} /></Form.Item>
          <Form.Item name="room" label="Аудитория"><Input /></Form.Item>
          <Form.Item name="capacity" label="Вместимость" initialValue={12}><InputNumber style={{ width: '100%' }} /></Form.Item>
        </Form>
      </Modal>
    </div>
  )
}
