/**
 * 认证状态。对照 Spring Security `SecurityContextHolder`，
 * 只存最小用户信息，权限校验靠 user.role 字段。
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authApi from '@/api/auth'
import type { CurrentUser, UserRole } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<CurrentUser | null>(null)
  const ready = ref(false)

  const isLoggedIn = computed(() => user.value !== null)
  const role = computed<UserRole | null>(() => user.value?.role ?? null)
  const isAdmin = computed(() => role.value === 'admin')
  const isStaff = computed(() => role.value === 'admin' || role.value === 'staff')
  const isMember = computed(() => role.value === 'member')

  async function fetchMe() {
    user.value = await authApi.fetchMe()
    ready.value = true
  }

  async function login(username: string, password: string) {
    user.value = await authApi.login(username, password)
  }

  async function logout() {
    try {
      await authApi.logout()
    } finally {
      user.value = null
    }
  }

  function hasRole(...roles: UserRole[]): boolean {
    return role.value !== null && roles.includes(role.value)
  }

  return {
    user,
    ready,
    isLoggedIn,
    role,
    isAdmin,
    isStaff,
    isMember,
    fetchMe,
    login,
    logout,
    hasRole,
  }
})
