<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { fetchCsrfToken } from '@/api/http'

const authStore = useAuthStore()

onMounted(async () => {
  await fetchCsrfToken()
  await authStore.fetchMe()
})
</script>

<template>
  <router-view />
</template>
