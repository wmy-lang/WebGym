<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const menu = [
  { path: '/admin', title: '工作台' },
  { path: '/admin/members', title: '会员管理' },
  { path: '/admin/cards', title: '会员卡' },
  { path: '/admin/card-types', title: '卡类型', roles: ['admin'] },
  { path: '/admin/coaches', title: '教练' },
  { path: '/admin/classes', title: '课程' },
  { path: '/admin/sessions', title: '排课' },
  { path: '/admin/bookings', title: '预约与签到' },
  { path: '/admin/stats', title: '统计' },
]

const visibleMenu = computed(() =>
  menu.filter((m) => !m.roles || (authStore.role && m.roles.includes(authStore.role))),
)

const activeMenu = computed(() => {
  // 精确匹配优先；否则取最长前缀
  const exact = menu.find((m) => m.path === route.path)
  if (exact) return exact.path
  const prefixed = menu
    .filter((m) => m.path !== '/admin' && route.path.startsWith(m.path))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return prefixed?.path ?? '/admin'
})

async function onLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', {
      type: 'warning',
    })
  } catch {
    return
  }
  await authStore.logout()
  ElMessage.success('已退出登录')
  router.replace('/login')
}
</script>

<template>
  <el-container class="admin-layout">
    <el-aside width="220px" class="aside">
      <div class="brand">
        <span class="logo">WebGym</span>
        <span class="tag">后台</span>
      </div>
      <el-menu :default-active="activeMenu" router :collapse="false" class="menu">
        <el-menu-item v-for="m in visibleMenu" :key="m.path" :index="m.path">
          {{ m.title }}
        </el-menu-item>
      </el-menu>
    </el-aside>
    <el-container>
      <el-header class="header">
        <div class="header-title">{{ route.meta.title || '工作台' }}</div>
        <div class="header-user">
          <el-tag size="small" type="info">{{ authStore.role }}</el-tag>
          <span class="username">{{ authStore.user?.real_name || authStore.user?.username }}</span>
          <el-button link type="primary" @click="onLogout">退出</el-button>
        </div>
      </el-header>
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<style scoped>
.admin-layout {
  height: 100vh;
}
.aside {
  background: #001529;
  color: #fff;
}
.brand {
  height: 60px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.brand .logo {
  font-size: 20px;
  font-weight: 600;
  color: #fff;
}
.brand .tag {
  font-size: 12px;
  color: #99a;
  border: 1px solid #99a;
  padding: 1px 6px;
  border-radius: 2px;
}
.menu {
  border-right: none;
  background: transparent;
}
.menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.75);
}
.menu :deep(.el-menu-item.is-active) {
  background: #1f7af6;
  color: #fff;
}
.menu :deep(.el-menu-item:hover) {
  background: rgba(255, 255, 255, 0.08);
}
.header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-title {
  font-size: 16px;
  font-weight: 500;
}
.header-user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.username {
  color: #303133;
  font-size: 14px;
}
.main {
  background: #f5f7fa;
  padding: 16px 20px;
}
</style>
