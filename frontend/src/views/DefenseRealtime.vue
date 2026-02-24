<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <div>
        <h1 class="text-2xl font-semibold">实时检测</h1>
        <p class="mt-1 text-sm text-muted-foreground">防御坚守模式下的实时威胁态势大屏</p>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle class="text-base">当前高危事件</CardTitle></CardHeader>
          <CardContent class="text-3xl font-semibold">12</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle class="text-base">5分钟新增告警</CardTitle></CardHeader>
          <CardContent class="text-3xl font-semibold">28</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle class="text-base">封禁执行成功率</CardTitle></CardHeader>
          <CardContent class="text-3xl font-semibold">98.4%</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">实时检测流</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid gap-3 text-sm text-muted-foreground md:grid-cols-2">
            <div class="rounded-md border border-border bg-card p-3">[01:31:02] 告警命中: 101.30.14.2 / SSH 爆破</div>
            <div class="rounded-md border border-border bg-card p-3">[01:31:09] AI 风险评分: 86 / 建议封禁</div>
            <div class="rounded-md border border-border bg-card p-3">[01:31:16] 执行器下发: edge-switch-03</div>
            <div class="rounded-md border border-border bg-card p-3">[01:31:22] 回执: 成功 / trace_id: evt_8fa2</div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
</script>
