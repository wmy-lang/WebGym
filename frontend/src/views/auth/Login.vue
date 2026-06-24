<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { fetchCsrfToken } from '@/api/http'

const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}
const formRef = ref<FormInstance>()
const loading = ref(false)

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

function homeFor(role: string | null): string {
  if (role === 'admin' || role === 'staff') return '/admin'
  if (role === 'member') return '/member'
  return '/login'
}

async function onSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await fetchCsrfToken()
    await authStore.login(form.username.trim(), form.password)
    ElMessage.success('登录成功')
    const redirect = (route.query.redirect as string) || homeFor(authStore.role)
    router.replace(redirect)
  } catch (err: any) {
    const code = err?.response?.data?.error
    if (code === 'invalid_credentials') ElMessage.error('用户名或密码错误')
    else if (code === 'account_disabled') ElMessage.error('账号已被禁用')
    else ElMessage.error('登录失败，请稍后再试')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <el-card class="login-card" shadow="hover">
      <div class="brand">
        <h1>WebGym</h1>
        <p>健身房会员信息管理系统</p>
      </div>
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="onSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            autocomplete="current-password"
            @keyup.enter="onSubmit"
          />
        </el-form-item>
        <el-button type="primary" :loading="loading" style="width: 100%" @click="onSubmit">
          登录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1f7af6 0%, #2dc4ad 100%);
}
.login-card {
  width: 380px;
  padding: 8px 12px;
}
.brand {
  text-align: center;
  margin-bottom: 24px;
}
.brand h1 {
  margin: 0;
  font-size: 28px;
  color: #1f7af6;
}
.brand p {
  margin: 4px 0 0;
  color: #909399;
  font-size: 14px;
}
</style>
