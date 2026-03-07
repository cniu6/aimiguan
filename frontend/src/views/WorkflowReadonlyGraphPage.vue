<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1560px] space-y-6">
      <div class="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
        <div class="space-y-1">
          <h1 class="text-2xl font-semibold tracking-tight">流程只读图谱</h1>
          <p class="text-sm text-muted-foreground">展示节点状态、边条件、版本和发布时间，不提供编辑能力。</p>
        </div>
        <div class="flex gap-2">
          <Button variant="outline" size="sm" class="cursor-pointer" @click="router.push('/workflow/catalog')">
            返回目录
          </Button>
          <Button variant="outline" size="sm" class="cursor-pointer" :disabled="loading" @click="loadWorkflow">
            {{ loading ? '刷新中...' : '刷新' }}
          </Button>
        </div>
      </div>

      <div class="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card class="bg-card/80">
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">流程标识</p>
            <p class="text-sm font-mono text-foreground">{{ detail?.workflow.workflow_key || '--' }}</p>
          </CardContent>
        </Card>
        <Card class="bg-card/80">
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">版本信息</p>
            <p class="text-sm text-foreground">v{{ detail?.version.version ?? '--' }}</p>
          </CardContent>
        </Card>
        <Card class="bg-card/80">
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">流程状态</p>
            <Badge class="text-[10px]" :class="stateClass(detail?.workflow.definition_state)">
              {{ detail?.workflow.definition_state || '--' }}
            </Badge>
          </CardContent>
        </Card>
        <Card class="bg-card/80">
          <CardContent class="space-y-1 py-4">
            <p class="text-xs text-muted-foreground">发布时间</p>
            <p class="text-sm text-foreground">{{ formatDateTime(detail?.version.created_at || null) }}</p>
          </CardContent>
        </Card>
      </div>

      <div v-if="errorText" class="rounded-lg border border-destructive/40 bg-destructive/5 px-4 py-3 text-sm text-destructive">
        {{ errorText }}
      </div>

      <div class="grid gap-4 xl:grid-cols-[1fr_320px]">
        <Card class="overflow-hidden">
          <CardHeader class="border-b border-border/60 pb-3">
            <CardTitle class="text-base">
              {{ detail?.workflow.name || 'Workflow Graph' }}
            </CardTitle>
            <p class="text-xs text-muted-foreground">
              {{ detail?.workflow.description || '无描述。' }}
            </p>
          </CardHeader>
          <CardContent class="p-0">
            <div v-if="loading" class="grid h-[620px] place-items-center text-sm text-muted-foreground">加载图谱中...</div>
            <div v-else-if="!detail" class="grid h-[620px] place-items-center text-sm text-muted-foreground">暂无图谱数据。</div>
            <div v-else class="h-[620px] bg-muted/10">
              <VueFlow
                :nodes="flowNodes"
                :edges="flowEdges"
                fit-view-on-init
                :nodes-draggable="false"
                :nodes-connectable="false"
                :elements-selectable="true"
                :zoom-on-double-click="false"
                :min-zoom="0.3"
                :max-zoom="1.6"
                @node-click="onNodeClick"
              >
                <Background :gap="24" :size="1" pattern-color="rgba(148, 163, 184, 0.25)" />
                <Controls />

                <template #node-default="{ data }">
                  <div class="workflow-node">
                    <p class="workflow-node-title">{{ data.name }}</p>
                    <p class="workflow-node-type">{{ data.type }}</p>
                    <p class="workflow-node-status">{{ data.status }}</p>
                  </div>
                </template>
              </VueFlow>
            </div>
          </CardContent>
        </Card>

        <div class="space-y-4">
          <Card>
            <CardHeader class="pb-2">
              <CardTitle class="text-base">节点详情</CardTitle>
            </CardHeader>
            <CardContent class="space-y-3 text-sm">
              <div v-if="!selectedNode" class="text-muted-foreground">点击左侧节点查看详细配置。</div>
              <template v-else>
                <div class="space-y-1">
                  <p class="text-xs text-muted-foreground">节点 ID</p>
                  <p class="font-mono text-foreground">{{ selectedNode.id }}</p>
                </div>
                <div class="space-y-1">
                  <p class="text-xs text-muted-foreground">节点名称</p>
                  <p>{{ selectedNode.name }}</p>
                </div>
                <div class="grid grid-cols-2 gap-3">
                  <div class="space-y-1">
                    <p class="text-xs text-muted-foreground">类型</p>
                    <p class="font-mono">{{ selectedNode.type }}</p>
                  </div>
                  <div class="space-y-1">
                    <p class="text-xs text-muted-foreground">超时</p>
                    <p>{{ selectedNode.timeout }}s</p>
                  </div>
                </div>
                <div class="space-y-1">
                  <p class="text-xs text-muted-foreground">节点状态</p>
                  <Badge class="text-[10px]" :class="stateClass(resolveNodeStatus(selectedNode))">
                    {{ resolveNodeStatus(selectedNode) }}
                  </Badge>
                </div>
                <div class="space-y-1">
                  <p class="text-xs text-muted-foreground">重试策略</p>
                  <p class="text-xs leading-6 text-muted-foreground">
                    max_retries={{ selectedNode.retry_policy.max_retries }},
                    backoff={{ selectedNode.retry_policy.backoff_seconds }}s x{{ selectedNode.retry_policy.backoff_multiplier }}
                  </p>
                </div>
              </template>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="pb-2">
              <CardTitle class="text-base">边条件</CardTitle>
            </CardHeader>
            <CardContent class="space-y-2">
              <div v-if="!detail?.dsl.edges.length" class="text-sm text-muted-foreground">无边定义。</div>
              <div
                v-for="(edge, index) in detail?.dsl.edges || []"
                :key="`${edge.from}-${edge.to}-${index}`"
                class="rounded-md border border-border/60 bg-muted/10 px-3 py-2"
              >
                <p class="text-xs text-foreground">
                  <span class="font-mono">{{ edge.from }}</span>
                  <span class="px-1 text-muted-foreground">→</span>
                  <span class="font-mono">{{ edge.to }}</span>
                </p>
                <p class="text-xs text-muted-foreground">条件：{{ edge.condition }} · priority={{ edge.priority }}</p>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader class="pb-2">
              <CardTitle class="text-base">trace 追踪入口</CardTitle>
            </CardHeader>
            <CardContent class="space-y-2">
              <p class="text-xs text-muted-foreground">流程上下文 trace_id 模板：{{ detail?.dsl.context.trace_id || '--' }}</p>
              <input
                v-model="traceIdInput"
                type="text"
                placeholder="输入本次执行 trace_id"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <Button
                variant="outline"
                size="sm"
                class="w-full cursor-pointer"
                :disabled="!traceIdInput.trim()"
                @click="jumpToAudit"
              >
                跳转审计链路
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { MarkerType, Position, VueFlow, type Edge, type Node, type NodeMouseEvent } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { workflowApi, type WorkflowDetailResult, type WorkflowNode } from '@/api/workflow'
import { getRequestErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

interface ReadonlyFlowNodeData {
  name: string
  type: string
  status: string
}

type PositionedWorkflowNode = WorkflowNode & {
  position: {
    x: number
    y: number
  }
}

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const errorText = ref('')
const detail = ref<WorkflowDetailResult | null>(null)
const selectedNodeId = ref<string>('')
const traceIdInput = ref('')

const workflowId = computed(() => Number(route.params.id))

const stateClass = (state?: string | null) => {
  if (state === 'PUBLISHED') return 'border-cyan-500/30 bg-cyan-500/12 text-cyan-300'
  if (state === 'VALIDATED' || state === 'SUCCESS') return 'border-emerald-500/30 bg-emerald-500/12 text-emerald-300'
  if (state === 'RUNNING') return 'border-blue-500/30 bg-blue-500/12 text-blue-300'
  if (state === 'FAILED' || state === 'CANCELLED') return 'border-red-500/30 bg-red-500/12 text-red-300'
  if (state === 'MANUAL_REQUIRED') return 'border-amber-500/30 bg-amber-500/12 text-amber-300'
  if (state === 'ARCHIVED') return 'border-slate-500/30 bg-slate-500/12 text-slate-300'
  return 'border-amber-500/30 bg-amber-500/12 text-amber-300'
}

const formatDateTime = (value: string | null) => {
  if (!value) return '--'
  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const resolveNodeStatus = (node: WorkflowNode): string => {
  const raw = node.config?.status
  if (typeof raw === 'string' && raw.trim()) return raw.trim().toUpperCase()
  if (detail.value?.dsl.status) return detail.value.dsl.status
  return 'DRAFT'
}

const layoutNodes = (nodes: WorkflowNode[], edges: WorkflowDetailResult['dsl']['edges']): PositionedWorkflowNode[] => {
  const incomingCount = new Map<string, number>()
  const graph = new Map<string, string[]>()

  nodes.forEach((node) => {
    incomingCount.set(node.id, 0)
    graph.set(node.id, [])
  })

  edges.forEach((edge) => {
    if (!incomingCount.has(edge.to) || !graph.has(edge.from)) return
    incomingCount.set(edge.to, (incomingCount.get(edge.to) || 0) + 1)
    graph.get(edge.from)?.push(edge.to)
  })

  const queue: Array<{ id: string; layer: number }> = []
  incomingCount.forEach((count, id) => {
    if (count === 0) queue.push({ id, layer: 0 })
  })

  const layerMap = new Map<string, number>()
  while (queue.length) {
    const current = queue.shift()
    if (!current) break
    layerMap.set(current.id, current.layer)
    const nextNodes = graph.get(current.id) || []
    nextNodes.forEach((nextId) => {
      const nextCount = (incomingCount.get(nextId) || 0) - 1
      incomingCount.set(nextId, nextCount)
      if (nextCount === 0) {
        queue.push({ id: nextId, layer: current.layer + 1 })
      }
    })
  }

  nodes.forEach((node, index) => {
    if (!layerMap.has(node.id)) {
      layerMap.set(node.id, Math.floor(index / 3))
    }
  })

  const grouped = new Map<number, WorkflowNode[]>()
  nodes.forEach((node) => {
    const layer = layerMap.get(node.id) || 0
    const bucket = grouped.get(layer) || []
    bucket.push(node)
    grouped.set(layer, bucket)
  })

  return nodes.map((node) => {
    const layer = layerMap.get(node.id) || 0
    const bucket = grouped.get(layer) || []
    const indexInLayer = bucket.findIndex((item) => item.id === node.id)
    return {
      ...node,
      position: {
        x: 100 + layer * 300,
        y: 80 + Math.max(indexInLayer, 0) * 145,
      },
    }
  })
}

const flowNodes = computed<Node<ReadonlyFlowNodeData>[]>(() => {
  if (!detail.value) return []
  const positionedNodes = layoutNodes(detail.value.dsl.nodes, detail.value.dsl.edges)
  return positionedNodes.map((node): Node<ReadonlyFlowNodeData> => ({
    id: node.id,
    type: 'default',
    position: node.position,
    data: {
      name: node.name,
      type: node.type,
      status: resolveNodeStatus(node),
    },
    draggable: false,
    selectable: true,
    sourcePosition: Position.Right,
    targetPosition: Position.Left,
  }))
})

const flowEdges = computed<Edge[]>(() => {
  if (!detail.value) return []
  return detail.value.dsl.edges.map((edge, index) => ({
    id: `edge-${index}-${edge.from}-${edge.to}`,
    source: edge.from,
    target: edge.to,
    label: edge.condition,
    markerEnd: MarkerType.ArrowClosed,
    animated: false,
    style: { stroke: 'rgba(148, 163, 184, 0.72)', strokeWidth: 1.2 },
    labelStyle: {
      fill: 'rgba(226, 232, 240, 0.92)',
      fontSize: '11px',
      fontWeight: 500,
    },
    labelBgStyle: {
      fill: 'rgba(15, 23, 42, 0.82)',
      fillOpacity: 0.95,
    },
    labelBgPadding: [6, 3],
    labelBgBorderRadius: 4,
  }))
})

const selectedNode = computed(() => {
  if (!detail.value || !selectedNodeId.value) return null
  return detail.value.dsl.nodes.find((node) => node.id === selectedNodeId.value) || null
})

const onNodeClick = (event: NodeMouseEvent) => {
  if (!event.node?.id) return
  selectedNodeId.value = event.node.id
}

const loadWorkflow = async () => {
  if (!Number.isFinite(workflowId.value) || workflowId.value <= 0) {
    errorText.value = '无效的 workflow_id。'
    detail.value = null
    return
  }

  loading.value = true
  errorText.value = ''
  try {
    const data = await workflowApi.getWorkflowDetail(workflowId.value)
    detail.value = data
    selectedNodeId.value = data.dsl.nodes[0]?.id || ''
    const traceTemplate = data.dsl.context.trace_id || ''
    traceIdInput.value = traceTemplate.includes('{{') ? '' : traceTemplate
  } catch (error) {
    detail.value = null
    selectedNodeId.value = ''
    errorText.value = getRequestErrorMessage(error, '加载流程图谱失败')
  } finally {
    loading.value = false
  }
}

const jumpToAudit = () => {
  const traceId = traceIdInput.value.trim()
  if (!traceId) return
  router.push({ path: '/audit', query: { trace_id: traceId } })
}

watch(() => route.params.id, () => {
  loadWorkflow()
}, { immediate: true })
</script>

<style scoped>
.workflow-node {
  min-width: 180px;
  max-width: 230px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.9), rgba(2, 6, 23, 0.95));
  box-shadow: 0 8px 24px rgba(2, 6, 23, 0.35);
  padding: 10px 12px;
}

.workflow-node-title {
  color: rgba(241, 245, 249, 0.95);
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
}

.workflow-node-type {
  margin-top: 4px;
  color: rgba(148, 163, 184, 0.9);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  font-size: 11px;
}

.workflow-node-status {
  margin-top: 6px;
  color: rgba(34, 211, 238, 0.92);
  font-size: 10px;
  letter-spacing: 0.04em;
}
</style>
