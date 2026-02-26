<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">审计中心</h1>
        <p class="text-sm text-muted-foreground">查询关键操作记录，按 trace_id 追溯全链路行为</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">快速检索</CardTitle>
        </CardHeader>
        <CardContent class="grid gap-3 md:grid-cols-3">
          <Input v-model="query.traceId" placeholder="trace_id" />
          <Input v-model="query.actor" placeholder="操作者" />
          <Input v-model="query.action" placeholder="动作关键字" />
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">最近审计事件（示例）</CardTitle>
        </CardHeader>
        <CardContent class="space-y-2">
          <div v-for="row in rows" :key="row.id" class="rounded-md border border-border px-3 py-2 text-sm">
            <div class="flex flex-wrap items-center justify-between gap-2">
              <span class="font-medium">{{ row.action }}</span>
              <span class="text-xs text-muted-foreground">{{ row.time }}</span>
            </div>
            <p class="mt-1 text-xs text-muted-foreground">
              actor={{ row.actor }} · target={{ row.target }} · trace_id={{ row.traceId }}
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'

const query = reactive({
  traceId: '',
  actor: '',
  action: '',
})

const rows = [
  {
    id: 1,
    action: 'set_mode:ACTIVE',
    actor: 'admin',
    target: 'system_mode',
    traceId: 'trace-20260226-001',
    time: '2026-02-26 11:20:00',
  },
  {
    id: 2,
    action: 'block_ip_execute',
    actor: 'defense_executor',
    target: 'execution_task:18',
    traceId: 'trace-20260226-004',
    time: '2026-02-26 11:18:20',
  },
]
</script>
