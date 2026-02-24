<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1200px] space-y-6">
      <div>
        <h1 class="text-2xl font-semibold">系统设置</h1>
        <p class="mt-1 text-sm text-muted-foreground">系统级配置与管理入口</p>
      </div>

      <div class="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader><CardTitle class="text-base">模式与策略</CardTitle></CardHeader>
          <CardContent class="text-sm text-muted-foreground">主动/被动策略、阈值、默认动作配置</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle class="text-base">权限与审计</CardTitle></CardHeader>
          <CardContent class="text-sm text-muted-foreground">角色权限、高风险动作审计、trace 检索</CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
</script>
