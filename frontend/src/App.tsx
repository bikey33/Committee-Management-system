import { BrowserRouter, Routes, Route, Navigate, Outlet } from 'react-router-dom'
import { DashboardLayout } from './layouts/DashboardLayout'
import { CommitteesPage } from './pages/CommitteesPage'
import { DashboardPage } from './pages/DashboardPage'
import { OfficesPage } from './pages/OfficesPage'
import { UsersPage } from './pages/UsersPage'
import { LoginPage } from './pages/LoginPage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { Toaster } from 'sonner'

function App() {
  return (
    <>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          
          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardLayout><Outlet /></DashboardLayout>}>
              <Route index element={<DashboardPage />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/offices" element={<OfficesPage />} />
              <Route path="/committees" element={<CommitteesPage />} />
              <Route path="/users" element={<UsersPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
      <Toaster position="top-center" richColors />
    </>
  )
}

export default App
