import { Navigate, Route, Routes } from 'react-router-dom'
import { AppLayout } from '@/layouts/AppLayout'
import { ProjectsListPage } from '@/pages/ProjectsListPage'
import { NewProjectPage } from '@/pages/NewProjectPage'
import { SetupPage } from '@/pages/SetupPage'
import { ProductsPage } from '@/pages/ProductsPage'
import { StaffingPage } from '@/pages/StaffingPage'
import {
  RevenueWorkspace,
  DirectCostsWorkspace,
  OperatingExpensesWorkspace,
} from '@/pages/SectionWorkspace'
import { StartupCostsPage } from '@/pages/StartupCostsPage'
import { FixedAssetsWorkspace } from '@/pages/FixedAssetsWorkspace'
import { WorkingCapitalPage } from '@/pages/WorkingCapitalPage'
import { FinancingPage } from '@/pages/FinancingPage'
import { TaxPage } from '@/pages/TaxPage'
import { ScenariosPage } from '@/pages/ScenariosPage'
import { KPIsPage } from '@/pages/KPIsPage'
import { ReviewPage } from '@/pages/ReviewPage'
import { IncomeStatementPage } from '@/pages/IncomeStatementPage'
import { BalanceSheetPage } from '@/pages/BalanceSheetPage'
import { CashFlowPage } from '@/pages/CashFlowPage'
import { FinancialAnalysisPage } from '@/pages/FinancialAnalysisPage'
import { ReportsPage } from '@/pages/ReportsPage'
import { TextBuilderPage } from '@/pages/TextBuilderPage'
import { LoginPage } from '@/pages/LoginPage'
import { GuidePage } from '@/pages/GuidePage'
import { UserManagementPage } from '@/pages/admin/UserManagementPage'
import { ChangePasswordPage } from '@/pages/ChangePasswordPage'
import { ProtectedRoute, AdminRoute } from '@/auth/ProtectedRoute'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route element={<ProtectedRoute />}>
      <Route path="/change-password" element={<ChangePasswordPage />} />
      <Route path="/" element={<Navigate to="/projects" replace />} />
      <Route path="/projects" element={<ProjectsListPage />} />
      <Route path="/projects/new" element={<NewProjectPage />} />
      <Route path="/guide" element={<GuidePage />} />
      <Route element={<AdminRoute />}>
        <Route path="/admin/users" element={<UserManagementPage />} />
        <Route path="/admin/security" element={<ChangePasswordPage />} />
      </Route>

      <Route path="/projects/:projectId" element={<AppLayout />}>
        <Route index element={<Navigate to="setup" replace />} />
        <Route path="setup" element={<SetupPage />} />
        <Route path="products" element={<ProductsPage />} />
        <Route path="revenue" element={<RevenueWorkspace />} />
        <Route path="direct-costs" element={<DirectCostsWorkspace />} />
        <Route path="staffing" element={<StaffingPage />} />
        <Route path="operating-expenses" element={<OperatingExpensesWorkspace />} />
        <Route path="startup-costs" element={<StartupCostsPage />} />
        <Route path="fixed-assets" element={<FixedAssetsWorkspace />} />
        <Route path="working-capital" element={<WorkingCapitalPage />} />
        <Route path="financing" element={<FinancingPage />} />
        <Route path="tax" element={<TaxPage />} />
        <Route path="scenarios" element={<ScenariosPage />} />
        <Route path="kpis" element={<KPIsPage />} />
        <Route path="review" element={<ReviewPage />} />
        <Route path="text-builder" element={<TextBuilderPage />} />
        <Route path="income-statement" element={<IncomeStatementPage />} />
        <Route path="balance-sheet" element={<BalanceSheetPage />} />
        <Route path="cash-flow" element={<CashFlowPage />} />
        <Route path="financial-analysis" element={<FinancialAnalysisPage />} />
        <Route path="reports" element={<ReportsPage />} />
      </Route>
      </Route>

      <Route path="*" element={<Navigate to="/projects" replace />} />
    </Routes>
  )
}
