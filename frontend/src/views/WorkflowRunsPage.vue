<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1600px] space-y-6">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold tracking-tight">流程运行监控</h1>
          <p class="text-sm text-muted-foreground">查看 workflow run 状态、耗时、失败率和节点级时间线，并支持 trace_id 跳转审计链路。</p>
        </div>
        <div class="flex flex-wrap items-center gap-2">
          <Button variant="outline" size="sm" class="cursor-pointer" @click="router.push('/workflow/catalog')">
            返回目录
          </Button>
          <Button variant="outline" size="sm" class="cursor-pointer" :disabled="loading" @click="loadRuns">
            {{ loading ? '刷新中...' : '刷新' }}
          </Button>
        </div>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Card>
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">总运行数</p>
            <p class="text-2xl font-semibold text-foreground">{{ summary.total_runs }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">运行中</p>
            <p class="text-2xl font-semibold text-cyan-300">{{ summary.running_runs }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">成功</p>
            <p class="text-2xl font-semibold text-emerald-300">{{ summary.success_runs }}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">失败率</p>
            <p class="text-2xl font-semibold text-amber-300">{{ summary.failure_rate.toFixed(2) }}%</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">平均耗时</p>
            <p class="text-2xl font-semibold text-foreground">{{ formatDuration(summary.avg_duration_ms) }}</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardContent class="pt-5">
          <div class="grid gap-3 xl:grid-cols-[1.2fr_1fr_180px_160px]">
            <input
              v-model="filters.keyword"
              type="text"
              placeholder="按 workflow_key / trace_id / trigger_ref 检索"
              class="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              @keyup.enter="search"
            />
            <input
              v-model="filters.workflow_key"
              type="text"
              placeholder="限定 workflow_key"
              class="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              @keyup.enter="search"
            />
            <select
              v-model="filters.run_state"
              class="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">全部状态</option>
              <option v-for="state in stateOptions" :key="state" :value="state">{{ state }}</option>
            </select>
            <div class="flex gap-2">
              <Button size="sm" class="cursor-pointer flex-1" :disabled="loading" @click="search">
                {{ loading ? '加载中...' : '查询' }}
              </Button>
              <Button variant="outline" size="sm" class="cursor-pointer" :disabled="loading" @click="resetFilters">
                重置
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      <div class="grid gap-6 xl:grid-cols-[minmax(0,1.2fr)_minmax(360px,0.8fr)]">
        <Card>
          <CardHeader class="flex-row items-center justify-between">
            <CardTitle class="text-base">运行列表</CardTitle>
            <span class="text-xs text-muted-foreground">共 {{ total }} 条</span>
          </CardHeader>
          <CardContent class="p-0">
            <div v-if="errorText" class="border-t border-border bg-destructive/5 px-4 py-3 text-xs text-destructive">
              {{ errorText }}
            </div>

            <div v-if="loading" class="space-y-2 p-4">
              <Skeleton v-for="index in 6" :key="index" class="h-14 w-full rounded-md" />
            </div>

            <div v-else-if="items.length === 0" class="px-4 py-16 text-center text-sm text-muted-foreground">
              暂无流程运行记录。
            </div>

            <div v-else class="overflow-x-auto">
              <table class="w-full text-sm">
                <thead>
                  <tr class="border-b border-border bg-muted/20">
                    <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground">流程</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground">状态</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground">版本</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground">耗时</th>
                    <th class="px-4 py-3 text-left text-xs font-medium text-muted-foreground">trace_id</th>
                    <th class="px-4 py-3 text-right text-xs font-medium text-muted-foreground">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="item in items"
                    :key="item.run_id"
                    class="cursor-pointer border-b border-border/60 hover:bg-muted/20"
                    :class="item.run_id === selectedRunId ? 'bg-primary/5' : ''"
                    @click="selectRun(item.run_id)"
                  >
                    <td class="px-4 py-3 align-top">
                      <div class="space-y-1">
                        <p class="font-medium text-foreground">{{ item.workflow_name }}</p>
                        <p class="font-mono text-xs text-muted-foreground">{{ item.workflow_key }}</p>
                        <p class="text-xs text-muted-foreground">{{ item.trigger_ref || '--' }}</p>
                      </div>
                    </td>
                    <td class="px-4 py-3 align-top">
                      <Badge class="text-[10px]" :class="stateClass(item.run_state)">
                        {{ item.run_state }}
                      </Badge>
                      <p v-if="item.latest_error_message" class="mt-2 max-w-[240px] text-xs text-destructive line-clamp-2">
                        {{ item.latest_error_message }}
                      </p>
                    </td>
                    <td class="px-4 py-3 align-top text-xs text-muted-foreground">
                      v{{ item.workflow_version }}
                    </td>
                    <td class="px-4 py-3 align-top text-xs text-muted-foreground">
                      {{ formatDuration(item.duration_ms) }}
                    </td>
                    <td class="px-4 py-3 align-top">
                      <button
                        type="button"
                        class="max-w-[180px] truncate text-left font-mono text-xs text-primary hover:underline"
                        @click.stop="jumpToAudit(item.trace_id)"
                      >
                        {{ item.trace_id || '--' }}
                      </button>
                    </td>
                    <td class="px-4 py-3 align-top text-right">
                      <Button variant="outline" size="sm" class="h-8 cursor-pointer" @click.stop="selectRun(item.run_id)">
                        查看时间线
                      </Button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>

            <div v-if="totalPages > 1" class="flex items-center justify-between border-t border-border px-4 py-3">
              <span class="text-xs text-muted-foreground">第 {{ page }} / {{ totalPages }} 页</span>
              <div class="flex gap-2">
                <Button variant="outline" size="sm" class="h-8 cursor-pointer" :disabled="page <= 1 || loading" @click="changePage(page - 1)">
                  上一页
                </Button>
                <Button variant="outline" size="sm" class="h-8 cursor-pointer" :disabled="page >= totalPages || loading" @click="changePage(page + 1)">
                  下一页
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader class="flex-row items-center justify-between">
            <CardTitle class="text-base">节点时间线</CardTitle>
            <div class="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                class="h-8 cursor-pointer"
                :disabled="debugLoading || !selectedRunId"
                @click="reloadDebugReport"
              >
                {{ debugLoading ? '生成中...' : '调试报告' }}
              </Button>
              <Button
                v-if="canReplayWorkflow"
                variant="outline"
                size="sm"
                class="h-8 cursor-pointer"
                :disabled="replayLoading || !selectedRunId"
                @click="runReplay('full')"
              >
                {{ replayLoading ? '执行中...' : '完整重放' }}
              </Button>
              <Button
                v-if="canReplayWorkflow"
                variant="outline"
                size="sm"
                class="h-8 cursor-pointer"
                :disabled="replayLoading || !selectedRunId || !debugReport?.replay_hints.resume_supported"
                @click="runReplay('resume_from_failure')"
              >
                从失败节点继续
              </Button>
              <Button
                v-if="detail?.run.trace_id"
                variant="outline"
                size="sm"
                class="h-8 cursor-pointer"
                @click="jumpToAudit(detail.run.trace_id)"
              >
                trace 跳转
              </Button>
              <Button
                variant="outline"
                size="sm"
                class="h-8 cursor-pointer"
                :disabled="detailLoading || !selectedRunId"
                @click="reloadDetail"
              >
                {{ detailLoading ? '刷新中...' : '刷新详情' }}
              </Button>
            </div>
          </CardHeader>
          <CardContent class="space-y-4">
            <div v-if="detailErrorText" class="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {{ detailErrorText }}
            </div>

            <div v-if="replayErrorText" class="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
              {{ replayErrorText }}
            </div>

            <div v-if="replayFeedback" class="rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-300">
              {{ replayFeedback }}
            </div>

            <div v-if="detailLoading" class="space-y-3">
              <Skeleton class="h-24 w-full rounded-md" />
              <Skeleton class="h-28 w-full rounded-md" />
              <Skeleton class="h-28 w-full rounded-md" />
            </div>

            <div v-else-if="!detail" class="rounded-md border border-dashed border-border px-4 py-16 text-center text-sm text-muted-foreground">
              选择左侧运行记录后查看节点级时间线。
            </div>

            <template v-else>
              <div class="rounded-lg border border-border/70 bg-muted/10 p-4">
                <div class="grid gap-3 md:grid-cols-2">
                  <div class="space-y-1">
                    <p class="text-xs text-muted-foreground">流程</p>
                    <p class="font-medium text-foreground">{{ detail.run.workflow_name }}</p>
                    <p class="font-mono text-xs text-muted-foreground">{{ detail.run.workflow_key }}</p>
                  </div>
                  <div class="space-y-1">
                    <p class="text-xs text-muted-foreground">运行状态</p>
                    <Badge class="text-[10px]" :class="stateClass(detail.run.run_state)">
                      {{ detail.run.run_state }}
                    </Badge>
                  </div>
                  <div class="space-y-1">
                    <p class="text-xs text-muted-foreground">trace_id</p>
                    <p class="font-mono text-xs text-foreground break-all">{{ detail.run.trace_id || '--' }}</p>
                  </div>
                  <div class="space-y-1">
                    <p class="text-xs text-muted-foreground">时长 / 版本</p>
                    <p class="text-sm text-foreground">{{ formatDuration(detail.run.duration_ms) }} / v{{ detail.run.workflow_version }}</p>
                  </div>
                </div>
                <div class="mt-4 grid gap-3">
                  <div>
                    <p class="text-xs text-muted-foreground">上下文摘要</p>
                    <p class="mt-1 text-xs text-foreground break-all">{{ detail.run.context_summary || '--' }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-muted-foreground">输入摘要</p>
                    <p class="mt-1 text-xs text-foreground break-all">{{ detail.run.input_summary || '--' }}</p>
                  </div>
                  <div>
                    <p class="text-xs text-muted-foreground">输出摘要</p>
                    <p class="mt-1 text-xs text-foreground break-all">{{ detail.run.output_summary || '--' }}</p>
                  </div>
                </div>
              </div>

              <div v-if="canReplayWorkflow" class="rounded-lg border border-border/70 bg-card/80 p-4">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-foreground">参数覆盖 / 手工修复</p>
                    <p class="text-xs text-muted-foreground">输入 JSON 后可执行完整重放，或在失败节点基础上继续执行。</p>
                  </div>
                  <span class="text-xs text-muted-foreground">JSON Object</span>
                </div>
                <textarea
                  v-model="overridesText"
                  rows="6"
                  class="mt-3 w-full rounded-md border border-input bg-background px-3 py-2 font-mono text-xs shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
                  placeholder='{"ip":"8.8.8.8"}'
                />
              </div>

              <div class="space-y-3">
                <div
                  v-for="step in detail.steps"
                  :key="`${step.id}-${step.attempt}`"
                  class="rounded-lg border border-border/70 bg-card/80 p-4"
                >
                  <div class="flex flex-col gap-2 md:flex-row md:items-start md:justify-between">
                    <div class="space-y-1">
                      <div class="flex items-center gap-2">
                        <p class="font-medium text-foreground">{{ step.node_id }}</p>
                        <Badge class="text-[10px]" :class="stateClass(step.step_state)">
                          {{ step.step_state }}
                        </Badge>
                      </div>
                      <p class="font-mono text-xs text-muted-foreground">{{ step.node_type }} · attempt {{ step.attempt }}</p>
                    </div>
                    <div class="text-right text-xs text-muted-foreground">
                      <p>{{ formatDuration(step.duration_ms) }}</p>
                      <button
                        type="button"
                        class="font-mono text-primary hover:underline"
                        @click="jumpToAudit(step.trace_id)"
                      >
                        {{ step.trace_id || '--' }}
                      </button>
                    </div>
                  </div>

                  <div class="mt-3 grid gap-3">
                    <div>
                      <p class="text-xs text-muted-foreground">输入摘要</p>
                      <p class="mt-1 text-xs text-foreground break-all">{{ step.input_summary || '--' }}</p>
                    </div>
                    <div>
                      <p class="text-xs text-muted-foreground">输出摘要</p>
                      <p class="mt-1 text-xs text-foreground break-all">{{ step.output_summary || '--' }}</p>
                    </div>
                    <div v-if="step.error_message">
                      <p class="text-xs text-muted-foreground">错误信息</p>
                      <p class="mt-1 text-xs text-destructive break-all">{{ step.error_message }}</p>
                    </div>
                  </div>
                </div>
              </div>

              <div class="rounded-lg border border-border/70 bg-card/80 p-4">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-medium text-foreground">调试报告</p>
                    <p class="text-xs text-muted-foreground">失败原因、推荐修复动作、最近节点摘要和续跑候选节点。</p>
                  </div>
                  <Badge class="text-[10px]" :class="stateClass(debugReport?.source_run.run_state)">
                    {{ debugReport?.source_run.run_state || 'UNKNOWN' }}
                  </Badge>
                </div>

                <div v-if="debugLoading" class="mt-3 space-y-2">
                  <Skeleton class="h-20 w-full rounded-md" />
                  <Skeleton class="h-24 w-full rounded-md" />
                </div>

                <div v-else-if="!debugReport" class="mt-3 rounded-md border border-dashed border-border px-4 py-10 text-center text-sm text-muted-foreground">
                  暂无调试报告，点击上方按钮生成。
                </div>

                <div v-else class="mt-4 space-y-4">
                  <div class="grid gap-3 md:grid-cols-2">
                    <div class="space-y-1">
                      <p class="text-xs text-muted-foreground">续跑候选节点</p>
                      <p class="font-mono text-xs text-foreground">{{ debugReport.resume_candidate.node_id || '--' }}</p>
                      <p class="text-xs text-muted-foreground">{{ debugReport.resume_candidate.node_type || '--' }} / {{ debugReport.resume_candidate.step_state || '--' }}</p>
                    </div>
                    <div class="space-y-1">
                      <p class="text-xs text-muted-foreground">最近错误</p>
                      <p class="text-xs text-destructive break-all">{{ debugReport.replay_hints.last_error || '--' }}</p>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs text-muted-foreground">建议修复项</p>
                    <div class="mt-2 space-y-2">
                      <div
                        v-for="(item, index) in debugReport.recommendations"
                        :key="`${index}-${item}`"
                        class="rounded-md border border-border/60 bg-muted/10 px-3 py-2 text-xs text-foreground"
                      >
                        {{ item }}
                      </div>
                    </div>
                  </div>

                  <div>
                    <p class="text-xs text-muted-foreground">最近节点摘要</p>
                    <div class="mt-2 space-y-2">
                      <div
                        v-for="item in debugReport.latest_steps"
                        :key="`${item.node_id}-${item.attempt}`"
                        class="rounded-md border border-border/60 bg-muted/10 px-3 py-2"
                      >
                        <div class="flex items-center justify-between gap-2">
                          <p class="font-mono text-xs text-foreground">{{ item.node_id }}</p>
                          <Badge class="text-[10px]" :class="stateClass(item.step_state)">
                            {{ item.step_state }}
                          </Badge>
                        </div>
                        <p class="mt-2 text-xs text-muted-foreground">输入：{{ item.input_summary || '--' }}</p>
                        <p class="mt-1 text-xs text-muted-foreground">输出：{{ item.output_summary || '--' }}</p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </template>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  workflowApi,
  type WorkflowDebugReport,
  type WorkflowRunDetailResult,
  type WorkflowRunItem,
  type WorkflowReplayPayload,
  type WorkflowRunSummary,
} from '@/api/workflow'
import { getRequestErrorMessage } from '@/api/client'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { hasPermission } from '@/composables/useAuthz'

const router = useRouter()
const route = useRoute()
const pageSize = 12
const stateOptions = ['QUEUED', 'RUNNING', 'RETRYING', 'SUCCESS', 'FAILED', 'MANUAL_REQUIRED', 'CANCELLED']
const canReplayWorkflow = computed(() => hasPermission('workflow_edit'))

const emptySummary = (): WorkflowRunSummary => ({
  total_runs: 0,
  queued_runs: 0,
  running_runs: 0,
  success_runs: 0,
  failed_runs: 0,
  manual_required_runs: 0,
  cancelled_runs: 0,
  failure_rate: 0,
  avg_duration_ms: 0,
})

const loading = ref(false)
const detailLoading = ref(false)
const debugLoading = ref(false)
const replayLoading = ref(false)
const errorText = ref('')
const detailErrorText = ref('')
const replayErrorText = ref('')
const replayFeedback = ref('')
const page = ref(1)
const total = ref(0)
const items = ref<WorkflowRunItem[]>([])
const summary = ref<WorkflowRunSummary>(emptySummary())
const selectedRunId = ref<number | null>(null)
const detail = ref<WorkflowRunDetailResult | null>(null)
const debugReport = ref<WorkflowDebugReport | null>(null)
const overridesText = ref('{}')

const filters = reactive({
  keyword: '',
  workflow_key: '',
  run_state: '',
})

const totalPages = computed(() => {
  const pages = Math.ceil(total.value / pageSize)
  return pages > 0 ? pages : 1
})

const stateClass = (state?: string | null) => {
  const normalized = String(state || '').toUpperCase()
  if (normalized === 'SUCCESS') return 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300'
  if (normalized === 'RUNNING' || normalized === 'RETRYING') return 'border-cyan-500/30 bg-cyan-500/12 text-cyan-300'
  if (normalized === 'FAILED' || normalized === 'MANUAL_REQUIRED' || normalized === 'CANCELLED') {
    return 'border-rose-500/30 bg-rose-500/12 text-rose-300'
  }
  return 'border-amber-500/30 bg-amber-500/12 text-amber-300'
}

const formatDuration = (value: number | null | undefined) => {
  if (value == null || !Number.isFinite(value)) return '--'
  if (value < 1000) return `${value}ms`
  if (value < 60_000) return `${(value / 1000).toFixed(1)}s`
  return `${(value / 60_000).toFixed(1)}m`
}

const changePage = (nextPage: number) => {
  page.value = nextPage
  loadRuns()
}

const jumpToAudit = (traceId?: string | null) => {
  const trace = (traceId || '').trim()
  if (!trace) return
  router.push({ path: '/audit', query: { trace_id: trace } })
}

const parseOverrides = (): Record<string, unknown> => {
  const text = overridesText.value.trim()
  if (!text) return {}
  const parsed = JSON.parse(text)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('参数覆盖必须是 JSON 对象')
  }
  return parsed as Record<string, unknown>
}

const loadDebugReport = async (runId: number) => {
  debugLoading.value = true
  try {
    debugReport.value = await workflowApi.getWorkflowDebugReport(runId)
  } catch (error) {
    debugReport.value = null
    replayErrorText.value = getRequestErrorMessage(error, '加载调试报告失败')
  } finally {
    debugLoading.value = false
  }
}

const loadDetail = async (runId: number) => {
  detailLoading.value = true
  detailErrorText.value = ''
  replayErrorText.value = ''
  try {
    detail.value = await workflowApi.getWorkflowRunDetail(runId)
    await loadDebugReport(runId)
  } catch (error) {
    detail.value = null
    debugReport.value = null
    detailErrorText.value = getRequestErrorMessage(error, '加载运行详情失败')
  } finally {
    detailLoading.value = false
  }
}

const selectRun = async (runId: number) => {
  selectedRunId.value = runId
  await router.replace({ query: { ...route.query, run_id: String(runId) } })
  await loadDetail(runId)
}

const syncSelection = async () => {
  const queryRunId = Number(route.query.run_id)
  if (Number.isFinite(queryRunId) && queryRunId > 0) {
    selectedRunId.value = queryRunId
    await loadDetail(queryRunId)
    return
  }
  if (items.value.length > 0) {
    await selectRun(items.value[0].run_id)
    return
  }
  selectedRunId.value = null
  detail.value = null
  debugReport.value = null
}

const loadRuns = async () => {
  loading.value = true
  errorText.value = ''
  try {
    const data = await workflowApi.getWorkflowRuns({
      page: page.value,
      page_size: pageSize,
      keyword: filters.keyword.trim() || undefined,
      workflow_key: filters.workflow_key.trim() || undefined,
      run_state: filters.run_state || undefined,
    })
    items.value = data.items
    total.value = data.total
    summary.value = data.summary
    const exists = selectedRunId.value != null && items.value.some((item) => item.run_id === selectedRunId.value)
    if (!exists) {
      await syncSelection()
    }
  } catch (error) {
    items.value = []
    total.value = 0
    summary.value = emptySummary()
    detail.value = null
    debugReport.value = null
    errorText.value = getRequestErrorMessage(error, '加载运行监控失败')
  } finally {
    loading.value = false
  }
}

const reloadDetail = async () => {
  if (!selectedRunId.value) return
  await loadDetail(selectedRunId.value)
}

const reloadDebugReport = async () => {
  if (!selectedRunId.value) return
  replayErrorText.value = ''
  await loadDebugReport(selectedRunId.value)
}

const runReplay = async (mode: WorkflowReplayPayload['mode']) => {
  if (!selectedRunId.value) return
  replayLoading.value = true
  replayErrorText.value = ''
  replayFeedback.value = ''
  try {
    const overrides = parseOverrides()
    const result = await workflowApi.replayWorkflowRun(selectedRunId.value, { mode, overrides })
    replayFeedback.value = `已创建回放 run #${result.replay_run_id}，状态：${result.replay_run_state}`
    debugReport.value = result.debug_report
    page.value = 1
    await loadRuns()
    await selectRun(result.replay_run_id)
  } catch (error) {
    replayErrorText.value = getRequestErrorMessage(error, '执行回放失败')
  } finally {
    replayLoading.value = false
  }
}

const search = () => {
  page.value = 1
  loadRuns()
}

const resetFilters = () => {
  filters.keyword = ''
  filters.workflow_key = ''
  filters.run_state = ''
  search()
}

watch(
  () => route.query.run_id,
  (value) => {
    const runId = Number(value)
    if (!Number.isFinite(runId) || runId <= 0 || runId === selectedRunId.value) return
    selectedRunId.value = runId
    loadDetail(runId)
  },
)

onMounted(loadRuns)
</script>
