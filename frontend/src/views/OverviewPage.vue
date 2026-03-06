<template>
  <div class="px-4 py-5 md:px-6">
    <div class="ops-shell mx-auto max-w-[1480px] space-y-6">
      <section class="ops-hero">
        <div class="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <div class="space-y-5">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="space-y-3">
                <span class="ops-eyebrow">Defense Command Deck</span>
                <div class="space-y-2">
                  <h1 class="ops-hero-title">防御坚守仪表盘</h1>
                  <p class="ops-hero-subtitle">{{ postureSummary.subtitle }}</p>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <select v-model="range" class="ops-select" @change="loadAll">
                  <option value="24h">24 小时</option>
                  <option value="7d">7 天</option>
                  <option value="30d">30 天</option>
                </select>
                <Button variant="outline" size="sm" class="cursor-pointer gap-1.5 rounded-full px-4" :disabled="loading" @click="loadAll">
                  <RefreshCw class="size-3.5" :class="loading ? 'animate-spin' : ''" />
                  刷新
                </Button>
              </div>
            </div>

            <ModuleFeedbackCard
              v-if="overviewIssues.length"
              title="部分模块同步失败"
              description="当前页面已经保留可用模块，其余区块可单独重试或展开日志排查接口失败原因。"
              :error="`异常模块：${overviewIssues.map(item => item.label).join('、')}`"
              :logs="overviewIssues.flatMap(item => item.logs)"
              @retry="loadAll"
            />

            <div class="grid gap-4 lg:grid-cols-[1.1fr_0.9fr]">
              <div class="ops-panel">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div class="space-y-2">
                    <p class="ops-section-copy uppercase tracking-[0.2em]">{{ postureSummary.eyebrow }}</p>
                    <h2 class="text-3xl font-semibold tracking-tight text-foreground">{{ postureSummary.title }}</h2>
                    <p class="max-w-3xl text-sm leading-7 text-muted-foreground">{{ postureSummary.body }}</p>
                  </div>
                  <Badge variant="outline" :class="postureSummary.badgeClass" class="rounded-full px-3 py-1 text-xs">
                    {{ postureSummary.badge }}
                  </Badge>
                </div>
                <div class="mt-5 grid gap-3 md:grid-cols-3">
                  <div v-for="item in heroHighlights" :key="item.label" class="ops-highlight-tile">
                    <p class="ops-highlight-label">{{ item.label }}</p>
                    <p class="ops-highlight-value" :class="item.valueClass">{{ item.value }}</p>
                    <p class="ops-highlight-note">{{ item.note }}</p>
                  </div>
                </div>
              </div>

              <div class="ops-panel flex h-full flex-col justify-between gap-5">
                <div class="space-y-2">
                  <p class="ops-section-title">值班建议</p>
                  <p class="ops-section-copy">先看队列压力，再看链路可信度，最后决定是否需要跨模块联动。</p>
                </div>
                <div class="ops-note-list">
                  <div v-for="(item, index) in priorityActions" :key="item" class="ops-note-item">
                    <span class="ops-note-index">{{ index + 1 }}</span>
                    <p class="text-sm leading-6 text-foreground/90">{{ item }}</p>
                  </div>
                </div>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="ops-highlight-tile">
                    <p class="ops-highlight-label">链路可用节点</p>
                    <p class="ops-highlight-value text-emerald-300">{{ chainOverview.healthy }}</p>
                    <p class="ops-highlight-note">共 {{ chainOverview.total }} 个节点，{{ chainOverview.summary }}</p>
                  </div>
                  <div class="ops-highlight-tile">
                    <p class="ops-highlight-label">跨域暴露面</p>
                    <p class="ops-highlight-value" :class="probeMetrics && probeMetrics.high_findings > 0 ? 'text-amber-300' : 'text-cyan-300'">
                      {{ probeMetrics?.high_findings ?? '--' }}
                    </p>
                    <p class="ops-highlight-note">高危发现需要和防御审批一起排优先级。</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <div class="ops-panel space-y-3">
              <div>
                <p class="ops-section-title">风险热区</p>
                <p class="ops-section-copy">把压力点转成一句话，不再让值班人员自己拼上下文。</p>
              </div>
              <div class="space-y-3">
                <div v-for="item in riskFocus" :key="item.label" class="ops-status-row">
                  <div class="min-w-0 space-y-1">
                    <div class="flex items-center gap-2">
                      <span class="ops-status-dot" :class="item.dotClass"></span>
                      <p class="text-sm font-medium text-foreground">{{ item.label }}</p>
                    </div>
                    <p class="text-xs leading-6 text-muted-foreground">{{ item.note }}</p>
                  </div>
                  <span class="text-sm font-semibold tabular-nums" :class="item.valueClass">{{ item.value }}</span>
                </div>
              </div>
            </div>

            <Card v-if="showDemoHint" class="ops-section-card border-dashed border-amber-500/30 bg-amber-500/5">
              <CardContent class="space-y-2 py-5">
                <p class="text-sm font-medium text-foreground">当前环境没有业务样本</p>
                <p class="text-xs leading-6 text-muted-foreground">
                  运行 <code class="ops-inline-code">python backend/seed_demo_data.py</code>
                  可以一键导入防御、探测、AI、审计演示数据，首屏会立即出现真实态势结构。
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section class="grid gap-4 lg:grid-cols-2 2xl:grid-cols-4">
        <ModuleFeedbackCard
          v-if="overviewFeedback.metrics.error"
          class="lg:col-span-2 2xl:col-span-4"
          title="关键指标暂时不可用"
          description="核心 KPI 没有完成同步，当前不展示旧指标，避免把值班判断建立在过期数据上。"
          :error="overviewFeedback.metrics.error"
          :logs="overviewFeedback.metrics.logs"
          @retry="loadAll"
        />
        <Card v-for="card in narrativeCards" v-else :key="card.label" class="ops-metric-card">
          <div class="ops-metric-top">
            <div>
              <p class="ops-metric-label">{{ card.label }}</p>
            </div>
            <span class="ops-metric-pill" :class="card.badgeClass">{{ card.badge }}</span>
          </div>
          <p class="ops-metric-value" :class="card.valueClass">{{ card.value }}</p>
          <div class="ops-metric-stack">
            <div class="ops-metric-line">
              <p class="ops-metric-caption">对比 / 趋势</p>
              <p class="ops-metric-copy">{{ card.compare }}</p>
            </div>
            <div class="ops-metric-line">
              <p class="ops-metric-caption">风险解释</p>
              <p class="ops-metric-copy">{{ card.explain }}</p>
            </div>
            <div class="ops-metric-line">
              <p class="ops-metric-caption">下一步建议</p>
              <p class="ops-metric-copy">{{ card.next }}</p>
            </div>
          </div>
        </Card>
      </section>

      <section class="grid gap-4 xl:grid-cols-[1.12fr_0.88fr]">
        <Card class="ops-section-card">
          <CardHeader class="space-y-3 pb-0">
            <div class="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
              <div class="space-y-1">
                <CardTitle class="ops-section-title">趋势洞察</CardTitle>
                <p class="ops-section-copy">把告警走势拆成最新周期、高危压力和阻断效率三条判断线。</p>
              </div>
              <Badge variant="outline" class="rounded-full border-border/70 bg-background/50 px-3 py-1 text-xs text-muted-foreground">
                {{ rangeLabel }}
              </Badge>
            </div>
            <div class="grid gap-3 md:grid-cols-3">
              <div v-for="item in trendHighlights" :key="item.label" class="ops-highlight-tile">
                <p class="ops-highlight-label">{{ item.label }}</p>
                <p class="ops-highlight-value" :class="item.valueClass">{{ item.value }}</p>
                <p class="ops-highlight-note">{{ item.note }}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent class="pt-5">
            <div v-if="loading" class="ops-empty">
              <Skeleton class="h-44 w-full rounded-xl" />
            </div>
            <ModuleFeedbackCard
              v-else-if="overviewFeedback.trends.error"
              title="趋势模块同步失败"
              description="趋势数据没有返回，暂时无法判断当前压力是在抬升还是回落。"
              :error="overviewFeedback.trends.error"
              :logs="overviewFeedback.trends.logs"
              @retry="loadAll"
            />
            <div v-else-if="!trends.alert_trend.length" class="ops-empty">
              <p class="ops-empty-title">暂无走势数据</p>
              <p class="ops-empty-copy">等到有告警进入系统后，这里会显示整体压力变化和高危告警的同步走势。</p>
            </div>
            <div v-else class="h-[19rem]">
              <Line :data="alertTrendChartData" :options="lineChartOptions" />
            </div>
          </CardContent>
        </Card>

        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">待处置任务</CardTitle>
            <p class="ops-section-copy">高危审批、人工介入和跨模块高危发现合并在一个工作面里看。</p>
          </CardHeader>
          <CardContent class="space-y-5 pt-5">
            <ModuleFeedbackCard
              v-if="overviewFeedback.todos.error"
              title="待处置队列同步失败"
              description="审批队列和人工介入列表没有成功返回，先不要据此判断当前待办压力。"
              :error="overviewFeedback.todos.error"
              :logs="overviewFeedback.todos.logs"
              @retry="loadAll"
            />
            <template v-else>
            <div>
              <div class="mb-3 flex items-center justify-between">
                <p class="text-sm font-medium text-foreground">待审批事件</p>
                <span class="text-xs text-muted-foreground">{{ todos?.counts.pending_events ?? 0 }} 条</span>
              </div>
              <div v-if="loading" class="space-y-2">
                <Skeleton v-for="i in 3" :key="i" class="h-18 w-full rounded-xl" />
              </div>
              <div v-else-if="!todos?.pending_events.length" class="ops-empty min-h-[9rem]">
                <p class="ops-empty-title">审批队列为空</p>
                <p class="ops-empty-copy">当前没有待审批防御事件，可以把注意力转到策略复盘和异常链路巡检。</p>
              </div>
              <div v-else class="ops-list">
                <div v-for="ev in todos.pending_events.slice(0, 4)" :key="ev.id" class="ops-list-item">
                  <div class="min-w-0 space-y-2">
                    <div class="flex flex-wrap items-center gap-2">
                      <code class="ops-inline-code">{{ ev.ip }}</code>
                      <span class="rounded-full border border-border/70 px-2 py-0.5 text-[11px] text-muted-foreground">{{ ev.source }}</span>
                    </div>
                    <p class="text-xs leading-6 text-muted-foreground">{{ eventSummary(ev) }}</p>
                    <p class="text-xs text-foreground/85">{{ eventAction(ev) }}</p>
                  </div>
                  <Badge :class="scoreColor(ev.ai_score)" class="shrink-0 rounded-full px-2.5 py-1 text-xs">
                    {{ ev.ai_score ?? '--' }}
                  </Badge>
                </div>
              </div>
            </div>

            <div>
              <div class="mb-3 flex items-center justify-between">
                <p class="text-sm font-medium text-foreground">人工介入</p>
                <span class="text-xs text-muted-foreground">{{ todos?.counts.manual_required ?? 0 }} 条</span>
              </div>
              <div v-if="todos?.failed_tasks.length" class="ops-list">
                <div v-for="task in todos.failed_tasks.slice(0, 3)" :key="task.id" class="ops-list-item">
                  <div class="min-w-0 space-y-1.5">
                    <div class="flex flex-wrap items-center gap-2">
                      <span class="text-sm font-medium text-foreground">执行任务 #{{ task.event_id }}</span>
                      <Badge variant="outline" class="rounded-full border-destructive/30 bg-destructive/8 text-[11px] text-destructive">
                        {{ task.state }}
                      </Badge>
                    </div>
                    <p class="text-xs leading-6 text-muted-foreground">{{ task.error_message || '执行链路返回失败，需要人工确认原因。' }}</p>
                    <p class="text-xs text-foreground/85">建议先核对动作参数和目标系统状态，再决定是否重试。</p>
                  </div>
                  <span class="text-xs tabular-nums text-muted-foreground">重试 {{ task.retry_count }}</span>
                </div>
              </div>
              <div v-else class="ops-empty min-h-[8rem]">
                <p class="ops-empty-title">没有人工介入项</p>
                <p class="ops-empty-copy">执行器没有积压失败任务，当前链路更适合做回顾和调优。</p>
              </div>
            </div>
            </template>
          </CardContent>
        </Card>
      </section>

      <section class="grid gap-4 xl:grid-cols-[0.82fr_1.18fr]">
        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">风险组成</CardTitle>
            <p class="ops-section-copy">按威胁等级拆开看，帮助判断当前是广泛噪声还是少量高压事件。</p>
          </CardHeader>
          <CardContent class="grid gap-5 pt-5 lg:grid-cols-[0.86fr_1fr] lg:items-center">
            <div v-if="loading" class="ops-empty min-h-[14rem]">
              <Skeleton class="size-40 rounded-full" />
            </div>
            <ModuleFeedbackCard
              v-else-if="overviewFeedback.defenseStats.error"
              title="风险组成同步失败"
              description="威胁等级分布没有成功返回，当前无法判断是高压风险还是噪声堆积。"
              :error="overviewFeedback.defenseStats.error"
              :logs="overviewFeedback.defenseStats.logs"
              @retry="loadAll"
            />
            <div v-else-if="!defenseStats?.threat_level_dist?.length" class="ops-empty min-h-[14rem]">
              <p class="ops-empty-title">还没有风险组成数据</p>
              <p class="ops-empty-copy">当事件进入聚合后，这里会展示高危与中低危的分布关系。</p>
            </div>
            <template v-else>
              <div class="mx-auto h-56 w-56 max-w-full">
                <Doughnut :data="threatPieChartData" :options="doughnutOptions" />
              </div>
              <div class="space-y-3">
                <div v-for="item in threatBreakdown" :key="item.level" class="ops-status-row">
                  <div class="min-w-0 space-y-1">
                    <div class="flex items-center gap-2">
                      <span class="ops-status-dot" :style="{ background: levelPieColor(item.level) }"></span>
                      <p class="text-sm font-medium text-foreground">{{ item.level }}</p>
                    </div>
                    <p class="text-xs leading-6 text-muted-foreground">{{ item.note }}</p>
                  </div>
                  <div class="text-right">
                    <p class="text-sm font-semibold tabular-nums text-foreground">{{ item.count }}</p>
                    <p class="text-xs text-muted-foreground">{{ item.pct }}%</p>
                  </div>
                </div>
              </div>
            </template>
          </CardContent>
        </Card>

        <Card class="ops-section-card">
          <CardHeader class="space-y-3 pb-0">
            <div class="space-y-1">
              <CardTitle class="ops-section-title">服务暴露热区</CardTitle>
              <p class="ops-section-copy">看当前被攻击最多的服务，再决定防护策略和暴露面梳理优先级。</p>
            </div>
            <div class="grid gap-3 md:grid-cols-3">
              <div v-for="item in serviceInsights" :key="item.label" class="ops-highlight-tile">
                <p class="ops-highlight-label">{{ item.label }}</p>
                <p class="ops-highlight-value" :class="item.valueClass">{{ item.value }}</p>
                <p class="ops-highlight-note">{{ item.note }}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent class="pt-5">
            <div v-if="loading" class="ops-empty">
              <Skeleton class="h-56 w-full rounded-xl" />
            </div>
            <ModuleFeedbackCard
              v-else-if="overviewFeedback.defenseStats.error"
              title="服务热区同步失败"
              description="服务命中排行没有返回，当前不建议根据缺失数据调整暴露策略。"
              :error="overviewFeedback.defenseStats.error"
              :logs="overviewFeedback.defenseStats.logs"
              @retry="loadAll"
            />
            <div v-else-if="!defenseStats?.service_dist?.length" class="ops-empty">
              <p class="ops-empty-title">暂无服务暴露数据</p>
              <p class="ops-empty-copy">等到攻击命中服务栈之后，这里会显示热点服务排行和攻击次数。</p>
            </div>
            <div v-else class="h-[19rem]">
              <Bar :data="serviceBarChartData" :options="barChartOptions" />
            </div>
          </CardContent>
        </Card>
      </section>

      <section class="grid gap-4 xl:grid-cols-[0.84fr_1.16fr]">
        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">链路可信度</CardTitle>
            <p class="ops-section-copy">用真实指标回看数据入口、审批执行和探测联动是否都在健康线内。</p>
          </CardHeader>
          <CardContent class="space-y-4 pt-5">
            <ModuleFeedbackCard
              v-if="overviewFeedback.chain.error"
              title="链路状态同步失败"
              description="链路健康指标没有返回，先不要据此判断是否可以继续放行或扩展自动化。"
              :error="overviewFeedback.chain.error"
              :logs="overviewFeedback.chain.logs"
              @retry="loadAll"
            />
            <template v-else>
            <div class="grid gap-3 md:grid-cols-2">
              <div class="ops-highlight-tile">
                <p class="ops-highlight-label">健康节点</p>
                <p class="ops-highlight-value text-emerald-300">{{ chainOverview.healthy }}</p>
                <p class="ops-highlight-note">{{ chainOverview.total }} 个节点中，{{ chainOverview.unhealthy }} 个需要关注。</p>
              </div>
              <div class="ops-highlight-tile">
                <p class="ops-highlight-label">值班判断</p>
                <p class="ops-highlight-value" :class="chainOverview.unhealthy > 0 ? 'text-amber-300' : 'text-cyan-300'">
                  {{ chainOverview.unhealthy > 0 ? '需要排查' : '可继续放行' }}
                </p>
                <p class="ops-highlight-note">{{ chainOverview.summary }}</p>
              </div>
            </div>
            <div class="ops-status-list">
              <div v-for="item in chainStatus" :key="item.key" class="ops-status-row">
                <div class="flex min-w-0 items-start gap-3">
                  <span class="mt-1 ops-status-dot" :class="item.ok ? 'bg-emerald-400 shadow-[0_0_0_4px_rgba(52,211,153,0.12)]' : 'bg-amber-400 shadow-[0_0_0_4px_rgba(251,191,36,0.12)]'"></span>
                  <div class="min-w-0">
                    <p class="text-sm font-medium text-foreground">{{ item.name }}</p>
                    <p class="mt-1 text-xs leading-6 text-muted-foreground">{{ item.metric || '等待链路指标同步' }}</p>
                  </div>
                </div>
                <span :class="item.ok ? 'text-emerald-300' : 'text-amber-300'" class="text-sm font-medium">{{ item.note }}</span>
              </div>
            </div>
            </template>
          </CardContent>
        </Card>

        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">攻击来源画像</CardTitle>
            <p class="ops-section-copy">用来源 IP 与最高评分结合看，判断是否出现持续性攻击源。</p>
          </CardHeader>
          <CardContent class="pt-5">
            <div v-if="loading" class="ops-empty">
              <Skeleton class="h-56 w-full rounded-xl" />
            </div>
            <ModuleFeedbackCard
              v-else-if="overviewFeedback.defenseStats.error"
              title="来源画像同步失败"
              description="攻击来源画像没有成功返回，暂时无法判断是否存在持续攻击源。"
              :error="overviewFeedback.defenseStats.error"
              :logs="overviewFeedback.defenseStats.logs"
              @retry="loadAll"
            />
            <div v-else-if="!defenseStats?.top_ips?.length" class="ops-empty">
              <p class="ops-empty-title">暂无攻击来源画像</p>
              <p class="ops-empty-copy">当前还没有足够的来源样本，等到防御流量进入后这里会显示高频来源与风险评分。</p>
            </div>
            <div v-else class="ops-table">
              <table>
                <thead>
                  <tr>
                    <th>IP</th>
                    <th>命中次数</th>
                    <th>最高评分</th>
                    <th>判断</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="ip in defenseStats.top_ips" :key="ip.ip">
                    <td><code class="ops-inline-code">{{ ip.ip }}</code></td>
                    <td class="tabular-nums">{{ ip.count }}</td>
                    <td>
                      <Badge :class="scoreColor(ip.max_score)" class="rounded-full px-2.5 py-1 text-xs">
                        {{ ip.max_score ?? '--' }}
                      </Badge>
                    </td>
                    <td class="text-xs text-muted-foreground">{{ topIpAssessment(ip.count, ip.max_score) }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { RefreshCw } from 'lucide-vue-next'
import { Line, Bar, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'
import {
  overviewApi,
  type OverviewChainStatus,
  type OverviewMetrics,
  type OverviewTrends,
  type OverviewTodos,
  type DefenseStats,
  type PendingEventItem,
  type TrendRange,
} from '@/api/overview'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import ModuleFeedbackCard from '@/components/dashboard/ModuleFeedbackCard.vue'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler,
)

interface NarrativeCard {
  label: string
  badge: string
  badgeClass: string
  value: string
  valueClass: string
  compare: string
  explain: string
  next: string
}

type OverviewModuleKey = 'metrics' | 'trends' | 'todos' | 'defenseStats' | 'chain'

interface ModuleFeedback {
  error: string | null
  logs: string[]
}

const createFeedbackState = (): ModuleFeedback => ({ error: null, logs: [] })

const loading = ref(false)
const range = ref<TrendRange>('7d')

const metrics = ref<OverviewMetrics | null>(null)
const trends = ref<OverviewTrends>({ range: '7d', alert_trend: [], high_alert_trend: [], task_trend: [] })
const todos = ref<OverviewTodos | null>(null)
const defenseStats = ref<DefenseStats | null>(null)
const chainStatusData = ref<OverviewChainStatus | null>(null)
const overviewFeedback = reactive<Record<OverviewModuleKey, ModuleFeedback>>({
  metrics: createFeedbackState(),
  trends: createFeedbackState(),
  todos: createFeedbackState(),
  defenseStats: createFeedbackState(),
  chain: createFeedbackState(),
})

const overviewModuleLabels: Record<OverviewModuleKey, string> = {
  metrics: '关键指标',
  trends: '趋势洞察',
  todos: '待处置任务',
  defenseStats: '风险统计',
  chain: '链路状态',
}

const resetOverviewFeedback = () => {
  ;(Object.keys(overviewFeedback) as OverviewModuleKey[]).forEach((key) => {
    overviewFeedback[key].error = null
    overviewFeedback[key].logs = []
  })
}

const normalizeError = (error: unknown) => {
  if (error instanceof Error) return error.message
  if (typeof error === 'string') return error
  try {
    return JSON.stringify(error)
  } catch {
    return '未知错误'
  }
}

const setOverviewFeedback = (key: OverviewModuleKey, error: unknown) => {
  const message = normalizeError(error)
  overviewFeedback[key].error = message
  overviewFeedback[key].logs = [
    `${new Date().toLocaleString('zh-CN')} ${overviewModuleLabels[key]}同步失败`,
    message,
  ]
  console.error(`Overview ${key} load failed:`, error)
}

const defenseMetrics = computed(() => metrics.value?.defense ?? null)
const probeMetrics = computed(() => metrics.value?.probe ?? null)
const chainStatus = computed(() => chainStatusData.value?.defense ?? [])

const rangeLabelMap: Record<TrendRange, string> = {
  '24h': '最近 24 小时',
  '7d': '最近 7 天',
  '30d': '最近 30 天',
}

const rangeLabel = computed(() => rangeLabelMap[range.value])
const overviewIssues = computed(() =>
  (Object.keys(overviewFeedback) as OverviewModuleKey[])
    .filter(key => overviewFeedback[key].error)
    .map(key => ({
      key,
      label: overviewModuleLabels[key],
      error: overviewFeedback[key].error,
      logs: overviewFeedback[key].logs,
    })),
)

const postureSummary = computed(() => {
  const d = defenseMetrics.value
  const p = probeMetrics.value
  if (!d || !p) {
    return {
      eyebrow: 'Current Posture',
      title: '正在同步值班态势',
      subtitle: '等待防御、探测和链路指标完成同步。',
      body: '数据还没有完全返回，首屏会在同步完成后自动收敛成当前风险判断和处理建议。',
      badge: 'Syncing',
      badgeClass: 'border-border/70 bg-background/60 text-muted-foreground',
    }
  }

  const pressure = d.pending_events + d.high_risk_pending + d.manual_required + p.high_findings
  if (d.high_risk_pending > 0 || p.high_findings > 0) {
    return {
      eyebrow: 'High Pressure',
      title: '当前存在高压风险堆积',
      subtitle: '首屏优先聚焦高危审批、人工介入和高危发现，不再把注意力耗散在平均视图里。',
      body: `待审批 ${d.pending_events} 条，其中高危 ${d.high_risk_pending} 条；探测侧还有 ${p.high_findings} 个高危发现待协同处置。`,
      badge: 'Priority Review',
      badgeClass: 'border-red-500/30 bg-red-500/10 text-red-300',
    }
  }

  if (pressure > 0) {
    return {
      eyebrow: 'Watch Mode',
      title: '链路总体可控，但仍有处理中队列',
      subtitle: '主要压力集中在常规审批和执行跟进，适合按值班节奏逐步消化。',
      body: `当前共有 ${pressure} 个需要跟进的点位，阻断成功率 ${d.block_success_rate}% ，没有形成明显高危挤压。`,
      badge: 'Monitor',
      badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    }
  }

  return {
    eyebrow: 'Stable Window',
    title: '当前没有明显堆积项',
    subtitle: '审批、执行和探测都处在低压窗口，适合做策略复盘而不是救火。',
    body: '待审批、人工介入和高危发现都处于低位，可以把当前窗口用来梳理服务暴露面和阻断策略命中率。',
    badge: 'Steady',
    badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  }
})

const heroHighlights = computed(() => {
  const d = defenseMetrics.value
  if (!d) {
    return [
      { label: '今日告警', value: '--', note: '等待告警流量回流。', valueClass: 'text-foreground' },
      { label: '待审批', value: '--', note: '等待审批队列同步。', valueClass: 'text-foreground' },
      { label: '今日阻断', value: '--', note: '等待执行结果同步。', valueClass: 'text-foreground' },
    ]
  }

  return [
    {
      label: '今日告警',
      value: String(d.today_alerts),
      note: d.today_alerts > 0 ? `${rangeLabel.value} 内保持输入压力监控。` : '当前没有新增告警压力。',
      valueClass: d.today_alerts > 0 ? 'text-foreground' : 'text-cyan-300',
    },
    {
      label: '待审批',
      value: String(d.pending_events),
      note: d.pending_events > 0 ? `高危 ${d.high_risk_pending} 条，人工介入 ${d.manual_required} 条。` : '审批队列已经清空。',
      valueClass: d.high_risk_pending > 0 ? 'text-amber-300' : 'text-foreground',
    },
    {
      label: '今日阻断',
      value: String(d.today_blocked),
      note: `阻断成功率 ${d.block_success_rate}% ，低于 95% 就需要复盘规则。`,
      valueClass: d.block_success_rate >= 95 ? 'text-emerald-300' : 'text-amber-300',
    },
  ]
})

const chainOverview = computed(() => {
  const total = chainStatus.value.length
  const healthy = chainStatus.value.filter(item => item.ok).length
  const unhealthy = total - healthy
  return {
    total,
    healthy,
    unhealthy,
    summary: unhealthy > 0 ? `${unhealthy} 个节点未达到健康线，建议先排查链路。` : '当前所有防御链路节点都在健康线内。',
  }
})

const priorityActions = computed(() => {
  const d = defenseMetrics.value
  const p = probeMetrics.value
  const actions: string[] = []

  if (!d || !p) {
    return ['等待指标同步完成后，再决定是否进入处置节奏。']
  }

  if (d.high_risk_pending > 0) {
    actions.push(`先处理 ${d.high_risk_pending} 条高危待审批事件，避免真正需要阻断的动作继续排队。`)
  }
  if (d.manual_required > 0) {
    actions.push(`检查 ${d.manual_required} 条人工介入任务，优先确认失败原因和是否具备重试条件。`)
  }
  if (p.high_findings > 0) {
    actions.push(`把探测侧 ${p.high_findings} 个高危发现和防御审批一起排优先级，避免只看单侧数据。`)
  }
  if (chainOverview.value.unhealthy > 0) {
    actions.push(`链路有 ${chainOverview.value.unhealthy} 个节点不健康，先排查数据入口和执行器状态，再做激进处置。`)
  }
  if (!actions.length) {
    actions.push('当前没有明显堆积项，建议转入策略复盘、规则命中率分析和服务暴露面巡检。')
  }

  return actions.slice(0, 3)
})

const riskFocus = computed(() => {
  const d = defenseMetrics.value
  const p = probeMetrics.value
  return [
    {
      label: '高危待审批',
      value: d ? String(d.high_risk_pending) : '--',
      note: d && d.high_risk_pending > 0 ? '这部分最容易造成处置滞后，需要优先清空。' : '当前没有高危审批堆积。',
      dotClass: d && d.high_risk_pending > 0 ? 'bg-red-400' : 'bg-emerald-400',
      valueClass: d && d.high_risk_pending > 0 ? 'text-red-300' : 'text-emerald-300',
    },
    {
      label: '人工介入任务',
      value: d ? String(d.manual_required) : '--',
      note: d && d.manual_required > 0 ? '说明自动处置链路有失败点，需要值班人员接管。' : '执行链路没有失败积压。',
      dotClass: d && d.manual_required > 0 ? 'bg-amber-400' : 'bg-cyan-400',
      valueClass: d && d.manual_required > 0 ? 'text-amber-300' : 'text-cyan-300',
    },
    {
      label: '高危发现联动',
      value: p ? String(p.high_findings) : '--',
      note: p && p.high_findings > 0 ? '探测暴露面已经抬头，防御策略需要同步关注。' : '探测侧没有新增高危压力。',
      dotClass: p && p.high_findings > 0 ? 'bg-red-400' : 'bg-emerald-400',
      valueClass: p && p.high_findings > 0 ? 'text-red-300' : 'text-emerald-300',
    },
  ]
})

const narrativeCards = computed<NarrativeCard[]>(() => {
  const d = defenseMetrics.value
  const p = probeMetrics.value
  const pendingEvents = d?.pending_events ?? 0
  const highRiskPending = d?.high_risk_pending ?? 0
  const manualRequired = d?.manual_required ?? 0
  const blockRate = d?.block_success_rate ?? 0
  const assets = p?.total_assets ?? 0
  const enabledAssets = p?.enabled_assets ?? 0
  const highFindings = p?.high_findings ?? 0
  const mediumFindings = p?.medium_findings ?? 0
  const todayTasks = p?.today_tasks ?? 0
  const coverage = assets > 0 ? Math.round((enabledAssets / assets) * 100) : 0

  return [
    {
      label: '待审批压力',
      badge: highRiskPending > 0 ? 'High' : pendingEvents > 0 ? 'Watch' : 'Stable',
      badgeClass: highRiskPending > 0 ? 'border-red-500/30 bg-red-500/10 text-red-300' : pendingEvents > 0 ? 'border-amber-500/30 bg-amber-500/10 text-amber-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
      value: `${pendingEvents}`,
      valueClass: highRiskPending > 0 ? 'text-red-300' : pendingEvents > 0 ? 'text-amber-300' : 'text-cyan-300',
      compare: `高危 ${highRiskPending} 条，人工介入 ${manualRequired} 条。`,
      explain: pendingEvents > 0 ? '审批队列仍在消耗值班带宽，高危审批越多，真正阻断动作越可能被延后。' : '审批队列为空，当前没有明显的人工决策积压。',
      next: pendingEvents > 0 ? '优先清空高危审批，再处理普通待办，避免队列继续拉长。' : '把窗口时间用于复盘误报和阻断策略质量。',
    },
    {
      label: '阻断有效率',
      badge: blockRate >= 95 ? 'On Target' : 'Below Line',
      badgeClass: blockRate >= 95 ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300',
      value: `${blockRate}%`,
      valueClass: blockRate >= 95 ? 'text-emerald-300' : 'text-amber-300',
      compare: `目标线 >= 95%，今日阻断 ${d?.today_blocked ?? 0} 次。`,
      explain: blockRate >= 95 ? '当前自动处置闭环处在健康区间，可以继续放大自动化覆盖面。' : '阻断成功率低于目标线，说明规则、执行器或目标环境存在摩擦。',
      next: blockRate >= 95 ? '挑选高频命中规则继续扩容自动化范围。' : '回看失败样本，定位是规则误判还是执行器动作失败。',
    },
    {
      label: '资产覆盖',
      badge: coverage >= 85 ? 'Covered' : 'Gap',
      badgeClass: coverage >= 85 ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300',
      value: `${coverage}%`,
      valueClass: coverage >= 85 ? 'text-cyan-300' : 'text-amber-300',
      compare: `已启用 ${enabledAssets} / 总资产 ${assets}。`,
      explain: assets > 0 ? '资产覆盖率越低，探测侧越容易漏掉真实暴露面，防御判断也会失真。' : '当前还没有资产样本，任何风险结论都缺少暴露面上下文。',
      next: assets > 0 ? '把未启用资产纳入探测计划，优先补齐高价值目标。' : '先导入演示或真实资产，再判断扫描策略是否合理。',
    },
    {
      label: '高危暴露面',
      badge: highFindings > 0 ? 'Escalate' : 'Quiet',
      badgeClass: highFindings > 0 ? 'border-red-500/30 bg-red-500/10 text-red-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
      value: `${highFindings}`,
      valueClass: highFindings > 0 ? 'text-red-300' : 'text-emerald-300',
      compare: `中危 ${mediumFindings} 个，今日扫描 ${todayTasks} 次。`,
      explain: highFindings > 0 ? '探测侧高危发现会直接提高防御策略调整优先级，不能被单独看待。' : '当前没有高危发现，防御与探测之间的联动压力较低。',
      next: highFindings > 0 ? '把高危发现映射到对应服务和防护规则，形成闭环处置。' : '继续维持基线扫描，关注是否出现新的高危抬头。',
    },
  ]
})

const trendHighlights = computed(() => {
  const alertTrend = trends.value.alert_trend
  const highTrend = trends.value.high_alert_trend
  const latest = alertTrend.at(-1)?.count ?? 0
  const previous = alertTrend.at(-2)?.count ?? latest
  const delta = latest - previous
  const highLatest = highTrend.at(-1)?.count ?? 0
  const average = alertTrend.length ? Math.round(alertTrend.reduce((sum, item) => sum + item.count, 0) / alertTrend.length) : 0
  const blockRate = defenseMetrics.value?.block_success_rate ?? 0

  return [
    {
      label: '最新周期告警',
      value: String(latest),
      note: delta === 0 ? '与上一周期持平。' : delta > 0 ? `较上一周期上升 ${delta} 条。` : `较上一周期下降 ${Math.abs(delta)} 条。`,
      valueClass: delta > 0 ? 'text-amber-300' : 'text-cyan-300',
    },
    {
      label: '高危告警',
      value: String(highLatest),
      note: highLatest > 0 ? '高危输入仍在持续，需要值班保持盯防。' : '最近周期没有高危告警抬头。',
      valueClass: highLatest > 0 ? 'text-red-300' : 'text-emerald-300',
    },
    {
      label: '基线效率',
      value: `${blockRate}%`,
      note: `平均告警 ${average} 条，当前阻断效率 ${blockRate >= 95 ? '达到' : '低于'}目标线。`,
      valueClass: blockRate >= 95 ? 'text-emerald-300' : 'text-amber-300',
    },
  ]
})

const threatBreakdown = computed(() => {
  const dist = defenseStats.value?.threat_level_dist ?? []
  const total = dist.reduce((sum, item) => sum + item.count, 0) || 1
  return dist.map(item => ({
    ...item,
    pct: Math.round((item.count / total) * 100),
    note: item.level === 'CRITICAL'
      ? '这部分代表最需要立即确认的风险。'
      : item.level === 'HIGH'
        ? '高危事件通常会直接进入审批优先级前列。'
        : item.level === 'MEDIUM'
          ? '中危更多用于观察趋势和配置质量。'
          : '低危和信息类更适合做噪声治理。',
  }))
})

const serviceInsights = computed(() => {
  const topService = defenseStats.value?.service_dist?.[0]
  const topIp = defenseStats.value?.top_ips?.[0]
  const total = defenseStats.value?.total ?? 0
  const highTotal = defenseStats.value?.high_total ?? 0
  const highPct = total > 0 ? Math.round((highTotal / total) * 100) : 0

  return [
    {
      label: '最高频服务',
      value: topService?.service || 'N/A',
      note: topService ? `最近命中 ${topService.count} 次，适合优先检查暴露策略。` : '等待服务命中样本。',
      valueClass: 'text-foreground',
    },
    {
      label: '高危占比',
      value: `${highPct}%`,
      note: highPct >= 30 ? '高危占比偏高，说明输入不是纯噪声。' : '高危占比可控，更适合做规则收敛。',
      valueClass: highPct >= 30 ? 'text-amber-300' : 'text-cyan-300',
    },
    {
      label: '重点来源',
      value: topIp?.ip || 'N/A',
      note: topIp ? `累计 ${topIp.count} 次命中，适合和封禁策略做交叉验证。` : '等待来源画像样本。',
      valueClass: topIp ? 'text-foreground' : 'text-muted-foreground',
    },
  ]
})

const showDemoHint = computed(() => {
  const d = defenseMetrics.value
  const p = probeMetrics.value
  if (!d || !p) return false
  if (overviewIssues.value.length) return false
  return (
    d.today_alerts === 0 &&
    d.pending_events === 0 &&
    d.today_blocked === 0 &&
    p.total_assets === 0 &&
    p.total_findings === 0 &&
    p.running_tasks === 0
  )
})

const CHART_COLORS = {
  primary: 'rgba(255, 157, 66, 1)',
  primaryAlpha: 'rgba(255, 157, 66, 0.16)',
  high: 'rgba(245, 104, 92, 0.9)',
  medium: 'rgba(255, 189, 91, 0.88)',
  low: 'rgba(73, 141, 255, 0.85)',
  critical: 'rgba(239, 68, 68, 0.95)',
  info: 'rgba(148, 163, 184, 0.75)',
}

const alertTrendChartData = computed(() => ({
  labels: trends.value.alert_trend.map(point => point.date),
  datasets: [
    {
      label: '告警总量',
      data: trends.value.alert_trend.map(point => point.count),
      borderColor: CHART_COLORS.primary,
      backgroundColor: CHART_COLORS.primaryAlpha,
      fill: true,
      tension: 0.38,
      pointRadius: 3,
      pointHoverRadius: 5,
    },
    ...(trends.value.high_alert_trend.length
      ? [{
          label: '高危告警',
          data: trends.value.high_alert_trend.map(point => point.count),
          borderColor: CHART_COLORS.high,
          backgroundColor: 'transparent',
          fill: false,
          tension: 0.38,
          pointRadius: 3,
          borderDash: [4, 4],
        }]
      : []),
  ],
}))

const levelPieColorMap: Record<string, string> = {
  CRITICAL: CHART_COLORS.critical,
  HIGH: CHART_COLORS.high,
  MEDIUM: CHART_COLORS.medium,
  LOW: CHART_COLORS.low,
}

const levelPieColor = (level: string) => levelPieColorMap[level] ?? CHART_COLORS.info

const threatPieChartData = computed(() => {
  const dist = defenseStats.value?.threat_level_dist ?? []
  return {
    labels: dist.map(item => item.level),
    datasets: [{
      data: dist.map(item => item.count),
      backgroundColor: dist.map(item => levelPieColor(item.level)),
      borderWidth: 0,
      hoverOffset: 6,
    }],
  }
})

const serviceBarChartData = computed(() => {
  const services = (defenseStats.value?.service_dist ?? []).slice(0, 8)
  return {
    labels: services.map(item => item.service),
    datasets: [{
      label: '命中次数',
      data: services.map(item => item.count),
      backgroundColor: 'rgba(255, 157, 66, 0.72)',
      borderColor: 'rgba(255, 157, 66, 1)',
      borderWidth: 1,
      borderRadius: 6,
    }],
  }
})

const baseChartFont = { family: 'IBM Plex Sans, Avenir Next, Segoe UI, sans-serif', size: 11 }
const gridColor = 'rgba(148, 163, 184, 0.14)'
const tickColor = 'rgba(203, 213, 225, 0.72)'

const lineChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      display: true,
      labels: { color: tickColor, font: baseChartFont, boxWidth: 10, padding: 14 },
    },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { grid: { color: gridColor }, ticks: { color: tickColor, font: baseChartFont, maxRotation: 0 } },
    y: { grid: { color: gridColor }, ticks: { color: tickColor, font: baseChartFont }, beginAtZero: true },
  },
}

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '67%',
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx: any) => ` ${ctx.label}: ${ctx.parsed}` } },
  },
}

const barChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  indexAxis: 'y' as const,
  plugins: {
    legend: { display: false },
    tooltip: { mode: 'index' as const, intersect: false },
  },
  scales: {
    x: { grid: { color: gridColor }, ticks: { color: tickColor, font: baseChartFont }, beginAtZero: true },
    y: { grid: { color: 'transparent' }, ticks: { color: tickColor, font: baseChartFont } },
  },
}

const scoreColor = (score: number | null | undefined) => {
  if (score == null) return 'border-border/70 bg-muted text-muted-foreground'
  if (score >= 80) return 'border-red-500/30 bg-red-500/12 text-red-300'
  if (score >= 40) return 'border-amber-500/30 bg-amber-500/12 text-amber-300'
  return 'border-cyan-500/30 bg-cyan-500/12 text-cyan-300'
}

const eventSummary = (event: PendingEventItem) => {
  const time = new Date(event.created_at).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  return `${time} 进入审批队列，${event.ai_reason || '当前还没有 AI 风险解释。'}`
}

const eventAction = (event: PendingEventItem) => {
  if ((event.ai_score ?? 0) >= 80) return '建议立即复核并决定是否执行阻断动作。'
  if ((event.ai_score ?? 0) >= 40) return '建议结合来源和上下文再做审批，避免误处置。'
  return '建议作为观察样本保留，优先处理评分更高的事件。'
}

const topIpAssessment = (count: number, score: number | null) => {
  if ((score ?? 0) >= 80) return `高风险来源，${count} 次命中足以进入重点封禁复盘。`
  if (count >= 3) return '持续命中来源，适合和规则命中率一起复盘。'
  return '当前更像零散样本，继续观察是否形成持续来源。'
}

const loadAll = async () => {
  loading.value = true
  resetOverviewFeedback()
  try {
    const [metricsSnapshot, trendSnapshot, todoSnapshot, defenseSnapshot, chainSnapshot] = await Promise.allSettled([
      overviewApi.getMetrics(),
      overviewApi.getTrends(range.value),
      overviewApi.getTodos(),
      overviewApi.getDefenseStats(range.value),
      overviewApi.getChainStatus(),
    ])

    if (metricsSnapshot.status === 'fulfilled') {
      metrics.value = metricsSnapshot.value
    } else {
      metrics.value = null
      setOverviewFeedback('metrics', metricsSnapshot.reason)
    }

    if (trendSnapshot.status === 'fulfilled') {
      trends.value = trendSnapshot.value ?? { range: range.value, alert_trend: [], high_alert_trend: [], task_trend: [] }
    } else {
      trends.value = { range: range.value, alert_trend: [], high_alert_trend: [], task_trend: [] }
      setOverviewFeedback('trends', trendSnapshot.reason)
    }

    if (todoSnapshot.status === 'fulfilled') {
      todos.value = todoSnapshot.value ?? {
        pending_events: [],
        failed_tasks: [],
        high_findings: [],
        counts: { pending_events: 0, manual_required: 0, high_findings_new: 0 },
      }
    } else {
      todos.value = {
        pending_events: [],
        failed_tasks: [],
        high_findings: [],
        counts: { pending_events: 0, manual_required: 0, high_findings_new: 0 },
      }
      setOverviewFeedback('todos', todoSnapshot.reason)
    }

    if (defenseSnapshot.status === 'fulfilled') {
      defenseStats.value = defenseSnapshot.value ?? { range: range.value, total: 0, high_total: 0, threat_level_dist: [], service_dist: [], top_ips: [] }
    } else {
      defenseStats.value = { range: range.value, total: 0, high_total: 0, threat_level_dist: [], service_dist: [], top_ips: [] }
      setOverviewFeedback('defenseStats', defenseSnapshot.reason)
    }

    if (chainSnapshot.status === 'fulfilled') {
      chainStatusData.value = chainSnapshot.value ?? { defense: [], probe: [], generated_at: new Date().toISOString() }
    } else {
      chainStatusData.value = { defense: [], probe: [], generated_at: new Date().toISOString() }
      setOverviewFeedback('chain', chainSnapshot.reason)
    }
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)
</script>
