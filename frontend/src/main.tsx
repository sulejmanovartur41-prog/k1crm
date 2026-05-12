import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import 'antd/dist/reset.css'
import dayjs from 'dayjs'
import 'dayjs/locale/ru'

import LoginPage from './pages/auth/LoginPage'
import AdminLayout from './layouts/AdminLayout'
import ManagerLayout from './layouts/ManagerLayout'
import TeacherLayout from './layouts/TeacherLayout'
import LeadsPage from './pages/leads/LeadsPage'
import LeadDetail from './pages/leads/LeadDetail'
import SchedulePage from './pages/schedule/SchedulePage'
import ContractsPage from './pages/contracts/ContractsPage'
import AttendancePage from './pages/attendance/AttendancePage'
import DashboardPage from './pages/payments/DashboardPage'
import ManagerHome from './pages/home/ManagerHome'
import TeacherHome from './pages/home/TeacherHome'
import GroupsPage from './pages/groups/GroupsPage'
import GroupDetail from './pages/groups/GroupDetail'
import { getRole, isAuthenticated } from './auth'

dayjs.locale('ru')

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
      staleTime: 30_000,
    },
  },
})

const ROLE_HOME: Record<string, string> = {
  admin:   '/admin',
  manager: '/manager',
  teacher: '/teacher',
}

function RoleGate({ role: required, children }: { role: string; children: React.ReactNode }) {
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  const role = getRole()
  if (role !== required) return <Navigate to={ROLE_HOME[role] ?? '/login'} replace />
  return <>{children}</>
}

function RootRedirect() {
  if (!isAuthenticated()) return <Navigate to="/login" replace />
  const role = getRole()
  return <Navigate to={ROLE_HOME[role] ?? '/login'} replace />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={ruRU}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />

            <Route path="/admin" element={<RoleGate role="admin"><AdminLayout /></RoleGate>}>
              <Route index element={<DashboardPage />} />
              <Route path="leads" element={<LeadsPage />} />
              <Route path="leads/:id" element={<LeadDetail />} />
              <Route path="groups" element={<GroupsPage />} />
              <Route path="groups/:id" element={<GroupDetail />} />
              <Route path="schedule" element={<SchedulePage />} />
              <Route path="contracts" element={<ContractsPage />} />
              <Route path="attendance" element={<AttendancePage />} />
            </Route>

            <Route path="/manager" element={<RoleGate role="manager"><ManagerLayout /></RoleGate>}>
              <Route index element={<ManagerHome />} />
              <Route path="leads" element={<LeadsPage />} />
              <Route path="leads/:id" element={<LeadDetail />} />
              <Route path="groups" element={<GroupsPage />} />
              <Route path="groups/:id" element={<GroupDetail />} />
              <Route path="schedule" element={<SchedulePage />} />
              <Route path="contracts" element={<ContractsPage />} />
            </Route>

            <Route path="/teacher" element={<RoleGate role="teacher"><TeacherLayout /></RoleGate>}>
              <Route index element={<TeacherHome />} />
              <Route path="schedule" element={<SchedulePage />} />
              <Route path="groups" element={<GroupsPage />} />
              <Route path="groups/:id" element={<GroupDetail />} />
              <Route path="attendance" element={<AttendancePage />} />
            </Route>

            <Route path="/" element={<RootRedirect />} />
            <Route path="*" element={<RootRedirect />} />
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
)
