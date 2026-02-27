<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">主动探测仪表盘</h1>
        <p class="text-sm text-muted-foreground">探测任务、资产覆盖与扫描结果总览</p>
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
            <CardTitle class="text-base">今日探测重点</CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-sm text-muted-foreground">
            <div class="rounded-md border border-border bg-card px-3 py-2">高风险网段补扫任务待触发</div>
            <div class="rounded-md border border-border bg-card px-3 py-2">新增资产指纹识别结果待复核</div>
            <div class="rounded-md border border-border bg-card px-3 py-2">扫描失败目标重试队列待处理</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle class="text-base">探测链路状态</CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-sm text-muted-foreground">
            <div class="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span>任务调度</span>
              <span class="text-emerald-500">正常</span>
            </div>
            <div class="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span>扫描执行器</span>
              <span class="text-emerald-500">正常</span>
            </div>
            <div class="flex items-center justify-between rounded-md border border-border px-3 py-2">
              <span>结果入库</span>
              <span class="text-amber-500">建设中</span>
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
  { label: '待触发任务', value: 4 },
  { label: '运行中扫描', value: 9 },
  { label: '新增资产', value: 23 },
  { label: '高危发现', value: 5 },
])
</script>
