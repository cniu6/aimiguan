import { createRouter, createWebHashHistory } from 'vue-router'
import DefenseDashboard from '../views/DefenseDashboard.vue'
import ScanManager from '../views/ScanManager.vue'
import AICenter from '../views/AICenter.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    {
      path: '/',
      redirect: '/defense'
    },
    {
      path: '/defense',
      name: 'defense',
      component: DefenseDashboard
    },
    {
      path: '/scan',
      name: 'scan',
      component: ScanManager
    },
    {
      path: '/ai',
      name: 'ai',
      component: AICenter
    }
  ]
})

export default router