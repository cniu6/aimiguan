<template>
  <div class="px-4 py-5 md:px-6">
    <div class="ops-shell mx-auto max-w-[1480px] space-y-6">
      <section class="ops-hero">
        <div class="grid gap-5 xl:grid-cols-[1.35fr_0.65fr]">
          <div class="space-y-5">
            <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
              <div class="space-y-3">
                <span class="ops-eyebrow">Probe Exposure Deck</span>
                <div class="space-y-2">
                  <h1 class="ops-hero-title">主动探测仪表盘</h1>
                  <p class="ops-hero-subtitle">{{ probePosture.subtitle }}</p>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-2">
                <router-link to="/probe/scan">
                  <Button variant="outline" size="sm" class="cursor-pointer gap-1.5 rounded-full px-4">
                    <ExternalLink class="size-3.5" />
                    扫描列表
                  </Button>
                </router-link>
                <Button variant="outline" size="sm" class="cursor-pointer gap-1.5 rounded-full px-4" :disabled="loading" @click="loadAll">
                  <RefreshCw class="size-3.5" :class="loading ? 'animate-spin' : ''" />
                  刷新
                </Button>
              </div>
            </div>

            <ModuleFeedbackCard
              v-if="probeIssues.length"
              title="部分探测模块同步失败"
              description="页面已经保留成功模块，其余分区可继续单独排查，不需要整页一起报废。"
              :error="`异常模块：${probeIssues.map(item => item.label).join('、')}`"
              :logs="probeIssues.flatMap(item => item.logs)"
              @retry="loadAll"
            />

            <div class="grid gap-4 lg:grid-cols-[1.08fr_0.92fr]">
              <div class="ops-panel">
                <div class="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div class="space-y-2">
                    <p class="ops-section-copy uppercase tracking-[0.2em]">{{ probePosture.eyebrow }}</p>
                    <h2 class="text-3xl font-semibold tracking-tight text-foreground">{{ probePosture.title }}</h2>
                    <p class="max-w-3xl text-sm leading-7 text-muted-foreground">{{ probePosture.body }}</p>
                  </div>
                  <Badge variant="outline" :class="probePosture.badgeClass" class="rounded-full px-3 py-1 text-xs">
                    {{ probePosture.badge }}
                  </Badge>
                </div>
                <div class="mt-5 grid gap-3 md:grid-cols-3">
                  <div v-for="item in heroHighlights" :key="item.label" class="ops-highlight-tile">
                    <p class="ops-highlight-label">{{ item.label }}</p>
                    <p class="ops-highlight-value" :class="item.valueClass">{{ item.value }}</p>
                    <p class="ops-highlight-note">{{ item.note }}</p>
                    <div v-if="item.progress !== undefined" class="mt-3 ops-kpi-bar">
                      <div class="ops-kpi-fill" :style="{ width: `${item.progress}%` }"></div>
                    </div>
                  </div>
                </div>
              </div>

              <div class="ops-panel flex h-full flex-col justify-between gap-5">
                <div class="space-y-2">
                  <p class="ops-section-title">扫描建议</p>
                  <p class="ops-section-copy">优先补齐覆盖缺口，再消化队列，再处理高危发现，避免扫描变成纯跑批。</p>
                </div>
                <div class="ops-note-list">
                  <div v-for="(item, index) in probeActions" :key="item" class="ops-note-item">
                    <span class="ops-note-index">{{ index + 1 }}</span>
                    <p class="text-sm leading-6 text-foreground/90">{{ item }}</p>
                  </div>
                </div>
                <div class="grid gap-3 sm:grid-cols-2">
                  <div class="ops-highlight-tile">
                    <p class="ops-highlight-label">覆盖率</p>
                    <p class="ops-highlight-value" :class="coverageRate >= 85 ? 'text-cyan-300' : 'text-amber-300'">{{ coverageRate }}%</p>
                    <p class="ops-highlight-note">{{ stats.totalAssets }} 个资产中启用了 {{ stats.enabledAssets }} 个。</p>
                  </div>
                  <div class="ops-highlight-tile">
                    <p class="ops-highlight-label">链路健康</p>
                    <p class="ops-highlight-value" :class="probeChainOverview.unhealthy > 0 ? 'text-amber-300' : 'text-emerald-300'">
                      {{ probeChainOverview.unhealthy > 0 ? '需排查' : '稳定' }}
                    </p>
                    <p class="ops-highlight-note">{{ probeChainOverview.summary }}</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="space-y-4">
            <div class="ops-panel space-y-3">
              <div>
                <p class="ops-section-title">暴露面焦点</p>
                <p class="ops-section-copy">直接指出当前最需要补洞的地方，而不是只显示静态统计。</p>
              </div>
              <div class="space-y-3">
                <div v-for="item in exposureFocus" :key="item.label" class="ops-status-row">
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
                <p class="text-sm font-medium text-foreground">当前环境没有探测样本</p>
                <p class="text-xs leading-6 text-muted-foreground">
                  运行 <code class="ops-inline-code">python backend/seed_demo_data.py</code>
                  会导入演示资产、扫描任务、漏洞发现和审计样本，方便直接评估探测链路效果。
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      <section class="grid gap-4 lg:grid-cols-2 2xl:grid-cols-4">
        <ModuleFeedbackCard
          v-if="probeFeedback.assets.error || probeFeedback.tasks.error || probeFeedback.findings.error"
          class="lg:col-span-2 2xl:col-span-4"
          title="核心探测指标暂时不可用"
          description="资产、任务或漏洞模块没有完整同步成功，当前不展示聚合 KPI，避免误导后续判断。"
          :error="[probeFeedback.assets.error, probeFeedback.tasks.error, probeFeedback.findings.error].filter(Boolean).join('；')"
          :logs="[
            ...probeFeedback.assets.logs,
            ...probeFeedback.tasks.logs,
            ...probeFeedback.findings.logs,
          ]"
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

      <section class="grid gap-4 xl:grid-cols-[1fr_1fr]">
        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">待处理扫描队列</CardTitle>
            <p class="ops-section-copy">最近任务不只看状态，还要给出当前应该怎么处理。</p>
          </CardHeader>
          <CardContent class="space-y-4 pt-5">
            <div v-if="loading" class="space-y-2">
              <Skeleton v-for="i in 4" :key="i" class="h-18 w-full rounded-xl" />
            </div>
            <ModuleFeedbackCard
              v-else-if="probeFeedback.tasks.error"
              title="任务队列同步失败"
              description="最近任务列表没有返回，当前无法判断排队、运行和失败的真实情况。"
              :error="probeFeedback.tasks.error"
              :logs="probeFeedback.tasks.logs"
              @retry="loadAll"
            />
            <div v-else-if="recentTasks.length === 0" class="ops-empty">
              <p class="ops-empty-title">暂无扫描任务</p>
              <p class="ops-empty-copy">当前没有运行或历史任务，建议先导入样本资产或创建首个扫描任务。</p>
            </div>
            <div v-else class="ops-list">
              <div v-for="task in recentTasks" :key="task.id" class="ops-list-item">
                <div class="min-w-0 space-y-2">
                  <div class="flex flex-wrap items-center gap-2">
                    <code class="ops-inline-code">{{ task.target }}</code>
                    <Badge variant="outline" class="rounded-full border-border/70 bg-background/40 px-2 py-0.5 text-[11px] text-muted-foreground">
                      {{ task.profile || 'default' }}
                    </Badge>
                    <Badge :class="getStateColor(task.state)" class="rounded-full px-2 py-0.5 text-[11px]">
                      {{ getStateLabel(task.state) }}
                    </Badge>
                  </div>
                  <p class="text-xs leading-6 text-muted-foreground">{{ formatTime(task.created_at) }} 创建 · {{ task.tool_name }}</p>
                  <p class="text-xs text-foreground/85">{{ taskAction(task.state) }}</p>
                </div>
                <span class="text-xs text-muted-foreground">#{{ task.id }}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card class="ops-section-card">
          <CardHeader class="space-y-3 pb-0">
            <div class="space-y-1">
              <CardTitle class="ops-section-title">漏洞暴露结构</CardTitle>
              <p class="ops-section-copy">把高危、中危、低危拆开后，再决定是先补洞还是继续扩面。</p>
            </div>
            <div class="grid gap-3 md:grid-cols-3">
              <div v-for="item in severityHighlights" :key="item.label" class="ops-highlight-tile">
                <p class="ops-highlight-label">{{ item.label }}</p>
                <p class="ops-highlight-value" :class="item.valueClass">{{ item.value }}</p>
                <p class="ops-highlight-note">{{ item.note }}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent class="grid gap-5 pt-5 lg:grid-cols-[0.9fr_1fr] lg:items-center">
            <div v-if="loading" class="ops-empty min-h-[14rem]">
              <Skeleton class="size-40 rounded-full" />
            </div>
            <ModuleFeedbackCard
              v-else-if="probeFeedback.findings.error"
              title="漏洞结构同步失败"
              description="严重程度分布没有返回，暂时无法判断当前应该先补洞还是继续扩面。"
              :error="probeFeedback.findings.error"
              :logs="probeFeedback.findings.logs"
              @retry="loadAll"
            />
            <div v-else-if="stats.totalFindings === 0" class="ops-empty min-h-[14rem]">
              <p class="ops-empty-title">暂无漏洞发现</p>
              <p class="ops-empty-copy">等到扫描结果完成解析后，这里会显示严重程度结构和当前暴露压力。</p>
            </div>
            <template v-else>
              <div class="mx-auto h-56 w-56 max-w-full">
                <Doughnut :data="severityChartData" :options="doughnutOptions" />
              </div>
              <div class="space-y-3">
                <div v-for="item in severitySummary" :key="item.label" class="ops-status-row">
                  <div class="min-w-0 space-y-1">
                    <div class="flex items-center gap-2">
                      <span class="ops-status-dot" :class="item.dotClass"></span>
                      <p class="text-sm font-medium text-foreground">{{ item.label }}</p>
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
      </section>

      <section class="grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">任务状态分布</CardTitle>
            <p class="ops-section-copy">看当前任务是卡在排队、运行还是失败，决定要扩资源还是做排障。</p>
          </CardHeader>
          <CardContent class="grid gap-5 pt-5 lg:grid-cols-[0.86fr_1fr] lg:items-center">
            <div v-if="loading" class="ops-empty min-h-[14rem]">
              <Skeleton class="size-36 rounded-full" />
            </div>
            <ModuleFeedbackCard
              v-else-if="probeFeedback.tasks.error"
              title="任务状态同步失败"
              description="当前拿不到任务状态统计，先不要据此决定扩容还是排障。"
              :error="probeFeedback.tasks.error"
              :logs="probeFeedback.tasks.logs"
              @retry="loadAll"
            />
            <template v-else>
              <div class="mx-auto h-52 w-52 max-w-full">
                <Doughnut :data="taskStateChartData" :options="taskDoughnutOptions" />
              </div>
              <div class="space-y-3">
                <div v-for="item in taskStateSummary" :key="item.label" class="ops-status-row">
                  <div class="min-w-0 space-y-1">
                    <div class="flex items-center gap-2">
                      <span class="ops-status-dot" :class="item.dotClass"></span>
                      <p class="text-sm font-medium text-foreground">{{ item.label }}</p>
                    </div>
                    <p class="text-xs leading-6 text-muted-foreground">{{ item.note }}</p>
                  </div>
                  <p class="text-sm font-semibold tabular-nums text-foreground">{{ item.count }}</p>
                </div>
              </div>
            </template>
          </CardContent>
        </Card>

        <Card class="ops-section-card">
          <CardHeader class="space-y-3 pb-0">
            <div class="space-y-1">
              <CardTitle class="ops-section-title">7 天交付趋势</CardTitle>
              <p class="ops-section-copy">看任务交付量是否稳定，避免只有任务创建，没有结果输出。</p>
            </div>
            <div class="grid gap-3 md:grid-cols-3">
              <div v-for="item in throughputHighlights" :key="item.label" class="ops-highlight-tile">
                <p class="ops-highlight-label">{{ item.label }}</p>
                <p class="ops-highlight-value" :class="item.valueClass">{{ item.value }}</p>
                <p class="ops-highlight-note">{{ item.note }}</p>
              </div>
            </div>
          </CardHeader>
          <CardContent class="pt-5">
            <div v-if="loading" class="ops-empty">
              <Skeleton class="h-52 w-full rounded-xl" />
            </div>
            <ModuleFeedbackCard
              v-else-if="probeFeedback.tasks.error"
              title="交付趋势同步失败"
              description="交付趋势没有成功返回，当前无法确认任务产出是否稳定。"
              :error="probeFeedback.tasks.error"
              :logs="probeFeedback.tasks.logs"
              @retry="loadAll"
            />
            <div v-else class="h-[19rem]">
              <Bar :data="trendChartData" :options="barOptions" />
            </div>
          </CardContent>
        </Card>
      </section>

      <section class="grid gap-4 xl:grid-cols-[0.84fr_1.16fr]">
        <Card class="ops-section-card">
          <CardHeader class="space-y-1 pb-0">
            <CardTitle class="ops-section-title">探测链路可信度</CardTitle>
            <p class="ops-section-copy">确认资产、任务调度、结果解析是否都在健康线内，避免指标看起来正常但链路其实断裂。</p>
          </CardHeader>
          <CardContent class="space-y-4 pt-5">
            <ModuleFeedbackCard
              v-if="probeFeedback.chain.error"
              title="探测链路状态同步失败"
              description="链路健康指标没有返回，先不要根据当前页面决定是否扩面或排障。"
              :error="probeFeedback.chain.error"
              :logs="probeFeedback.chain.logs"
              @retry="loadAll"
            />
            <template v-else>
            <div class="grid gap-3 md:grid-cols-2">
              <div class="ops-highlight-tile">
                <p class="ops-highlight-label">健康节点</p>
                <p class="ops-highlight-value text-emerald-300">{{ probeChainOverview.healthy }}</p>
                <p class="ops-highlight-note">{{ probeChainOverview.total }} 个节点中，{{ probeChainOverview.unhealthy }} 个需要排查。</p>
              </div>
              <div class="ops-highlight-tile">
                <p class="ops-highlight-label">值班判断</p>
                <p class="ops-highlight-value" :class="probeChainOverview.unhealthy > 0 ? 'text-amber-300' : 'text-cyan-300'">
                  {{ probeChainOverview.unhealthy > 0 ? '先排障' : '可扩面' }}
                </p>
                <p class="ops-highlight-note">{{ probeChainOverview.summary }}</p>
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
            <CardTitle class="ops-section-title">高危发现工作面</CardTitle>
            <p class="ops-section-copy">高危发现必须带上时间、状态和建议动作，避免只停留在漏洞清单层面。</p>
          </CardHeader>
          <CardContent class="pt-5">
            <div v-if="loading" class="ops-empty">
              <Skeleton class="h-56 w-full rounded-xl" />
            </div>
            <ModuleFeedbackCard
              v-else-if="probeFeedback.findings.error"
              title="高危发现同步失败"
              description="高危发现列表没有返回，当前无法确认最需要优先处理的资产和漏洞。"
              :error="probeFeedback.findings.error"
              :logs="probeFeedback.findings.logs"
              @retry="loadAll"
            />
            <div v-else-if="highFindings.length === 0" class="ops-empty">
              <p class="ops-empty-title">暂无高危发现</p>
              <p class="ops-empty-copy">当前还没有高危漏洞样本，等扫描结果积累后这里会列出最需要优先确认的发现。</p>
            </div>
            <div v-else class="ops-table">
              <table>
                <thead>
                  <tr>
                    <th>资产</th>
                    <th>端口 / 服务</th>
                    <th>CVE</th>
                    <th>发现时间</th>
                    <th>建议</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="finding in highFindings" :key="finding.id">
                    <td><code class="ops-inline-code">{{ finding.asset }}</code></td>
                    <td class="text-xs text-muted-foreground">{{ finding.port || '--' }}/{{ finding.service || 'unknown' }}</td>
                    <td class="text-xs text-muted-foreground">{{ finding.cve || '--' }}</td>
                    <td class="text-xs text-muted-foreground">{{ formatTime(finding.created_at) }}</td>
                    <td class="text-xs text-muted-foreground">{{ findingAction(finding.status) }}</td>
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
import { Doughnut, Bar } from 'vue-chartjs'
import {
  Chart as ChartJS,
  ArcElement,
  Tooltip,
  Legend,
  CategoryScale,
  LinearScale,
  BarElement,
  Title,
} from 'chart.js'
import { scanApi, type ScanTask, type ScanFinding } from '@/api/scan'
import { overviewApi, type OverviewChainStatus } from '@/api/overview'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { RefreshCw, ExternalLink } from 'lucide-vue-next'
import ModuleFeedbackCard from '@/components/dashboard/ModuleFeedbackCard.vue'

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, BarElement, Title)

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

type ProbeModuleKey = 'assets' | 'tasks' | 'findings' | 'chain'

interface ModuleFeedback {
  error: string | null
  logs: string[]
}

const createFeedbackState = (): ModuleFeedback => ({ error: null, logs: [] })

const loading = ref(false)
const recentTasks = ref<ScanTask[]>([])
const trendTasks = ref<ScanTask[]>([])
const highFindings = ref<ScanFinding[]>([])
const taskStateCounts = ref({ CREATED: 0, RUNNING: 0, REPORTED: 0, FAILED: 0 })
const chainStatusData = ref<OverviewChainStatus | null>(null)
const probeFeedback = reactive<Record<ProbeModuleKey, ModuleFeedback>>({
  assets: createFeedbackState(),
  tasks: createFeedbackState(),
  findings: createFeedbackState(),
  chain: createFeedbackState(),
})

const stats = ref({
  totalAssets: 0,
  enabledAssets: 0,
  runningTasks: 0,
  totalFindings: 0,
  highFindings: 0,
  mediumFindings: 0,
  lowFindings: 0,
  infoFindings: 0,
})

const probeModuleLabels: Record<ProbeModuleKey, string> = {
  assets: '资产覆盖',
  tasks: '任务链路',
  findings: '漏洞发现',
  chain: '链路状态',
}

const resetProbeFeedback = () => {
  ;(Object.keys(probeFeedback) as ProbeModuleKey[]).forEach((key) => {
    probeFeedback[key].error = null
    probeFeedback[key].logs = []
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

const setProbeFeedback = (key: ProbeModuleKey, error: unknown) => {
  const message = normalizeError(error)
  probeFeedback[key].error = message
  probeFeedback[key].logs = [
    `${new Date().toLocaleString('zh-CN')} ${probeModuleLabels[key]}同步失败`,
    message,
  ]
  console.error(`Probe ${key} load failed:`, error)
}

const chainStatus = computed(() => chainStatusData.value?.probe ?? [])
const probeIssues = computed(() =>
  (Object.keys(probeFeedback) as ProbeModuleKey[])
    .filter(key => probeFeedback[key].error)
    .map(key => ({
      key,
      label: probeModuleLabels[key],
      error: probeFeedback[key].error,
      logs: probeFeedback[key].logs,
    })),
)
const coverageRate = computed(() => stats.value.totalAssets > 0 ? Math.round((stats.value.enabledAssets / stats.value.totalAssets) * 100) : 0)
const backlogCount = computed(() => taskStateCounts.value.CREATED + taskStateCounts.value.RUNNING)
const deliveryRate = computed(() => {
  const finished = taskStateCounts.value.REPORTED + taskStateCounts.value.FAILED
  return finished > 0 ? Math.round((taskStateCounts.value.REPORTED / finished) * 100) : 0
})
const findingPressure = computed(() => stats.value.totalFindings > 0 ? Math.round((stats.value.highFindings / stats.value.totalFindings) * 100) : 0)

const probeChainOverview = computed(() => {
  const total = chainStatus.value.length
  const healthy = chainStatus.value.filter(item => item.ok).length
  const unhealthy = total - healthy
  return {
    total,
    healthy,
    unhealthy,
    summary: unhealthy > 0 ? `${unhealthy} 个节点没有达到健康线。` : '当前探测链路没有明显断点。',
  }
})

const probePosture = computed(() => {
  if (stats.value.totalAssets === 0 && stats.value.totalFindings === 0 && recentTasks.value.length === 0) {
    return {
      eyebrow: 'Cold Start',
      title: '当前还没有形成探测样本面',
      subtitle: '先补资产和扫描任务，再谈暴露面判断和优先级。',
      body: '没有资产、任务和发现时，任何看板都只会是空壳。先导入样本数据或真实资产，才能评估扫描链路是否可信。',
      badge: 'Seed First',
      badgeClass: 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    }
  }

  if (stats.value.highFindings > 0) {
    return {
      eyebrow: 'High Exposure',
      title: '当前暴露面存在高危积压',
      subtitle: '先处理高危发现，再继续扩大扫描范围，避免把更多噪声堆进队列。',
      body: `当前高危发现 ${stats.value.highFindings} 个，占总发现 ${findingPressure.value}% ，需要先确认资产责任和修复路径。`,
      badge: 'Escalate',
      badgeClass: 'border-red-500/30 bg-red-500/10 text-red-300',
    }
  }

  if (backlogCount.value > 0 || stats.value.runningTasks > 0) {
    return {
      eyebrow: 'Pipeline Busy',
      title: '链路正在消化扫描队列',
      subtitle: '当前更像产线负载管理问题，不是单纯的暴露面扩张问题。',
      body: `排队和运行中的任务共有 ${backlogCount.value} 个，已交付任务成功率 ${deliveryRate.value}% ，需要先稳住节奏。`,
      badge: 'Monitor',
      badgeClass: 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300',
    }
  }

  return {
    eyebrow: 'Stable Sweep',
    title: '当前探测链路总体稳定',
    subtitle: '资产覆盖、任务交付和漏洞压力都在可控区间，可以继续扩面。',
    body: '没有高危发现堆积，也没有明显的运行堵塞，当前更适合扩大覆盖面和优化扫描策略。',
    badge: 'Steady',
    badgeClass: 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
  }
})

const heroHighlights = computed(() => [
  {
    label: '资产覆盖',
    value: `${coverageRate.value}%`,
    note: `${stats.value.enabledAssets}/${stats.value.totalAssets} 资产已启用探测。`,
    valueClass: coverageRate.value >= 85 ? 'text-cyan-300' : 'text-amber-300',
    progress: coverageRate.value,
  },
  {
    label: '运行中任务',
    value: String(stats.value.runningTasks),
    note: backlogCount.value > 0 ? `排队和运行合计 ${backlogCount.value} 个。` : '当前没有排队压力。',
    valueClass: stats.value.runningTasks > 0 ? 'text-foreground' : 'text-cyan-300',
  },
  {
    label: '高危发现',
    value: String(stats.value.highFindings),
    note: stats.value.highFindings > 0 ? `占总发现 ${findingPressure.value}% 。` : '当前没有高危发现抬头。',
    valueClass: stats.value.highFindings > 0 ? 'text-red-300' : 'text-emerald-300',
  },
])

const probeActions = computed(() => {
  const actions: string[] = []

  if (coverageRate.value < 85) {
    actions.push(`先补齐资产覆盖，当前覆盖率 ${coverageRate.value}% ，未启用资产会直接导致暴露面盲区。`)
  }
  if (stats.value.highFindings > 0) {
    actions.push(`优先确认 ${stats.value.highFindings} 个高危发现的责任资产和状态，避免只继续跑扫描。`)
  }
  if (backlogCount.value > 0) {
    actions.push(`队列里还有 ${backlogCount.value} 个任务，先稳定调度和执行速度，再扩大扫描范围。`)
  }
  if (probeChainOverview.value.unhealthy > 0) {
    actions.push(`链路有 ${probeChainOverview.value.unhealthy} 个节点不健康，先排障再看统计结果。`)
  }
  if (!actions.length) {
    actions.push('当前可以继续扩展扫描范围，把更多高价值资产纳入基线探测。')
  }

  return actions.slice(0, 3)
})

const exposureFocus = computed(() => [
  {
    label: '覆盖缺口',
    value: `${Math.max(stats.value.totalAssets - stats.value.enabledAssets, 0)}`,
    note: coverageRate.value < 85 ? '覆盖不足会让漏洞分布判断失真。' : '当前覆盖缺口处于可接受范围。',
    dotClass: coverageRate.value < 85 ? 'bg-amber-400' : 'bg-emerald-400',
    valueClass: coverageRate.value < 85 ? 'text-amber-300' : 'text-emerald-300',
  },
  {
    label: '排队压力',
    value: `${backlogCount.value}`,
    note: backlogCount.value > 0 ? '任务队列还没有完全出清，交付效率要继续盯。' : '当前没有明显排队积压。',
    dotClass: backlogCount.value > 0 ? 'bg-cyan-400' : 'bg-emerald-400',
    valueClass: backlogCount.value > 0 ? 'text-cyan-300' : 'text-emerald-300',
  },
  {
    label: '高危发现率',
    value: `${findingPressure.value}%`,
    note: findingPressure.value >= 20 ? '高危占比偏高，优先级应转向补洞。' : '高危占比可控，可以继续扩大探测面。',
    dotClass: findingPressure.value >= 20 ? 'bg-red-400' : 'bg-emerald-400',
    valueClass: findingPressure.value >= 20 ? 'text-red-300' : 'text-emerald-300',
  },
])

const narrativeCards = computed<NarrativeCard[]>(() => [
  {
    label: '资产覆盖',
    badge: coverageRate.value >= 85 ? 'Covered' : 'Gap',
    badgeClass: coverageRate.value >= 85 ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    value: `${coverageRate.value}%`,
    valueClass: coverageRate.value >= 85 ? 'text-cyan-300' : 'text-amber-300',
    compare: `已启用 ${stats.value.enabledAssets} / 总资产 ${stats.value.totalAssets}。`,
    explain: stats.value.totalAssets > 0 ? '覆盖率越低，探测结论越像局部样本，无法代表真实暴露面。' : '当前没有资产样本，任何漏洞结论都不完整。',
    next: stats.value.totalAssets > 0 ? '优先把高价值资产纳入启用列表，再扩面。' : '先导入资产或演示数据，建立最小样本面。',
  },
  {
    label: '扫描负载',
    badge: backlogCount.value > 0 ? 'Busy' : 'Idle',
    badgeClass: backlogCount.value > 0 ? 'border-cyan-500/30 bg-cyan-500/10 text-cyan-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    value: `${backlogCount.value}`,
    valueClass: backlogCount.value > 0 ? 'text-cyan-300' : 'text-emerald-300',
    compare: `运行中 ${stats.value.runningTasks} 个，已完成 ${taskStateCounts.value.REPORTED} 个。`,
    explain: backlogCount.value > 0 ? '任务还在排队或执行，说明当前瓶颈更可能在调度和执行，而不是数据展示。' : '当前产线没有明显堵塞，可以继续安排更多任务。',
    next: backlogCount.value > 0 ? '先确认调度吞吐和失败原因，再决定是否扩大扫描范围。' : '按资产优先级继续拉高扫描覆盖率。',
  },
  {
    label: '高危发现率',
    badge: findingPressure.value >= 20 ? 'High' : 'Quiet',
    badgeClass: findingPressure.value >= 20 ? 'border-red-500/30 bg-red-500/10 text-red-300' : 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300',
    value: `${findingPressure.value}%`,
    valueClass: findingPressure.value >= 20 ? 'text-red-300' : 'text-emerald-300',
    compare: `高危 ${stats.value.highFindings} / 总发现 ${stats.value.totalFindings}。`,
    explain: stats.value.highFindings > 0 ? '高危发现越多，当前值班动作越应该偏向确认资产责任和修复窗口。' : '高危发现为空，当前更适合做基线扩面和规则优化。',
    next: stats.value.highFindings > 0 ? '优先处理高危发现，再回头优化中低危噪声。' : '保持基线扫描，防止高危在下一轮集中冒头。',
  },
  {
    label: '交付吞吐',
    badge: deliveryRate.value >= 85 ? 'Healthy' : 'Watch',
    badgeClass: deliveryRate.value >= 85 ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-amber-500/30 bg-amber-500/10 text-amber-300',
    value: `${deliveryRate.value}%`,
    valueClass: deliveryRate.value >= 85 ? 'text-emerald-300' : 'text-amber-300',
    compare: `已报告 ${taskStateCounts.value.REPORTED} 个，失败 ${taskStateCounts.value.FAILED} 个。`,
    explain: deliveryRate.value >= 85 ? '任务最终产出稳定，说明解析和报告链路总体可靠。' : '失败比例偏高时，看板上的漏洞统计也会跟着失真。',
    next: deliveryRate.value >= 85 ? '继续扩展任务规模，同时观察失败是否集中在某个 profile。' : '先排查失败任务，再继续放量。',
  },
])

const severitySummary = computed(() => {
  const total = stats.value.totalFindings || 1
  return [
    {
      label: 'HIGH',
      count: stats.value.highFindings,
      pct: Math.round((stats.value.highFindings / total) * 100),
      dotClass: 'bg-red-400',
      valueClass: stats.value.highFindings > 0 ? 'text-red-300' : 'text-emerald-300',
      note: stats.value.highFindings > 0 ? '需要优先进入责任确认和修复节奏。' : '当前没有高危发现。',
    },
    {
      label: 'MEDIUM',
      count: stats.value.mediumFindings,
      pct: Math.round((stats.value.mediumFindings / total) * 100),
      dotClass: 'bg-amber-400',
      valueClass: 'text-amber-300',
      note: '中危更适合结合资产价值决定处置优先级。',
    },
    {
      label: 'LOW',
      count: stats.value.lowFindings,
      pct: Math.round((stats.value.lowFindings / total) * 100),
      dotClass: 'bg-cyan-400',
      valueClass: 'text-cyan-300',
      note: '低危更多用于暴露面画像，而不是抢占值班注意力。',
    },
    {
      label: 'INFO',
      count: stats.value.infoFindings,
      pct: Math.round((stats.value.infoFindings / total) * 100),
      dotClass: 'bg-slate-400',
      valueClass: 'text-muted-foreground',
      note: '信息类更适合做资产指纹和基线补充。',
    },
  ]
})

const severityHighlights = computed(() => [
  {
    label: '总发现',
    value: String(stats.value.totalFindings),
    valueClass: 'text-foreground',
    note: stats.value.totalFindings > 0 ? '已经形成可分析的暴露面样本。' : '等待扫描结果产出。',
  },
  {
    label: '高危发现',
    value: String(stats.value.highFindings),
    valueClass: stats.value.highFindings > 0 ? 'text-red-300' : 'text-emerald-300',
    note: stats.value.highFindings > 0 ? '需要优先补洞。' : '当前没有高危压力。',
  },
  {
    label: '高危占比',
    value: `${findingPressure.value}%`,
    valueClass: findingPressure.value >= 20 ? 'text-amber-300' : 'text-cyan-300',
    note: findingPressure.value >= 20 ? '结构偏陡，先处理高危。' : '结构可控，适合继续扩面。',
  },
])

const taskStateSummary = computed(() => [
  {
    label: '待调度',
    count: taskStateCounts.value.CREATED,
    dotClass: 'bg-slate-400',
    note: taskStateCounts.value.CREATED > 0 ? '任务还在等待资源或调度窗口。' : '当前没有排队等待任务。',
  },
  {
    label: '运行中',
    count: taskStateCounts.value.RUNNING,
    dotClass: 'bg-cyan-400',
    note: taskStateCounts.value.RUNNING > 0 ? '当前资源正在消化实时任务。' : '当前没有活动执行任务。',
  },
  {
    label: '已交付',
    count: taskStateCounts.value.REPORTED,
    dotClass: 'bg-emerald-400',
    note: '代表扫描、解析和报告链路最终闭环。',
  },
  {
    label: '失败',
    count: taskStateCounts.value.FAILED,
    dotClass: 'bg-red-400',
    note: taskStateCounts.value.FAILED > 0 ? '需要优先排查失败原因，否则统计会失真。' : '当前没有失败任务积压。',
  },
])

const throughputHighlights = computed(() => {
  const todayDone = trendTasks.value.filter(task => {
    const ended = task.ended_at || task.created_at
    return ended && ended.slice(0, 10) === new Date().toISOString().slice(0, 10) && (task.state === 'REPORTED' || task.state === 'FAILED')
  }).length

  return [
    {
      label: '今日交付',
      value: String(todayDone),
      valueClass: todayDone > 0 ? 'text-foreground' : 'text-muted-foreground',
      note: todayDone > 0 ? '代表今天已经有扫描结果产出。' : '今天还没有结果交付。',
    },
    {
      label: '成功率',
      value: `${deliveryRate.value}%`,
      valueClass: deliveryRate.value >= 85 ? 'text-emerald-300' : 'text-amber-300',
      note: deliveryRate.value >= 85 ? '交付链路总体稳定。' : '失败比例偏高，需要先排障。',
    },
    {
      label: '运行压力',
      value: String(backlogCount.value),
      valueClass: backlogCount.value > 0 ? 'text-cyan-300' : 'text-emerald-300',
      note: backlogCount.value > 0 ? '排队和运行中的任务仍在消耗带宽。' : '当前没有明显积压。',
    },
  ]
})

const showDemoHint = computed(() =>
  !loading.value &&
  probeIssues.value.length === 0 &&
  stats.value.totalAssets === 0 &&
  stats.value.totalFindings === 0 &&
  stats.value.runningTasks === 0 &&
  recentTasks.value.length === 0,
)

const severityChartData = computed(() => ({
  labels: severitySummary.value.map(item => item.label),
  datasets: [{
    data: severitySummary.value.map(item => item.count),
    backgroundColor: ['rgba(245,104,92,0.85)', 'rgba(255,189,91,0.85)', 'rgba(82,214,205,0.82)', 'rgba(148,163,184,0.7)'],
    borderWidth: 0,
    hoverOffset: 6,
  }],
}))

const doughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '64%',
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx: any) => ` ${ctx.label}: ${ctx.parsed}` } },
  },
}

const taskStateChartData = computed(() => ({
  labels: ['待调度', '运行中', '已交付', '失败'],
  datasets: [{
    data: [taskStateCounts.value.CREATED, taskStateCounts.value.RUNNING, taskStateCounts.value.REPORTED, taskStateCounts.value.FAILED],
    backgroundColor: ['rgba(148,163,184,0.72)', 'rgba(82,214,205,0.82)', 'rgba(52,211,153,0.82)', 'rgba(245,104,92,0.84)'],
    borderWidth: 0,
    hoverOffset: 6,
  }],
}))

const taskDoughnutOptions = {
  responsive: true,
  maintainAspectRatio: false,
  cutout: '62%',
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx: any) => ` ${ctx.label}: ${ctx.parsed}` } },
  },
}

const trendChartData = computed(() => {
  const days: string[] = []
  const counts: number[] = []
  const now = new Date()
  for (let i = 6; i >= 0; i -= 1) {
    const d = new Date(now)
    d.setDate(d.getDate() - i)
    const key = `${d.getMonth() + 1}/${d.getDate()}`
    days.push(key)
    const isoDate = d.toISOString().slice(0, 10)
    const count = trendTasks.value.filter(task => {
      const ended = task.ended_at || task.created_at
      return ended && ended.slice(0, 10) === isoDate && (task.state === 'REPORTED' || task.state === 'FAILED')
    }).length
    counts.push(count)
  }
  return {
    labels: days,
    datasets: [{
      label: '交付任务数',
      data: counts,
      backgroundColor: 'rgba(255, 157, 66, 0.72)',
      borderRadius: 6,
    }],
  }
})

const barOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: { callbacks: { label: (ctx: any) => ` 交付任务 ${ctx.parsed.y}` } },
  },
  scales: {
    x: { grid: { display: false }, ticks: { color: '#cbd5e1', font: { size: 11 } } },
    y: { beginAtZero: true, grid: { color: 'rgba(148,163,184,0.12)' }, ticks: { color: '#cbd5e1', precision: 0 } },
  },
}

const loadAll = async () => {
  loading.value = true
  resetProbeFeedback()
  try {
    const [assetsSnapshot, tasksSnapshot, findingsSnapshot, chainSnapshot] = await Promise.allSettled([
      Promise.all([
        scanApi.getAssets({ page_size: 1 }),
        scanApi.getAssets({ enabled: true, page_size: 1 }),
      ]),
      Promise.all([
        scanApi.getTasks({ state: 'RUNNING', page_size: 1 }),
        scanApi.getTasks({ page: 1, page_size: 6 }),
        scanApi.getTasks({ state: 'CREATED', page_size: 1 }),
        scanApi.getTasks({ state: 'RUNNING', page_size: 1 }),
        scanApi.getTasks({ state: 'REPORTED', page_size: 1 }),
        scanApi.getTasks({ state: 'FAILED', page_size: 1 }),
        scanApi.getTasks({ page: 1, page_size: 100 }),
      ]),
      Promise.all([
        scanApi.getFindings({ page_size: 1 }),
        scanApi.getFindings({ severity: 'HIGH', page_size: 8 }),
        scanApi.getFindings({ severity: 'MEDIUM', page_size: 1 }),
        scanApi.getFindings({ severity: 'LOW', page_size: 1 }),
        scanApi.getFindings({ severity: 'INFO', page_size: 1 }),
      ]),
      overviewApi.getChainStatus(),
    ])

    if (assetsSnapshot.status === 'fulfilled') {
      const [assetsAll, assetsEnabled] = assetsSnapshot.value
      stats.value.totalAssets = assetsAll.total
      stats.value.enabledAssets = assetsEnabled.total
    } else {
      stats.value.totalAssets = 0
      stats.value.enabledAssets = 0
      setProbeFeedback('assets', assetsSnapshot.reason)
    }

    if (tasksSnapshot.status === 'fulfilled') {
      const [tasksRunning, tasksRecent, stateCreated, stateRunning, stateReported, stateFailed, tasksTrend] = tasksSnapshot.value
      stats.value.runningTasks = tasksRunning.total
      taskStateCounts.value = {
        CREATED: stateCreated.total,
        RUNNING: stateRunning.total,
        REPORTED: stateReported.total,
        FAILED: stateFailed.total,
      }
      recentTasks.value = tasksRecent.items
      trendTasks.value = tasksTrend.items
    } else {
      stats.value.runningTasks = 0
      taskStateCounts.value = { CREATED: 0, RUNNING: 0, REPORTED: 0, FAILED: 0 }
      recentTasks.value = []
      trendTasks.value = []
      setProbeFeedback('tasks', tasksSnapshot.reason)
    }

    if (findingsSnapshot.status === 'fulfilled') {
      const [findingsAll, findingsHigh, findingsMed, findingsLow, findingsInfo] = findingsSnapshot.value
      stats.value.totalFindings = findingsAll.total
      stats.value.highFindings = findingsHigh.total
      stats.value.mediumFindings = findingsMed.total
      stats.value.lowFindings = findingsLow.total
      stats.value.infoFindings = findingsInfo.total
      highFindings.value = findingsHigh.items
    } else {
      stats.value.totalFindings = 0
      stats.value.highFindings = 0
      stats.value.mediumFindings = 0
      stats.value.lowFindings = 0
      stats.value.infoFindings = 0
      highFindings.value = []
      setProbeFeedback('findings', findingsSnapshot.reason)
    }

    if (chainSnapshot.status === 'fulfilled') {
      chainStatusData.value = chainSnapshot.value ?? { defense: [], probe: [], generated_at: new Date().toISOString() }
    } else {
      chainStatusData.value = { defense: [], probe: [], generated_at: new Date().toISOString() }
      setProbeFeedback('chain', chainSnapshot.reason)
    }
  } finally {
    loading.value = false
  }
}

const getStateColor = (state: string) => {
  const map: Record<string, string> = {
    CREATED: 'border-border/70 bg-muted text-muted-foreground',
    RUNNING: 'border-cyan-500/30 bg-cyan-500/12 text-cyan-300',
    REPORTED: 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300',
    FAILED: 'border-red-500/30 bg-red-500/12 text-red-300',
    DISPATCHED: 'border-blue-500/30 bg-blue-500/12 text-blue-300',
    PARSED: 'border-amber-500/30 bg-amber-500/12 text-amber-300',
  }
  return map[state] || 'border-border/70 bg-muted text-muted-foreground'
}

const getStateLabel = (state: string) => {
  const map: Record<string, string> = {
    CREATED: '待调度',
    DISPATCHED: '已分发',
    RUNNING: '运行中',
    PARSED: '解析中',
    REPORTED: '已交付',
    FAILED: '失败',
  }
  return map[state] || state
}

const taskAction = (state: string) => {
  if (state === 'CREATED') return '建议确认调度窗口和资源配额，避免长时间排队。'
  if (state === 'RUNNING') return '继续观察执行耗时和结果产出。'
  if (state === 'FAILED') return '优先排查失败原因，再决定是否重试。'
  return '结果已经产出，可以转入发现确认和资产处置。'
}

const findingAction = (status: string) => {
  if (status === 'NEW') return '建议先确认真实性并绑定责任资产。'
  if (status === 'CONFIRMED') return '进入修复或缓解排期。'
  if (status === 'FIXED') return '保持复测，确认问题已真正关闭。'
  return '结合资产上下文确认是否继续跟进。'
}

const formatTime = (value: string) => new Date(value).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })

onMounted(loadAll)
</script>
