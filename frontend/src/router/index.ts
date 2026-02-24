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
      path: '/',
      component: Layout,
      meta: { requiresAuth: true },
      children: [
        {
          path: '',
          redirect: '/defense/realtime'
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
        }
      ]
    }
  ]
})

// Route guard
router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('access_token')
  
  if (to.meta.requiresAuth !== false && !token) {
    next('/login')
  } else if (to.path === '/login' && token) {
    next('/')
  } else {
    next()
  }
})

export default router
