import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ConfigProvider } from 'antd'
import ruRU from 'antd/locale/ru_RU'
import 'antd/dist/reset.css'

import LoginPage from './pages/auth/LoginPage'
import AppLayout from './components/AppLayout'
import LeadsPage from './pages/leads/LeadsPage'
import LeadDetail from './pages/leads/LeadDetail'
import SchedulePage from './pages/schedule/SchedulePage'
import ContractsPage from './pages/contracts/ContractsPage'
import AttendancePage from './pages/attendance/AttendancePage'
import DashboardPage from './pages/payments/DashboardPage'

const queryClient = new QueryClient()

function PrivateRoute({ children }: { children: React.ReactNode }) {
  const token = localStorage.getItem('token')
  return token ? <>{children}</> : <Navigate to="/login" replace />
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider locale={ruRU}>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route
              path="/"
              element={
                <PrivateRoute>
                  <AppLayout />
                </PrivateRoute>
              }
            >
              <Route index element={<Navigate to="/leads" replace />} />
              <Route path="leads" element={<LeadsPage />} />
              <Route path="leads/:id" element={<LeadDetail />} />
              <Route path="schedule" element={<SchedulePage />} />
              <Route path="contracts" element={<ContractsPage />} />
              <Route path="attendance" element={<AttendancePage />} />
              <Route path="dashboard" element={<DashboardPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  </React.StrictMode>
)
