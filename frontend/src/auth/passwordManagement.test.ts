import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'

const read = (relative: string) => readFileSync(fileURLToPath(new URL(relative, import.meta.url)), 'utf8')

test('admin Security page exposes the complete change-password form', () => {
  const page = read('../pages/ChangePasswordPage.tsx')
  const routes = read('../routes/AppRoutes.tsx')
  assert.match(routes, /admin\/security/)
  assert.match(page, /Current password/)
  assert.match(page, /New password/)
  assert.match(page, /Confirm new password/)
  assert.match(page, /Password changed successfully/)
})

test('user management has a confirmed reset and one-time success result', () => {
  const page = read('../pages/admin/UserManagementPage.tsx')
  assert.match(page, />Reset password</)
  assert.match(page, /Confirm reset/)
  assert.match(page, /shown only once/)
  assert.match(page, /temporaryPassword/)
})

test('forced password change cannot be navigated around', () => {
  const guard = read('./ProtectedRoute.tsx')
  const routes = read('../routes/AppRoutes.tsx')
  assert.match(routes, /path="\/change-password"/)
  assert.match(guard, /currentUser\?\.must_change_password/)
  assert.match(guard, /Navigate to="\/change-password" replace/)
})
