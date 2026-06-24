<script setup lang="ts">
import { computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox, ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const menu = [
  { path: '/admin', title: '工作台', icon: 'House' },
  { path: '/admin/members', title: '会员管理', icon: 'User' },
  { path: '/admin/cards', title: '会员卡', icon: 'CreditCard' },
  { path: '/admin/coaches', title: '教练', icon: 'Avatar' },
  { path: '/admin/classes', title: '课程与排课', icon: 'Calendar' },
  { path: '/admin/bookings', title: '预约与签到', icon: 'Tickets' },
  { path: '/admin/stats', title: '统计', icon: 'DataAnalysis' },
]

const activeMenu = computed(() => {
  return menu.find((m) => route.path.startsWith(m.path) && m.path !== '/admin')?.path
    ?? '/admin'
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
        <el-menu-item v-for="m in menu" :key="m.path" :index="m.path">
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
