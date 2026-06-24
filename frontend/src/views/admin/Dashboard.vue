<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
</script>

<template>
  <el-card shadow="never">
    <template #header>
      <span>欢迎进入 WebGym 后台</span>
    </template>
    <el-descriptions :column="2" border>
      <el-descriptions-item label="用户名">{{ authStore.user?.username }}</el-descriptions-item>
      <el-descriptions-item label="角色">{{ authStore.role }}</el-descriptions-item>
      <el-descriptions-item label="姓名">{{ authStore.user?.real_name || '—' }}</el-descriptions-item>
      <el-descriptions-item label="电话">{{ authStore.user?.phone || '—' }}</el-descriptions-item>
    </el-descriptions>
    <el-alert
      style="margin-top: 16px"
      title="后台页面将在 W9 实现：会员、教练、卡、课程、排课、预约、统计。"
      type="info"
      :closable="false"
    />
  </el-card>
</template>
