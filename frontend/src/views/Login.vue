<template>
  <div class="min-h-screen grid place-items-center bg-background px-4">
    <Card class="w-full max-w-[400px] border-border shadow-sm">
      <CardHeader class="space-y-2 text-center">
        <div class="mx-auto inline-flex size-12 items-center justify-center rounded-lg border border-border bg-muted">
          <ShieldCheck class="size-6 text-primary" />
        </div>
        <CardTitle class="text-2xl tracking-tight">AI 蜜罐</CardTitle>
        <CardDescription>智能安全运营平台</CardDescription>
      </CardHeader>

      <CardContent>
        <form @submit.prevent="handleLogin" class="space-y-4">
          <div class="space-y-2">
            <Label for="username" class="text-muted-foreground">用户名</Label>
            <Input
              id="username"
              v-model="form.username"
              type="text"
              required
              autocomplete="username"
              placeholder="请输入用户名"
            />
          </div>

          <div class="space-y-2">
            <Label for="password" class="text-muted-foreground">密码</Label>
            <Input
              id="password"
              v-model="form.password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </div>

          <Alert v-if="error" variant="destructive">
            <XCircle class="size-4" />
            <AlertDescription>{{ error }}</AlertDescription>
          </Alert>

          <Button type="submit" class="w-full cursor-pointer" :disabled="loading">
            <Loader2 v-if="loading" class="size-4 animate-spin" />
            {{ loading ? '验证中...' : '登录' }}
          </Button>
        </form>

        <Separator class="my-4" />
        <p class="text-center text-xs text-muted-foreground">默认账号: admin / admin123</p>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { ShieldCheck, XCircle, Loader2 } from 'lucide-vue-next'

const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    error.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  error.value = ''
  try {
    const res = await authApi.login(form.value)
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('user_info', JSON.stringify(res.user))
    router.push('/')
  } catch (err: any) {
    error.value = err.displayMessage || err.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}
</script>


