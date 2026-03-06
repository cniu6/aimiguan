<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <!-- Header -->
      <div class="flex items-center justify-between">
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold">防御坚守仪表盘</h1>
          <p class="text-sm text-muted-foreground">防御处置链路与核心安全指标总览</p>
        </div>
        <div class="flex items-center gap-2">
          <!-- 时间范围选择 -->
          <select
            v-model="range"
            class="h-8 rounded-md border border-border bg-background px-2 text-sm text-foreground"
            @change="loadAll"
          >
            <option value="24h">24小时</option>
            <option value="7d">7天</option>
            <option value="30d">30天</option>
          </select>
          <Button variant="outline" size="sm" class="cursor-pointer gap-1.5" :disabled="loading" @click="loadAll">
            <RefreshCw class="size-3.5" :class="loading ? 'animate-spin' : ''" />
            刷新
          </Button>
        </div>
      </div>

      <!-- KPI 卡片 -->
      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <Card v-for="item in kpiCards" :key="item.label">
          <CardHeader class="pb-2 flex-row items-center justify-between space-y-0">
            <CardTitle class="text-sm font-medium text-muted-foreground">{{ item.label }}</CardTitle>
            <component :is="item.icon" class="size-4 text-muted-foreground/60" />
          </CardHeader>
          <CardContent>
            <p class="text-2xl font-semibold" :class="item.color">
              <span v-if="loading">—</span>
              <span v-else>{{ item.value }}</span>
            </p>
            <p v-if="item.sub" class="mt-1 text-xs text-muted-foreground">{{ item.sub }}</p>
          </CardContent>
        </Card>
      </div>

      <!-- 趋势图 + 待办 -->
      <div class="grid gap-4 lg:grid-cols-2">
        <!-- 告警趋势折线图 -->
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="text-base">告警趋势</CardTitle>
          </CardHeader>
          <CardContent>
            <div v-if="loading" class="h-40 flex items-center justify-center text-muted-foreground text-sm">加载中…</div>
            <div v-else-if="trends.alert_trend.length === 0" class="h-40 flex items-center justify-center text-muted-foreground text-sm">暂无数据</div>
            <div v-else class="space-y-1">
              <!-- 简易条形趋势 -->
              <div class="flex items-end gap-1 h-32">
                <div
                  v-for="pt in trends.alert_trend"
                  :key="pt.date"
                  class="flex-1 flex flex-col items-center gap-1"
                >
                  <div
                    class="w-full rounded-sm bg-primary/70 transition-all"
                    :style="{ height: barHeight(pt.count, maxAlertCount) + 'px' }"
                    :title="`${pt.date}: ${pt.count} 条`"
                  />
                </div>
              </div>
              <div class="flex justify-between text-[10px] text-muted-foreground">
                <span>{{ trends.alert_trend[0]?.date }}</span>
                <span>{{ trends.alert_trend[trends.alert_trend.length - 1]?.date }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- 待办事项 -->
        <Card>
          <CardHeader class="pb-3 flex-row items-center justify-between">
            <CardTitle class="text-base">高优待办</CardTitle>
            <div class="flex gap-2 text-xs">
              <span class="text-muted-foreground">待审批</span>
              <span class="font-semibold text-amber-400">{{ todos?.counts.pending_events ?? '—' }}</span>
            </div>
          </CardHeader>
          <CardContent class="space-y-2">
            <div v-if="loading" class="space-y-2">
              <Skeleton v-for="i in 3" :key="i" class="h-10 w-full rounded" />
            </div>
            <div v-else-if="!todos?.pending_events.length" class="py-6 text-center text-sm text-muted-foreground">
              暂无高优待办
            </div>
            <div
              v-for="ev in todos?.pending_events"
              :key="ev.id"
              class="flex items-center justify-between rounded-md border border-border px-3 py-2 text-sm"
            >
              <div class="flex items-center gap-2 min-w-0">
                <code class="text-xs font-mono">{{ ev.ip }}</code>
                <span class="truncate text-xs text-muted-foreground">{{ ev.source }}</span>
              </div>
              <Badge :class="scoreColor(ev.ai_score)" class="text-xs shrink-0">{{ ev.ai_score ?? '—' }}</Badge>
            </div>
            <!-- 失败任务 -->
            <template v-if="todos?.failed_tasks.length">
              <p class="pt-1 text-xs font-medium text-muted-foreground">需人工介入</p>
              <div
                v-for="t in todos.failed_tasks"
                :key="t.id"
                class="flex items-center justify-between rounded-md border border-destructive/30 px-3 py-2 text-sm"
              >
                <span class="text-xs">执行任务 #{{ t.event_id }}</span>
                <Badge variant="outline" class="text-xs text-destructive border-destructive/40">{{ t.state }}</Badge>
              </div>
            </template>
          </CardContent>
        </Card>
      </div>

      <!-- 威胁分布 + 链路状态 -->
      <div class="grid gap-4 lg:grid-cols-2">
        <!-- 威胁等级分布 -->
        <Card>
          <CardHeader class="pb-3 flex-row items-center justify-between">
            <CardTitle class="text-base">威胁等级分布</CardTitle>
            <span class="text-xs text-muted-foreground">{{ range }} 范围</span>
          </CardHeader>
          <CardContent class="space-y-2">
            <div v-if="loading" class="space-y-2">
              <Skeleton v-for="i in 4" :key="i" class="h-8 w-full rounded" />
            </div>
            <div v-else>
              <div
                v-for="item in defenseStats?.threat_level_dist"
                :key="item.level"
                class="flex items-center justify-between rounded-md border border-border px-3 py-2"
              >
                <div class="flex items-center gap-2">
                  <Badge :class="levelColor(item.level)" class="text-xs w-20 justify-center">{{ item.level }}</Badge>
                  <div class="h-2 w-28 overflow-hidden rounded-full bg-muted">
                    <div
                      :class="levelBarColor(item.level)"
                      class="h-full rounded-full transition-all"
                      :style="{ width: levelPct(item.count) + '%' }"
                    />
                  </div>
                </div>
                <span class="text-sm font-semibold tabular-nums">{{ item.count }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <!-- 链路健康状态 -->
        <Card>
          <CardHeader class="pb-3">
            <CardTitle class="text-base">链路健康状态</CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-sm">
            <div
              v-for="item in chainStatus"
              :key="item.name"
              class="flex items-center justify-between rounded-md border border-border px-3 py-2"
            >
              <span>{{ item.name }}</span>
              <span :class="item.ok ? 'text-emerald-500' : 'text-amber-500'">
                {{ item.ok ? '正常' : item.note }}
              </span>
            </div>
          </CardContent>
        </Card>
      </div>

      <!-- TOP 攻击 IP -->
      <Card v-if="!loading && defenseStats?.top_ips.length">
        <CardHeader class="pb-3 flex-row items-center gap-2">
          <AlertTriangle class="size-4 text-amber-400" />
          <CardTitle class="text-base">TOP 攻击来源 IP</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="rounded-lg border border-border overflow-hidden">
            <table class="w-full text-sm">
              <thead>
                <tr class="border-b border-border bg-muted/30">
                  <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground">IP</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground">攻击次数</th>
                  <th class="px-4 py-2 text-left text-xs font-medium text-muted-foreground">最高评分</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="ip in defenseStats.top_ips"
                  :key="ip.ip"
                  class="border-b border-border/50 hover:bg-muted/20"
                >
                  <td class="px-4 py-2 font-mono text-xs">{{ ip.ip }}</td>
                  <td class="px-4 py-2 text-xs">{{ ip.count }}</td>
                  <td class="px-4 py-2">
                    <Badge :class="scoreColor(ip.max_score)" class="text-xs">{{ ip.max_score ?? '—' }}</Badge>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { AlertTriangle, RefreshCw, Shield, ShieldAlert, Target, TrendingUp } from 'lucide-vue-next'
import { overviewApi, type OverviewMetrics, type OverviewTrends, type OverviewTodos, type DefenseStats, type TrendRange } from '@/api/overview'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'

const loading = ref(false)
const range = ref<TrendRange>('7d')

const metrics = ref<OverviewMetrics | null>(null)
const trends = ref<OverviewTrends>({ range: '7d', alert_trend: [], high_alert_trend: [], task_trend: [] })
const todos = ref<OverviewTodos | null>(null)
const defenseStats = ref<DefenseStats | null>(null)

const kpiCards = computed(() => {
  const d = metrics.value?.defense
  const p = metrics.value?.probe
  return [
    {
      label: '待审批事件',
      value: d?.pending_events ?? '—',
      sub: d ? `其中高危 ${d.high_risk_pending} 条` : '',
      icon: ShieldAlert,
      color: (d?.pending_events ?? 0) > 0 ? 'text-amber-400' : 'text-foreground',
    },
    {
      label: '今日封禁成功',
      value: d?.today_blocked ?? '—',
      sub: d ? `成功率 ${d.block_success_rate}%` : '',
      icon: Shield,
      color: 'text-emerald-400',
    },
    {
      label: '资产总数',
      value: p?.total_assets ?? '—',
      sub: p ? `已启用 ${p.enabled_assets} 个` : '',
      icon: Target,
      color: 'text-foreground',
    },
    {
      label: '高危漏洞发现',
      value: p?.high_findings ?? '—',
      sub: p ? `中危 ${p.medium_findings} 条` : '',
      icon: TrendingUp,
      color: (p?.high_findings ?? 0) > 0 ? 'text-red-400' : 'text-foreground',
    },
  ]
})

const maxAlertCount = computed(() =>
  Math.max(1, ...trends.value.alert_trend.map(p => p.count))
)

const totalLevelCount = computed(() =>
  Math.max(1, defenseStats.value?.threat_level_dist.reduce((s, i) => s + i.count, 0) ?? 1)
)

const chainStatus = computed(() => {
  const d = metrics.value?.defense
  const p = metrics.value?.probe
  return [
    { name: '告警接入（HFish）', ok: true, note: '' },
    { name: 'AI 评分引擎', ok: true, note: '' },
    { name: '审批与执行', ok: (d?.manual_required ?? 0) === 0, note: `${d?.manual_required} 条需人工` },
    { name: '探测扫描', ok: (p?.total_assets ?? 0) >= 0, note: '' },
  ]
})

const barHeight = (count: number, max: number) =>
  Math.max(4, Math.round((count / max) * 112))

const levelPct = (count: number) =>
  Math.round((count / totalLevelCount.value) * 100)

const levelColor = (level: string) => {
  const map: Record<string, string> = {
    CRITICAL: 'bg-red-500/15 text-red-400 border-red-500/30',
    HIGH: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
    MEDIUM: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
    LOW: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  }
  return map[level] ?? 'bg-muted text-muted-foreground'
}

const levelBarColor = (level: string) => {
  const map: Record<string, string> = {
    CRITICAL: 'bg-red-500',
    HIGH: 'bg-orange-500',
    MEDIUM: 'bg-yellow-400',
    LOW: 'bg-blue-500',
  }
  return map[level] ?? 'bg-muted-foreground'
}

const scoreColor = (score: number | null | undefined) => {
  if (score == null) return 'bg-muted text-muted-foreground'
  if (score >= 80) return 'bg-red-500/15 text-red-400 border-red-500/30'
  if (score >= 40) return 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30'
  return 'bg-blue-500/15 text-blue-400 border-blue-500/30'
}

const loadAll = async () => {
  loading.value = true
  try {
    const [m, tr, td, ds] = await Promise.all([
      overviewApi.getMetrics(),
      overviewApi.getTrends(range.value),
      overviewApi.getTodos(),
      overviewApi.getDefenseStats(range.value),
    ])
    metrics.value = m
    trends.value = tr
    todos.value = td
    defenseStats.value = ds
  } catch (e) {
    console.error('Overview load failed:', e)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>
