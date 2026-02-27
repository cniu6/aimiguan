<template>
  <div class="min-h-screen grid place-items-center bg-background px-4">
    <Card class="relative w-full max-w-[400px] border-border shadow-sm">
      <div class="absolute right-4 top-4">
        <Button
          type="button"
          variant="ghost"
          size="icon"
          class="size-8 cursor-pointer text-muted-foreground"
          :aria-label="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
          :title="isDarkMode ? '切换到浅色模式' : '切换到深色模式'"
          @click="toggleTheme"
        >
          <Sun v-if="isDarkMode" class="size-4" />
          <Moon v-else class="size-4" />
        </Button>
      </div>

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
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Separator } from '@/components/ui/separator'
import { ShieldCheck, XCircle, Loader2, Moon, Sun } from 'lucide-vue-next'

const router = useRouter()
const route = useRoute()
const form = ref({ username: '', password: '' })
const loading = ref(false)
const error = ref('')
const isDarkMode = ref(false)
const THEME_KEY = 'theme'

type ThemeMode = 'light' | 'dark'

const applyTheme = (mode: ThemeMode) => {
  const root = document.documentElement
  root.classList.toggle('dark', mode === 'dark')
  isDarkMode.value = mode === 'dark'
  localStorage.setItem(THEME_KEY, mode)
}

const initTheme = () => {
  const savedTheme = localStorage.getItem(THEME_KEY)
  if (savedTheme === 'light' || savedTheme === 'dark') {
    applyTheme(savedTheme)
    return
  }

  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  applyTheme(prefersDark ? 'dark' : 'light')
}

const toggleTheme = async (event?: MouseEvent) => {
  const newMode: ThemeMode = isDarkMode.value ? 'light' : 'dark'
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (reducedMotion) {
    applyTheme(newMode)
    return
  }

  const triggerElement = event?.currentTarget
  if (!(triggerElement instanceof HTMLElement)) {
    applyTheme(newMode)
    return
  }

  const rect = triggerElement.getBoundingClientRect()
  const x = rect.left + rect.width / 2
  const y = rect.top + rect.height / 2

  const { executeThemeAnimation, getAnimationConfig } = await import('@/composables/useThemeAnimation')
  const config = getAnimationConfig()

  if (config.type === 'view') {
    const root = document.documentElement
    root.classList.add('view-transitioning')
    isDarkMode.value = newMode === 'dark'
    localStorage.setItem(THEME_KEY, newMode)
    try {
      await executeThemeAnimation({ x, y, reducedMotion })
    } finally {
      root.classList.remove('view-transitioning')
    }
  } else {
    const animationPromise = executeThemeAnimation({ x, y, reducedMotion })
    setTimeout(() => {
      applyTheme(newMode)
    }, config.duration / 2)
    await animationPromise
  }
}

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
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : '/'
    router.push(redirect)
  } catch (err: any) {
    error.value = err.displayMessage || err.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  initTheme()
})
</script>
