import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { Select, Table, Switch, Button, Typography, Space, message } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import api from '../../api/client'

const { Title } = Typography

export default function AttendancePage() {
  const [lessonId, setLessonId] = useState<number | null>(null)
  const [marks, setMarks] = useState<Record<number, boolean>>({})

  const { data: lessons = [] } = useQuery({
    queryKey: ['lessons'],
    queryFn: () => api.get('/schedule/lessons').then((r) => r.data),
  })

  const { data: students = [], isLoading } = useQuery({
    queryKey: ['attendance', lessonId],
    queryFn: () => lessonId ? api.get(`/attendance/lessons/${lessonId}`).then((r) => r.data) : [],
    enabled: !!lessonId,
  })

  const markMutation = useMutation({
    mutationFn: () =>
      api.post(`/attendance/lessons/${lessonId}/mark`, {
        marks: Object.entries(marks).map(([id, present]) => ({ client_id: Number(id), present })),
      }),
    onSuccess: () => message.success('Перекличка сохранена'),
  })

  const columns = [
    { title: 'Имя ребёнка', dataIndex: 'child_name' },
    { title: 'Родитель', dataIndex: 'parent_name' },
    {
      title: 'Присутствие',
      render: (_: unknown, row: any) => (
        <Switch
          checked={marks[row.client_id] ?? row.present ?? false}
          onChange={(v) => setMarks((m) => ({ ...m, [row.client_id]: v }))}
        />
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>Посещаемость</Title>
      <Space style={{ marginBottom: 16 }}>
        <Select
          placeholder="Выберите занятие"
          style={{ width: 280 }}
          onChange={(v) => { setLessonId(v); setMarks({}) }}
          options={lessons.map((l: any) => ({
            value: l.id,
            label: `${l.group_name} — ${new Date(l.datetime).toLocaleString('ru')}`,
          }))}
        />
        <Button
          type="primary"
          icon={<SaveOutlined />}
          disabled={!lessonId}
          onClick={() => markMutation.mutate()}
        >
          Сохранить перекличку
        </Button>
      </Space>
      {lessonId && (
        <Table rowKey="client_id" columns={columns} dataSource={students} loading={isLoading} size="middle" />
      )}
    </div>
  )
}
