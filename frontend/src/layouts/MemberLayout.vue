<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const menu = [
  { path: '/member', title: '首页' },
  { path: '/member/cards', title: '我的会员卡' },
  { path: '/member/classes', title: '可预约课程' },
  { path: '/member/bookings', title: '我的预约' },
  { path: '/member/profile', title: '个人资料' },
]

const activePath = computed(() => {
  return menu.find((m) => route.path.startsWith(m.path) && m.path !== '/member')?.path
    ?? '/member'
})

async function onLogout() {
  try {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
  } catch {
    return
  }
  await authStore.logout()
  ElMessage.success('已退出登录')
  router.replace('/login')
}
</script>

<template>
  <el-container class="member-layout">
    <el-header class="header">
      <div class="header-inner">
        <div class="brand">WebGym <span class="tag">会员中心</span></div>
        <el-menu :default-active="activePath" mode="horizontal" router class="menu">
          <el-menu-item v-for="m in menu" :key="m.path" :index="m.path">
            {{ m.title }}
          </el-menu-item>
        </el-menu>
        <div class="user">
          <span class="hi">你好，{{ authStore.user?.real_name || authStore.user?.username }}</span>
          <el-button link type="primary" @click="onLogout">退出</el-button>
        </div>
      </div>
    </el-header>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<style scoped>
.member-layout {
  min-height: 100vh;
}
.header {
  background: #fff;
  border-bottom: 1px solid #ebeef5;
  padding: 0;
}
.header-inner {
  max-width: 1200px;
  margin: 0 auto;
  height: 60px;
  display: flex;
  align-items: center;
  gap: 24px;
}
.brand {
  font-size: 20px;
  font-weight: 600;
  color: #1f7af6;
}
.brand .tag {
  margin-left: 6px;
  font-size: 12px;
  color: #909399;
  font-weight: 400;
  border: 1px solid #dcdfe6;
  padding: 1px 6px;
  border-radius: 2px;
  vertical-align: middle;
}
.menu {
  flex: 1;
  border-bottom: none;
}
.user {
  display: flex;
  align-items: center;
  gap: 12px;
}
.hi {
  color: #606266;
  font-size: 14px;
}
.main {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 16px;
  width: 100%;
}
</style>
