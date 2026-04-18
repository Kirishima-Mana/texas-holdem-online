import { createRouter, createWebHistory } from 'vue-router'
import Login from '@/components/Login.vue'
import Lobby from '@/components/Lobby.vue'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    redirect: '/login'
  },
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false }
  },
  {
    path: '/lobby',
    name: 'Lobby',
    component: Lobby,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    // 需要认证但未登录，重定向到登录页
    next('/login')
  } else if (to.path === '/login' && authStore.isAuthenticated) {
    // 已登录但访问登录页，重定向到大厅
    next('/lobby')
  } else {
    next()
  }
})

export default router