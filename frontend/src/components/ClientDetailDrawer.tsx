import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Badge,
  Button,
  DatePicker,
  Descriptions,
  Drawer,
  Form,
  InputNumber,
  Modal,
  Select,
  Space,
  Table,
  Tag,
  Tabs,
  Typography,
  message,
} from 'antd'
import {
  CheckCircleFilled,
  CloseCircleFilled,
  FilePdfOutlined,
  PlusOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { getClientDetails, PaymentItem, AttendanceItem } from '../api/clients'
import { createPayment } from '../api/payments'
import { getRole } from '../auth'
import api from '../api/client'

const { Text, Title } = Typography

const PAY_TAG: Record<string, { color: string; label: string }> = {
  paid:    { color: 'green',  label: 'Оплачен' },
  pending: { color: 'orange', label: 'Ожидает' },
  overdue: { color: 'red',    label: 'Просрочен' },
  blocked: { color: 'red',    label: 'Заблокирован' },
}

const CLIENT_STATUS: Record<string, { color: string; label: string }> = {
  active:   { color: 'green',   label: 'Активен' },
  inactive: { color: 'default', label: 'Неактивен' },
  frozen:   { color: 'blue',    label: 'Заморожен' },
}

const CONTRACT_STATUS: Record<string, { color: string; label: string }> = {
  generated: { color: 'default', label: 'Сформирован' },
  signed:    { color: 'blue',    label: 'Подписан' },
  paid:      { color: 'green',   label: 'Оплачен' },
}

async function downloadPdf(contractId: number) {
  try {
    const res = await api.get(`/contracts/${contractId}/download`, { responseType: 'blob' })
    const url = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
    const a = document.createElement('a')
    a.style.display = 'none'
    a.href = url
    a.download = `contract_${contractId}.pdf`
    document.body.appendChild(a)
    a.click()
    setTimeout(() => { document.body.removeChild(a); URL.revokeObjectURL(url) }, 100)
  } catch {
    message.error('PDF не найден или ещё не сформирован')
  }
}

interface Props {
  clientId: number | null
  onClose: () => void
}

export default function ClientDetailDrawer({ clientId, onClose }: Props) {
  const role = getRole()
  const canManage = role === 'admin' || role === 'manager'
  const qc = useQueryClient()
  const [paymentModal, setPaymentModal] = useState(false)
  const [form] = Form.useForm()

  const { data, isLoading } = useQuery({
    queryKey: ['client-details', clientId],
    queryFn: () => getClientDetails(clientId!),
    enabled: clientId !== null,
  })

  const payMutation = useMutation({
    mutationFn: (values: any) =>
      createPayment({
        client_id: clientId!,
        amount: values.amount,
        period_from: values.period[0].format('YYYY-MM-DD'),
        period_to: values.period[1].format('YYYY-MM-DD'),
        method: values.method,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['client-details', clientId] })
      message.success('Платёж внесён')
      setPaymentModal(false)
      form.resetFields()
    },
    onError: (e: any) => message.error(e?.response?.data?.detail ?? 'Ошибка платежа'),
  })

  const paymentColumns: ColumnsType<PaymentItem> = [
    {
      title: 'Период',
      render: (_: unknown, r) => `${r.period_from} — ${r.period_to}`,
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      width: 100,
      align: 'right',
      render: (a: number) => `${a.toLocaleString()} ₽`,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      width: 110,
      render: (s: string) => {
        const t = PAY_TAG[s]
        return t ? <Tag color={t.color}>{t.label}</Tag> : <Tag>{s}</Tag>
      },
    },
    {
      title: 'Способ',
      dataIndex: 'method',
      width: 80,
      render: (m: string | null) => m ?? <Text type="secondary">—</Text>,
    },
  ]

  const attColumns: ColumnsType<AttendanceItem> = [
    {
      title: 'Дата урока',
      dataIndex: 'lesson_datetime',
      render: (d: string) => dayjs(d).format('DD MMM YYYY HH:mm'),
    },
    {
      title: '',
      dataIndex: 'present',
      width: 100,
      align: 'center',
      render: (p: boolean) => p
        ? <CheckCircleFilled style={{ color: '#52c41a', fontSize: 18 }} />
        : <CloseCircleFilled style={{ color: '#ff4d4f', fontSize: 18 }} />,
    },
  ]

  const calcAge = (birth: string) => dayjs().diff(dayjs(birth), 'year')

  return (
    <Drawer
      open={clientId !== null}
      onClose={onClose}
      width={540}
      title={
        data ? (
          <Space>
            <Title level={5} style={{ margin: 0 }}>{data.child_name}</Title>
            {(() => {
              const t = CLIENT_STATUS[data.status]
              return t ? <Badge color={t.color} text={t.label} /> : null
            })()}
          </Space>
        ) : 'Карточка ученика'
      }
      loading={isLoading}
    >
      {data && (
        <Tabs
          items={[
            {
              key: 'contacts',
              label: 'Контакты',
              children: (
                <Descriptions column={1} bordered size="small">
                  <Descriptions.Item label="Ученик">{data.child_name}</Descriptions.Item>
                  <Descriptions.Item label="Возраст">
                    {calcAge(data.child_birth_date)} лет ({dayjs(data.child_birth_date).format('DD.MM.YYYY')})
                  </Descriptions.Item>
                  <Descriptions.Item label="Родитель">{data.parent_name}</Descriptions.Item>
                  <Descriptions.Item label="Телефон">{data.parent_phone}</Descriptions.Item>
                  {data.passport_data && (
                    <Descriptions.Item label="Паспорт">{data.passport_data}</Descriptions.Item>
                  )}
                  <Descriptions.Item label="В системе с">
                    {dayjs(data.created_at).format('DD.MM.YYYY')}
                  </Descriptions.Item>
                </Descriptions>
              ),
            },
            {
              key: 'finance',
              label: 'Финансы',
              children: (
                <>
                  {canManage && (
                    <div style={{ marginBottom: 12 }}>
                      <Button
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => setPaymentModal(true)}
                      >
                        Внести оплату
                      </Button>
                    </div>
                  )}
                  <Table
                    rowKey="id"
                    columns={paymentColumns}
                    dataSource={data.payments}
                    size="small"
                    pagination={false}
                    locale={{ emptyText: 'Платежей нет' }}
                  />
                </>
              ),
            },
            {
              key: 'attendance',
              label: 'Посещаемость',
              children: (
                <>
                  {data.attendance.length > 0 && (
                    <div style={{ marginBottom: 12 }}>
                      {(() => {
                        const total = data.attendance.length
                        const present = data.attendance.filter(a => a.present).length
                        const pct = Math.round((present / total) * 100)
                        return (
                          <Text>
                            Итого: <Text strong>{present}/{total}</Text> уроков ({pct}%)
                          </Text>
                        )
                      })()}
                    </div>
                  )}
                  <Table
                    rowKey="lesson_id"
                    columns={attColumns}
                    dataSource={data.attendance}
                    size="small"
                    pagination={false}
                    locale={{ emptyText: 'Данных посещаемости нет' }}
                  />
                </>
              ),
            },
            {
              key: 'contract',
              label: 'Договор',
              children: data.contract ? (
                <Descriptions column={1} bordered size="small">
                  <Descriptions.Item label="Статус">
                    {(() => {
                      const t = CONTRACT_STATUS[data.contract.status]
                      return t ? <Tag color={t.color}>{t.label}</Tag> : <Tag>{data.contract.status}</Tag>
                    })()}
                  </Descriptions.Item>
                  <Descriptions.Item label="Сумма">
                    {data.contract.amount.toLocaleString()} ₽
                  </Descriptions.Item>
                  {data.contract.signed_at && (
                    <Descriptions.Item label="Подписан">
                      {dayjs(data.contract.signed_at).format('DD.MM.YYYY')}
                    </Descriptions.Item>
                  )}
                  {data.contract.pdf_path && (
                    <Descriptions.Item label="Документ">
                      <Button
                        icon={<FilePdfOutlined />}
                        type="link"
                        style={{ padding: 0 }}
                        onClick={() => downloadPdf(data.contract!.id)}
                      >
                        Скачать PDF
                      </Button>
                    </Descriptions.Item>
                  )}
                </Descriptions>
              ) : (
                <Text type="secondary">Договор не найден</Text>
              ),
            },
          ]}
        />
      )}

      <Modal
        title="Внести оплату"
        open={paymentModal}
        onCancel={() => { setPaymentModal(false); form.resetFields() }}
        onOk={() => form.submit()}
        okText="Внести"
        confirmLoading={payMutation.isPending}
      >
        <Form form={form} layout="vertical" onFinish={(v) => payMutation.mutate(v)}>
          <Form.Item name="period" label="Период оплаты" rules={[{ required: true }]}>
            <DatePicker.RangePicker style={{ width: '100%' }} format="YYYY-MM-DD" />
          </Form.Item>
          <Form.Item name="amount" label="Сумма (₽)" rules={[{ required: true }]}>
            <InputNumber min={1} style={{ width: '100%' }} />
          </Form.Item>
          <Form.Item name="method" label="Способ оплаты" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'cash', label: 'Наличные' },
                { value: 'qr', label: 'QR / СБП' },
              ]}
            />
          </Form.Item>
        </Form>
      </Modal>
    </Drawer>
  )
}
