<template>
  <div class="grid min-h-screen place-items-center bg-background px-6">
    <Card class="w-full max-w-[520px] border-border">
      <CardHeader class="space-y-2">
        <CardTitle class="text-2xl">403 无权限访问</CardTitle>
        <CardDescription>
          当前账号没有访问该页面的权限。请联系管理员授权，或返回工作台继续操作。
        </CardDescription>
      </CardHeader>
      <CardContent class="flex gap-3">
        <Button variant="outline" class="cursor-pointer" @click="goBack">返回上页</Button>
        <Button class="cursor-pointer" @click="goHome">回到仪表盘</Button>
      </CardContent>
    </Card>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const router = useRouter()

const goHome = () => {
  router.push('/defense/dashboard')
}

const goBack = () => {
  router.back()
}
</script>
