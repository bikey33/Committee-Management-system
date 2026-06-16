import { BrowserRouter, Routes, Route, Outlet } from 'react-router-dom'
import { DashboardLayout } from './layouts/DashboardLayout'
import { CommitteesPage } from './pages/CommitteesPage'
import { DashboardPage } from './pages/DashboardPage'
import { OfficesPage } from './pages/OfficesPage'
import { UsersPage } from './pages/UsersPage'
import { EmployeesPage } from './pages/EmployeesPage'
import { ReportsPage } from './pages/ReportsPage'
import { RolesPage } from './pages/RolesPage'
import { LoginPage } from './pages/LoginPage'
import { SignupPage } from './pages/SignupPage'
import { ChangePasswordPage } from './pages/ChangePasswordPage'
import { ProtectedRoute } from './components/ProtectedRoute'
import { PermissionProvider } from './contexts/PermissionContext'
import { Toaster } from 'sonner'

function App() {
  return (
    <>
      <PermissionProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />

            <Route element={<ProtectedRoute />}>
              <Route path="/change-password" element={<ChangePasswordPage />} />
              <Route element={<DashboardLayout><Outlet /></DashboardLayout>}>
                <Route index element={<DashboardPage />} />
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route element={<ProtectedRoute requiredPermission="settings.offices" />}>
                  <Route path="/offices" element={<OfficesPage />} />
                </Route>
                <Route element={<ProtectedRoute requiredPermission="committee.view" />}>
                  <Route path="/committees" element={<CommitteesPage />} />
                </Route>
                <Route element={<ProtectedRoute requiredPermission="users.view" />}>
                  <Route path="/employees" element={<EmployeesPage />} />
                  <Route path="/users" element={<UsersPage />} />
                </Route>
                <Route element={<ProtectedRoute requiredPermission="reports.view" />}>
                  <Route path="/reports" element={<ReportsPage />} />
                </Route>
                <Route element={<ProtectedRoute requiredPermission="roles.manage" />}>
                  <Route path="/roles" element={<RolesPage />} />
                </Route>
              </Route>
            </Route>
          </Routes>
        </BrowserRouter>
      </PermissionProvider>
      <Toaster position="top-center" richColors />
    </>
  )
}

export default App
