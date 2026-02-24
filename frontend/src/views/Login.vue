<template>
  <div class="min-h-screen flex flex-col items-center justify-center relative overflow-hidden bg-background">
    <!-- Animated grid background -->
    <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,.06)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,.06)_1px,transparent_1px)] bg-[length:48px_48px] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_40%,black_40%,transparent_100%)] animate-[grid-drift_20s_linear_infinite]" aria-hidden="true" />

    <!-- Login card -->
    <Card class="w-full max-w-[400px] mx-4 backdrop-blur-xl bg-card/75 border-border/60 shadow-[0_0_60px_rgba(59,130,246,.08),0_8px_32px_rgba(0,0,0,.4)] animate-in fade-in slide-in-from-bottom-4 duration-500">
      <CardHeader class="text-center pb-0">
        <div class="inline-flex items-center justify-center size-14 rounded-xl bg-primary/10 border border-primary/25 mx-auto">
          <ShieldCheck class="size-8 text-primary" />
        </div>
        <CardTitle class="text-2xl tracking-tight mt-4">AI 蜜罐</CardTitle>
        <CardDescription>智能安全运营平台</CardDescription>
      </CardHeader>

      <CardContent>
        <form @submit.prevent="handleLogin" class="space-y-5">
          <div class="space-y-2">
            <Label for="username" class="text-muted-foreground">
              <User class="size-3.5 opacity-60" />
              用户名
            </Label>
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
            <Label for="password" class="text-muted-foreground">
              <Lock class="size-3.5 opacity-60" />
              密码
            </Label>
            <Input
              id="password"
              v-model="form.password"
              type="password"
              required
              autocomplete="current-password"
              placeholder="请输入密码"
            />
          </div>

          <!-- Error -->
          <Alert v-if="error" variant="destructive">
            <XCircle class="size-4" />
            <AlertDescription>{{ error }}</AlertDescription>
          </Alert>

          <!-- Submit -->
          <Button type="submit" class="w-full cursor-pointer" :disabled="loading">
            <Loader2 v-if="loading" class="size-4 animate-spin" />
            {{ loading ? '验证中...' : '登录' }}
          </Button>
        </form>

        <Separator class="my-5" />
        <p class="text-xs text-muted-foreground/70 text-center">默认账号: admin / admin123</p>
      </CardContent>
    </Card>

    <p class="absolute bottom-4 text-xs text-muted-foreground/40 select-none">v0.1.0</p>
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
import { ShieldCheck, User, Lock, XCircle, Loader2 } from 'lucide-vue-next'

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

<style>
@keyframes grid-drift {
  0%   { background-position: 0 0; }
  100% { background-position: 48px 48px; }
}
</style>
