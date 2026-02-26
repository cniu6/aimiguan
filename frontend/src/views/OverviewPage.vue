<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">总览</h1>
        <p class="text-sm text-muted-foreground">平台核心指标与待处理事项总览</p>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card v-for="item in metrics" :key="item.label">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm font-medium text-muted-foreground">{{ item.label }}</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-2xl font-semibold">{{ item.value }}</p>
          </CardContent>
        </Card>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle class="text-base">今日关键待办</CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-sm text-muted-foreground">
            <div class="rounded-md border border-border bg-card px-3 py-2">补齐待审批筛选接口（Step 3.16）</div>
            <div class="rounded-md border border-border bg-card px-3 py-2">MCP block_ip 改为真实通信实现</div>
            <div class="rounded-md border border-border bg-card px-3 py-2">推进 Step 4 扫描链路最小闭环</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle class="text-base">链路健康状态</CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-sm text-muted-foreground">
            <div class="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span>防御链路</span>
              <span class="text-emerald-500">已贯通</span>
            </div>
            <div class="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span>扫描链路</span>
              <span class="text-amber-500">建设中</span>
            </div>
            <div class="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span>外部联动</span>
              <span class="text-amber-500">部分可用</span>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const metrics = computed(() => [
  { label: '待审批事件', value: 6 },
  { label: '今日封禁成功', value: 18 },
  { label: '扫描进行中', value: 7 },
  { label: '审计日志写入', value: '1.2k' },
])
</script>
