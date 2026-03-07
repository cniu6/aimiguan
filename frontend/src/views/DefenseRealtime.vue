<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold flex items-center gap-2">
            <span
              class="inline-flex size-2.5 rounded-full"
              :class="polling ? 'bg-emerald-500 animate-pulse' : 'bg-muted-foreground'"
            />
            实时检测
          </h1>
          <p class="text-sm text-muted-foreground">防御坚守模式下的实时威胁态势大屏 · 每 {{ INTERVAL }}s 自动刷新</p>
        </div>
        <div class="flex items-center gap-2">
          <span class="text-xs text-muted-foreground">{{ lastUpdated }}</span>
          <Button variant="outline" size="sm" class="cursor-pointer gap-1.5" @click="refresh">
            <RefreshCw class="size-3.5" :class="loading ? 'animate-spin' : ''" />
            立即刷新
          </Button>
        </div>
      </div>

      <!-- Metrics -->
      <div class="grid gap-4 sm:grid-cols-3">
        <Card>
          <CardContent class="pt-5 pb-4 flex items-center gap-4">
            <div class="size-10 rounded-lg flex items-center justify-center bg-red-500/10 shrink-0">
              <AlertTriangle class="size-5 text-red-400" />
            </div>
            <div>
              <p class="text-2xl font-bold tabular-nums" :class="metrics.highRisk > 0 ? 'text-red-400' : 'text-foreground'">
                {{ loading ? '—' : metrics.highRisk }}
              </p>
              <p class="text-xs text-muted-foreground mt-0.5">当前高危事件</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="pt-5 pb-4 flex items-center gap-4">
            <div class="size-10 rounded-lg flex items-center justify-center bg-amber-500/10 shrink-0">
              <Bell class="size-5 text-amber-400" />
            </div>
            <div>
              <p class="text-2xl font-bold tabular-nums">{{ loading ? '—' : metrics.todayAlerts }}</p>
              <p class="text-xs text-muted-foreground mt-0.5">今日新增告警</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="pt-5 pb-4 flex items-center gap-4">
            <div class="size-10 rounded-lg flex items-center justify-center bg-emerald-500/10 shrink-0">
              <ShieldCheck class="size-5 text-emerald-400" />
            </div>
            <div>
              <p class="text-2xl font-bold tabular-nums" :class="metrics.blockRate >= 90 ? 'text-emerald-400' : 'text-amber-400'">
                {{ loading ? '—' : metrics.blockRate + '%' }}
              </p>
              <p class="text-xs text-muted-foreground mt-0.5">封禁执行成功率</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div class="grid gap-4 lg:grid-cols-2">
        <!-- 实时事件流 -->
        <Card>
          <CardHeader class="pb-3 flex-row items-center justify-between">
            <CardTitle class="text-base flex items-center gap-2">
              <span class="inline-flex size-1.5 rounded-full bg-red-500 animate-pulse" />
              实时威胁流
            </CardTitle>
            <span class="text-xs text-muted-foreground">最近 {{ eventStream.length }} 条</span>
          </CardHeader>
          <CardContent class="space-y-1.5 max-h-[380px] overflow-y-auto pr-1">
            <div v-if="loading && eventStream.length === 0" class="space-y-1.5">
              <Skeleton v-for="i in 5" :key="i" class="h-10 w-full rounded" />
            </div>
            <div v-else-if="eventStream.length === 0" class="py-8 text-center text-sm text-muted-foreground">
              暂无实时事件，持续监控中…
            </div>
            <div
              v-for="ev in eventStream"
              :key="ev.id"
              class="flex items-start gap-2.5 rounded-md border border-border px-3 py-2 text-xs transition-colors"
              :class="ev.isNew ? 'bg-primary/5 border-primary/30' : ''"
            >
              <code class="shrink-0 text-muted-foreground/70 mt-0.5">{{ ev.time }}</code>
              <div class="min-w-0 flex-1">
                <span class="font-mono text-muted-foreground">{{ ev.ip }}</span>
                <span class="mx-1 text-muted-foreground/50">/</span>
                <span>{{ ev.label }}</span>
              </div>
              <Badge
                :class="scoreColor(ev.score)"
                class="text-[10px] h-4 shrink-0"
              >{{ ev.score }}</Badge>
            </div>
          </CardContent>
        </Card>

        <!-- 高危待处理 + 审计日志 -->
        <div class="space-y-4">
          <!-- 高危待处理 -->
          <Card>
            <CardHeader class="pb-3">
              <CardTitle class="text-base">高危待处理（AI 分 ≥ 80）</CardTitle>
            </CardHeader>
            <CardContent class="space-y-1.5">
              <div v-if="loading" class="space-y-1.5">
                <Skeleton v-for="i in 3" :key="i" class="h-8 w-full rounded" />
              </div>
              <div v-else-if="highRiskList.length === 0" class="py-4 text-center text-xs text-muted-foreground">
                暂无高危待处理事件
              </div>
              <div
                v-for="ev in highRiskList"
                :key="ev.id"
                class="flex items-center justify-between rounded-md border border-red-500/20 bg-red-500/5 px-3 py-2 text-xs gap-2"
              >
                <div class="flex items-center gap-2 min-w-0">
                  <code class="font-mono text-red-300 shrink-0">{{ ev.ip }}</code>
                  <span class="text-muted-foreground truncate">{{ ev.label }}</span>
                </div>
                <div class="flex items-center gap-1.5 shrink-0">
                  <Badge class="bg-red-500/20 text-red-400 border-red-500/30 text-[10px] h-4">{{ ev.score }}</Badge>
                  <span class="text-muted-foreground/60">{{ ev.time }}</span>
                </div>
              </div>
            </CardContent>
          </Card>

          <!-- 最近审计快照 -->
          <Card>
            <CardHeader class="pb-3 flex-row items-center justify-between">
              <CardTitle class="text-base">审计快照</CardTitle>
              <router-link to="/audit">
                <Button variant="ghost" size="sm" class="cursor-pointer text-xs gap-1 h-7">
                  <ExternalLink class="size-3" />
                  全部
                </Button>
              </router-link>
            </CardHeader>
            <CardContent class="space-y-1.5">
              <div v-if="auditLoading" class="space-y-1.5">
                <Skeleton v-for="i in 3" :key="i" class="h-8 w-full rounded" />
              </div>
              <div v-else-if="auditItems.length === 0" class="py-4 text-center text-xs text-muted-foreground">
                暂无审计记录
              </div>
              <div
                v-for="a in auditItems"
                :key="a.id"
                class="flex items-center justify-between rounded-md border border-border px-3 py-1.5 text-xs"
              >
                <div class="flex items-center gap-2 min-w-0">
                  <span class="font-medium truncate">{{ a.action }}</span>
                  <span class="text-muted-foreground shrink-0">{{ a.actor }}</span>
                </div>
                <Badge
                  :class="a.result === 'success' ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-destructive/15 text-destructive'"
                  class="text-[10px] h-4 shrink-0"
                >{{ a.result }}</Badge>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { apiClient } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { AlertTriangle, Bell, ExternalLink, RefreshCw, ShieldCheck } from 'lucide-vue-next'

const INTERVAL = 15
const MAX_STREAM = 30

interface StreamEvent {
  id: number
  ip: string
  label: string
  score: number
  time: string
  isNew: boolean
}

interface AuditItem {
  id: number
  actor: string
  action: string
  result: string
}

const loading = ref(false)
const auditLoading = ref(false)
const polling = ref(false)
const lastUpdated = ref('')

const metrics = ref({ highRisk: 0, todayAlerts: 0, blockRate: 0 })
const eventStream = ref<StreamEvent[]>([])
const highRiskList = ref<StreamEvent[]>([])
const auditItems = ref<AuditItem[]>([])

let pollTimer: ReturnType<typeof setInterval> | null = null
let seenIds = new Set<number>()

const loadMetrics = async () => {
  try {
    const res: any = await apiClient.get('/overview/metrics')
    const d = res?.data ?? res
    metrics.value = {
      highRisk: d?.defense?.high_risk_pending ?? 0,
      todayAlerts: d?.defense?.today_alerts ?? 0,
      blockRate: d?.defense?.block_success_rate ?? 0,
    }
  } catch { /* ignore */ }
}

const loadEvents = async () => {
  try {
    const res: any = await apiClient.get('/defense/events', {
      params: { page: 1, page_size: 20, status: 'PENDING', sort: '-created_at' },
    })
    const items: any[] = res?.data?.items ?? res?.items ?? []

    const newEntries: StreamEvent[] = []
    for (const ev of items) {
      const isNew = !seenIds.has(ev.id)
      if (isNew) seenIds.add(ev.id)
      newEntries.push({
        id: ev.id,
        ip: ev.ip || ev.source_ip || '—',
        label: ev.event_type || ev.action_type || '未知威胁',
        score: ev.ai_score ?? 0,
        time: ev.created_at
          ? new Date(ev.created_at).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
          : '—',
        isNew,
      })
    }

    // Prepend new items, keep MAX_STREAM entries
    const merged = [...newEntries, ...eventStream.value.filter((e) => !newEntries.find((n) => n.id === e.id))]
    eventStream.value = merged.slice(0, MAX_STREAM).map((e, i) => ({ ...e, isNew: i < newEntries.length && e.isNew }))

    // High-risk subset
    highRiskList.value = eventStream.value.filter((e) => e.score >= 80).slice(0, 8)
  } catch { /* ignore */ }
}

const loadAudit = async () => {
  auditLoading.value = true
  try {
    const res: any = await apiClient.get('/system/audit/logs', { params: { page: 1, page_size: 5 } })
    const d = res?.data ?? res
    auditItems.value = (d?.items ?? []).map((a: any) => ({
      id: a.id,
      actor: a.actor,
      action: a.action,
      result: a.result,
    }))
  } catch {
    auditItems.value = []
  } finally {
    auditLoading.value = false
  }
}

const refresh = async () => {
  loading.value = true
  try {
    await Promise.all([loadMetrics(), loadEvents()])
    lastUpdated.value = new Date().toLocaleTimeString('zh-CN')
  } finally {
    loading.value = false
  }
}

const scoreColor = (score: number) => {
  if (score >= 80) return 'bg-red-500/20 text-red-400 border-red-500/30'
  if (score >= 60) return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-muted text-muted-foreground'
}

onMounted(async () => {
  polling.value = true
  await Promise.all([refresh(), loadAudit()])
  pollTimer = setInterval(refresh, INTERVAL * 1000)
})

onUnmounted(() => {
  polling.value = false
  if (pollTimer) clearInterval(pollTimer)
})
</script>
