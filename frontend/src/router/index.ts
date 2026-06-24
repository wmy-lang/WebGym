/**
 * 路由 + 角色守卫。对照 Spring Security 的 SecurityFilterChain：
 *
 * - meta.requiresAuth：未登录 → 跳 /login。
 * - meta.roles：登录但角色不符 → 跳到角色对应首页（admin/staff → /admin；member → /member）。
 *
 * 真正的鉴权仍由后端 @role_required 兜底，前端守卫只为 UX。
 */
import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { UserRole } from '@/api/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    roles?: UserRole[]
    title?: string
  }
}

const routes: RouteRecordRaw[] = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { title: '登录' },
  },
  {
    path: '/admin',
    component: () => import('@/layouts/AdminLayout.vue'),
    meta: { requiresAuth: true, roles: ['admin', 'staff'] },
    children: [
      {
        path: '',
        name: 'admin-home',
        component: () => import('@/views/admin/Dashboard.vue'),
        meta: { title: '后台首页' },
      },
    ],
  },
  {
    path: '/member',
    component: () => import('@/layouts/MemberLayout.vue'),
    meta: { requiresAuth: true, roles: ['member'] },
    children: [
      {
        path: '',
        name: 'member-home',
        component: () => import('@/views/member/Home.vue'),
        meta: { title: '会员中心' },
      },
    ],
  },
  {
    path: '/',
    redirect: () => {
      // 实际重定向在守卫里完成（拿到 ready 后才知道角色）
      return '/login'
    },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/login',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

function homeFor(role: UserRole | null): string {
  if (role === 'admin' || role === 'staff') return '/admin'
  if (role === 'member') return '/member'
  return '/login'
}

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) {
    await auth.fetchMe()
  }

  // 已登录访问 /login → 回各自首页
  if (to.name === 'login' && auth.isLoggedIn) {
    return homeFor(auth.role)
  }

  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { path: '/login', query: { redirect: to.fullPath } }
  }

  if (to.meta.roles && auth.role && !to.meta.roles.includes(auth.role)) {
    return homeFor(auth.role)
  }

  if (to.meta.title) {
    document.title = `${to.meta.title} · WebGym`
  }
})

export default router
