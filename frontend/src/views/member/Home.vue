<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <span>欢迎，{{ authStore.user?.real_name || authStore.user?.username }}</span>
    </template>
    <el-empty description="会员端页面将在 W10 实现：我的卡 / 课程预约 / 我的预约 / 个人资料" />
  </el-card>
</template>
