import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import AdminLayout from '../components/AdminLayout.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    component: AdminLayout,
    children: [
      { path: '', redirect: '/dashboard' },
      { path: 'dashboard', name: 'Dashboard', component: () => import('../views/Dashboard.vue'), meta: { title: '运营概览', icon: 'Odometer' } },
      { path: 'tickets', name: 'Tickets', component: () => import('../views/Tickets.vue'), meta: { title: '工单管理', icon: 'Ticket' } },
      { path: 'conversations', name: 'Conversations', component: () => import('../views/Conversations.vue'), meta: { title: '对话历史', icon: 'ChatDotRound' } },
      { path: 'users', name: 'Users', component: () => import('../views/Users.vue'), meta: { title: '用户管理', icon: 'User' } },
      { path: 'billing', name: 'Billing', component: () => import('../views/Billing.vue'), meta: { title: '用量计费', icon: 'Coin' } },
      { path: 'settings', name: 'Settings', component: () => import('../views/Settings.vue'), meta: { title: '系统设置', icon: 'Setting' } },
    ],
  },
]

const router = createRouter({
  history: createWebHistory('/admin/'),
  routes,
})

router.beforeEach((to, from, next) => {
  const auth = useAuthStore()
  if (!auth.isLoggedIn && !to.meta.guest) next('/login')
  else if (auth.isLoggedIn && to.meta.guest) next('/dashboard')
  else next()
})

export default router
