import { createRouter, createWebHashHistory } from 'vue-router'
import Layout from '../components/Layout.vue'
import DefenseDashboard from '../views/DefenseDashboard.vue'
import ScanManager from '../views/ScanManager.vue'
import AICenter from '../views/AICenter.vue'
import Login from '../views/Login.vue'
import DefenseRealtime from '../views/DefenseRealtime.vue'
import ProbeRealtime from '../views/ProbeRealtime.vue'
import SettingsPage from '../views/SettingsPage.vue'
import ProfilePage from '../views/ProfilePage.vue'
import OverviewPage from '../views/OverviewPage.vue'
import IntegrationsPage from '../views/IntegrationsPage.vue'
import AuditPage from '../views/AuditPage.vue'
import ForbiddenPage from '../views/ForbiddenPage.vue'

type UserRole = 'admin' | 'operator' | 'viewer'

interface UserInfo {
  username?: string
  role?: string
}

const allowedRolesMap: Record<UserRole, UserRole[]> = {
  admin: ['admin', 'operator', 'viewer'],
  operator: ['operator', 'viewer'],
  viewer: ['viewer'],
}

const parseUserInfo = (): UserInfo | null => {
  const raw = localStorage.getItem('user_info')
  if (!raw) return null
  try {
    return JSON.parse(raw) as UserInfo
  } catch {
    return null
  }
}

const hasRoleAccess = (requiredRoles?: UserRole[]): boolean => {
  if (!requiredRoles || requiredRoles.length === 0) return true
  const user = parseUserInfo()
  const role = (user?.role || 'viewer') as UserRole
  const granted = allowedRolesMap[role] || ['viewer']
  return requiredRoles.some((required) => granted.includes(required))
}

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: Login,
      meta: { requiresAuth: false }
    },
    {
      path: '/forbidden',
      name: 'forbidden',
      component: ForbiddenPage,
      meta: { requiresAuth: true }
    },
    {
      path: '/',
      component: Layout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/overview'
        },
        {
          path: '/overview',
          name: 'overview',
          component: OverviewPage
        },
        {
          path: '/defense/realtime',
          name: 'defense-realtime',
          component: DefenseRealtime
        },
        {
          path: '/defense/events',
          name: 'defense-events',
          component: DefenseDashboard
        },
        {
          path: '/defense/ai',
          name: 'defense-ai',
          component: AICenter
        },
        {
          path: '/probe/realtime',
          name: 'probe-realtime',
          component: ProbeRealtime
        },
        {
          path: '/probe/scan',
          name: 'probe-scan',
          component: ScanManager
        },
        {
          path: '/probe/ai',
          name: 'probe-ai',
          component: AICenter
        },
        {
          path: '/settings',
          name: 'settings',
          component: SettingsPage
        },
        {
          path: '/integrations',
          name: 'integrations',
          component: IntegrationsPage,
          meta: { requiredRoles: ['operator', 'admin'] }
        },
        {
          path: '/audit',
          name: 'audit',
          component: AuditPage,
          meta: { requiredRoles: ['operator', 'admin'] }
        },
        {
          path: '/profile',
          name: 'profile',
          component: ProfilePage
        },
        {
          path: '/defense',
          redirect: '/defense/realtime'
        },
        {
          path: '/scan',
          redirect: '/probe/scan'
        },
        {
          path: '/ai',
          redirect: '/defense/ai'
        },
        {
          path: '/ai-center',
          redirect: '/defense/ai'
        }
      ]
    }
  ]
})

// Route guard
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')

  if (to.meta.requiresAuth !== false && !token) {
    next({ path: '/login', query: { redirect: to.fullPath } })
    return
  } else if (to.path === '/login' && token) {
    next('/')
    return
  }

  const requiredRoles = to.meta.requiredRoles as UserRole[] | undefined
  if (to.meta.requiresAuth !== false && !hasRoleAccess(requiredRoles)) {
    next('/forbidden')
    return
  }

  if (to.matched.length === 0) {
    next('/overview')
  } else {
    next()
  }
})

export default router
