<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1200px] space-y-6">
      <div>
        <h1 class="text-2xl font-semibold">用户中心</h1>
        <p class="mt-1 text-sm text-muted-foreground">当前用户信息与安全设置入口</p>
      </div>

      <Card>
        <CardHeader><CardTitle class="text-base">账户信息</CardTitle></CardHeader>
        <CardContent class="grid gap-2 text-sm text-muted-foreground sm:grid-cols-2">
          <p>用户名：{{ username }}</p>
          <p>角色：{{ role }}</p>
          <p>最近登录：{{ lastLogin }}</p>
          <p>状态：正常</p>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const user = computed(() => {
  const raw = localStorage.getItem('user_info')
  return raw ? JSON.parse(raw) : { username: 'user', role: 'viewer' }
})

const username = computed(() => user.value.username || 'user')
const role = computed(() => user.value.role || 'viewer')
const lastLogin = computed(() => new Date().toLocaleString('zh-CN'))
</script>
