import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Table, Tag, Button, Typography, message, Space } from 'antd'
import { CheckOutlined, DownloadOutlined } from '@ant-design/icons'
import api from '../../api/client'
import dayjs from 'dayjs'

const { Title } = Typography

const STATUS_LABELS: Record<string, string> = {
  generated: 'Сгенерирован',
  signed: 'Подписан',
  paid: 'Оплачен',
}
const STATUS_COLORS: Record<string, string> = {
  generated: 'blue',
  signed: 'green',
  paid: 'gold',
}

export default function ContractsPage() {
  const qc = useQueryClient()
  const { data: contracts = [], isLoading } = useQuery({
    queryKey: ['contracts'],
    queryFn: () => api.get('/contracts').then((r) => r.data),
  })

  const signMutation = useMutation({
    mutationFn: (id: number) => api.post(`/contracts/${id}/sign`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['contracts'] })
      message.success('Договор отмечен как подписанный')
    },
  })

  const columns = [
    { title: 'ID', dataIndex: 'id', width: 60 },
    { title: 'Клиент ID', dataIndex: 'client_id' },
    { title: 'Сумма', dataIndex: 'amount', render: (v: number) => `${Number(v).toLocaleString('ru')} ₽` },
    { title: 'Статус', dataIndex: 'status', render: (s: string) => <Tag color={STATUS_COLORS[s]}>{STATUS_LABELS[s] || s}</Tag> },
    { title: 'Создан', dataIndex: 'created_at', render: (d: string) => dayjs(d).format('DD.MM.YY') },
    {
      title: 'Действия',
      render: (_: unknown, row: any) => (
        <Space>
          <Button size="small" icon={<DownloadOutlined />} href={`/api/v1/contracts/${row.id}/download`} target="_blank">
            PDF
          </Button>
          {row.status === 'generated' && (
            <Button size="small" icon={<CheckOutlined />} onClick={() => signMutation.mutate(row.id)}>
              Подписан
            </Button>
          )}
        </Space>
      ),
    },
  ]

  return (
    <div>
      <Title level={3}>Договора</Title>
      <Table rowKey="id" columns={columns} dataSource={contracts} loading={isLoading} size="middle" />
    </div>
  )
}
