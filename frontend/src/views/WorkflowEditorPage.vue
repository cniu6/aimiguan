<template>
  <div class="flex h-[calc(100vh-56px)] overflow-hidden">
    <!-- Left: Canvas -->
    <div class="relative flex-1">
      <!-- Top toolbar -->
      <div class="absolute left-0 right-0 top-0 z-10 flex items-center justify-between border-b border-border/60 bg-background/95 px-4 py-2 backdrop-blur-sm">
        <div class="flex items-center gap-3">
          <Button variant="ghost" size="sm" class="cursor-pointer gap-1" @click="goBack">
            <ArrowLeft class="h-4 w-4" /> 返回
          </Button>
          <Separator orientation="vertical" class="h-5" />
          <div class="flex items-center gap-2">
            <input
              v-model="workflowName"
              class="h-7 w-48 rounded border border-input bg-transparent px-2 text-sm font-medium focus:outline-none focus:ring-1 focus:ring-ring"
              placeholder="流程名称"
              @input="markDirty"
            />
            <Badge class="border-sky-500/30 bg-sky-500/12 text-sky-300 text-[10px]">{{ definitionState }}</Badge>
            <Badge v-if="publishedVersion" class="border-cyan-500/30 bg-cyan-500/12 text-cyan-300 text-[10px]">发布 v{{ publishedVersion }}</Badge>
            <Badge v-if="isDirty" class="border-amber-500/30 bg-amber-500/12 text-amber-300 text-[10px]">未保存</Badge>
            <Badge v-if="autoSaveStatus" class="border-emerald-500/30 bg-emerald-500/12 text-emerald-300 text-[10px]">{{ autoSaveStatus }}</Badge>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <Button variant="outline" size="sm" class="cursor-pointer gap-1" @click="addNode('action')">
            <Plus class="h-3.5 w-3.5" /> 动作
          </Button>
          <Button variant="outline" size="sm" class="cursor-pointer gap-1" @click="addNode('condition')">
            <GitBranch class="h-3.5 w-3.5" /> 条件
          </Button>
          <Button variant="outline" size="sm" class="cursor-pointer gap-1" @click="addNode('trigger')">
            <Zap class="h-3.5 w-3.5" /> 触发器
          </Button>
          <Button variant="outline" size="sm" class="cursor-pointer gap-1" @click="addNode('notification')">
            <Bell class="h-3.5 w-3.5" /> 通知
          </Button>
          <Button variant="outline" size="sm" class="cursor-pointer gap-1" @click="addNode('approval')">
            <ShieldCheck class="h-3.5 w-3.5" /> 审批
          </Button>
          <Separator orientation="vertical" class="h-5" />
          <Button variant="outline" size="sm" class="cursor-pointer" :disabled="saving" @click="saveDraft">
            <Save class="mr-1 h-3.5 w-3.5" /> {{ saving ? '保存中...' : '保存草稿' }}
          </Button>
          <Button variant="default" size="sm" class="cursor-pointer" :disabled="saving" @click="validateDraft">
            <CheckCircle class="mr-1 h-3.5 w-3.5" /> 校验
          </Button>
          <Button v-if="canPublishWorkflow" variant="default" size="sm" class="cursor-pointer" :disabled="saving || publishing" @click="openPublishDialog">
            <ShieldCheck class="mr-1 h-3.5 w-3.5" /> {{ publishing ? '发布中...' : '发布' }}
          </Button>
          <Button v-if="canRollbackWorkflow" variant="outline" size="sm" class="cursor-pointer" :disabled="saving || rollingBack" @click="openRollbackDialog">
            <ArrowLeft class="mr-1 h-3.5 w-3.5" /> {{ rollingBack ? '回滚中...' : '回滚' }}
          </Button>
        </div>
      </div>

      <!-- VueFlow Canvas -->
      <div class="h-full pt-[49px]">
        <VueFlow
          v-model:nodes="flowNodesModel"
          v-model:edges="flowEdgesModel"
          :nodes-draggable="true"
          :nodes-connectable="true"
          :elements-selectable="true"
          :snap-to-grid="true"
          :snap-grid="[20, 20]"
          :min-zoom="0.2"
          :max-zoom="2"
          :default-viewport="{ x: 60, y: 40, zoom: 0.85 }"
          :connection-mode="ConnectionMode.Loose"
          @node-click="onNodeClick"
          @edge-click="onEdgeClick"
          @connect="onConnect"
          @nodes-change="onNodesChange"
          @edges-change="onEdgesChange"
          @pane-click="onPaneClick"
        >
          <Background :gap="20" :size="1" pattern-color="rgba(148,163,184,0.18)" />
          <Controls />

          <template #node-custom="nodeProps">
            <div
              class="editor-node"
              :class="[
                `editor-node--${nodeProps.data.nodeType}`,
                { 'editor-node--selected': nodeProps.selected }
              ]"
            >
              <div class="editor-node__header">
                <component :is="nodeTypeIcon(nodeProps.data.nodeType)" class="h-3.5 w-3.5 shrink-0" />
                <span class="truncate text-xs font-semibold">{{ nodeProps.data.label }}</span>
              </div>
              <p class="editor-node__type">{{ nodeProps.data.nodeType }}</p>
              <div class="editor-node__handles">
                <Handle type="target" :position="Position.Left" class="!bg-slate-400" />
                <Handle type="source" :position="Position.Right" class="!bg-cyan-400" />
              </div>
            </div>
          </template>

          <NodeToolbar v-if="selectedNodeId" :node-id="selectedNodeId" :position="Position.Top" :offset="8">
            <div class="flex gap-1 rounded-lg border border-border/60 bg-background/95 p-1 shadow-lg backdrop-blur-sm">
              <Button variant="ghost" size="sm" class="h-7 w-7 cursor-pointer p-0" title="复制节点" @click="duplicateNode(selectedNodeId)">
                <Copy class="h-3.5 w-3.5" />
              </Button>
              <Button variant="ghost" size="sm" class="h-7 w-7 cursor-pointer p-0 text-destructive hover:text-destructive" title="删除节点" @click="removeNode(selectedNodeId)">
                <Trash2 class="h-3.5 w-3.5" />
              </Button>
            </div>
          </NodeToolbar>
        </VueFlow>
      </div>

      <!-- Error toast area -->
      <div v-if="errorText" class="absolute bottom-4 left-4 right-4 z-20 rounded-lg border border-destructive/40 bg-destructive/10 px-4 py-3 text-sm text-destructive backdrop-blur-sm">
        {{ errorText }}
        <button class="ml-2 underline" @click="errorText = ''">dismiss</button>
      </div>
      <div v-if="successText" class="absolute bottom-4 left-4 right-4 z-20 rounded-lg border border-emerald-500/40 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300 backdrop-blur-sm">
        {{ successText }}
        <button class="ml-2 underline" @click="successText = ''">dismiss</button>
      </div>
    </div>

    <!-- Right: Property Panel -->
    <div class="w-[380px] shrink-0 overflow-y-auto border-l border-border/60 bg-card/60">
      <Tabs v-model="activeTab" class="h-full">
        <TabsList class="w-full rounded-none border-b border-border/60">
          <TabsTrigger value="properties" class="flex-1 cursor-pointer text-xs">节点属性</TabsTrigger>
          <TabsTrigger value="edges" class="flex-1 cursor-pointer text-xs">边/条件</TabsTrigger>
          <TabsTrigger value="json" class="flex-1 cursor-pointer text-xs">JSON</TabsTrigger>
        </TabsList>

        <TabsContent value="properties" class="p-4">
          <div v-if="!editingNodeState" class="py-8 text-center text-sm text-muted-foreground">
            点击画布中的节点查看和编辑属性。
          </div>
          <div v-else class="space-y-4">
            <div class="space-y-1.5">
              <label class="text-xs font-medium text-muted-foreground">节点 ID</label>
              <p class="rounded border border-border/40 bg-muted/20 px-2 py-1.5 font-mono text-xs text-foreground">{{ editingNodeId }}</p>
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-medium text-muted-foreground">节点名称</label>
              <input
                :value="editingNodeDataState.label"
                class="h-8 w-full rounded border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                @input="updateNodeLabel(editingNodeId, ($event.target as HTMLInputElement).value)"
              />
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-medium text-muted-foreground">节点类型</label>
              <Select :model-value="editingNodeDataState.nodeType" @update:model-value="(v) => updateNodeType(editingNodeId, String(v || 'action'))">
                <SelectTrigger class="h-8 text-xs">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="trigger">trigger</SelectItem>
                  <SelectItem value="condition">condition</SelectItem>
                  <SelectItem value="action">action</SelectItem>
                  <SelectItem value="notification">notification</SelectItem>
                  <SelectItem value="approval">approval</SelectItem>
                  <SelectItem value="ai">ai</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div class="space-y-1.5">
              <label class="text-xs font-medium text-muted-foreground">超时 (秒)</label>
              <input
                type="number"
                :value="editingNodeDataState.timeout"
                min="1"
                max="3600"
                class="h-8 w-full rounded border border-input bg-background px-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
                @input="updateNodeField(editingNodeId, 'timeout', Number(($event.target as HTMLInputElement).value) || 30)"
              />
            </div>

            <Separator />

            <p class="text-xs font-semibold text-muted-foreground">重试策略</p>
            <div class="grid grid-cols-2 gap-3">
              <div class="space-y-1">
                <label class="text-[10px] text-muted-foreground">max_retries</label>
                <input
                  type="number"
                  :value="editingNodeDataState.retryPolicy.max_retries"
                  min="0"
                  max="10"
                  class="h-7 w-full rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  @input="updateRetryField(editingNodeId, 'max_retries', Number(($event.target as HTMLInputElement).value) || 0)"
                />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-muted-foreground">backoff_seconds</label>
                <input
                  type="number"
                  :value="editingNodeDataState.retryPolicy.backoff_seconds"
                  min="1"
                  max="3600"
                  class="h-7 w-full rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  @input="updateRetryField(editingNodeId, 'backoff_seconds', Number(($event.target as HTMLInputElement).value) || 1)"
                />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-muted-foreground">backoff_multiplier</label>
                <input
                  type="number"
                  step="0.1"
                  :value="editingNodeDataState.retryPolicy.backoff_multiplier"
                  min="1"
                  max="5"
                  class="h-7 w-full rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  @input="updateRetryField(editingNodeId, 'backoff_multiplier', Number(($event.target as HTMLInputElement).value) || 1)"
                />
              </div>
              <div class="space-y-1">
                <label class="text-[10px] text-muted-foreground">retry_on (逗号分隔)</label>
                <input
                  :value="editingNodeDataState.retryPolicy.retry_on.join(', ')"
                  class="h-7 w-full rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  @input="updateRetryOn(editingNodeId, ($event.target as HTMLInputElement).value)"
                />
              </div>
            </div>

            <Separator />

            <div class="space-y-1.5">
              <div class="flex items-center justify-between">
                <label class="text-xs font-semibold text-muted-foreground">节点配置 (config)</label>
                <div class="flex items-center gap-2">
                  <label class="text-[10px] text-muted-foreground">JSON模式</label>
                  <Switch :checked="configJsonMode" @update:checked="configJsonMode = $event" />
                </div>
              </div>
              <div v-if="configJsonMode">
                <textarea
                  :value="configJsonText"
                  rows="8"
                  class="w-full rounded border border-input bg-background px-2 py-1.5 font-mono text-xs leading-5 focus:outline-none focus:ring-1 focus:ring-ring"
                  @input="onConfigJsonInput(editingNodeId, ($event.target as HTMLTextAreaElement).value)"
                />
                <p v-if="configJsonError" class="mt-1 text-[10px] text-destructive">{{ configJsonError }}</p>
              </div>
              <div v-else class="space-y-2">
                <div v-for="(val, key) in editingNodeDataState.config" :key="String(key)" class="flex items-center gap-2">
                  <span class="w-24 truncate font-mono text-[10px] text-muted-foreground">{{ key }}</span>
                  <input
                    :value="typeof val === 'string' ? val : JSON.stringify(val)"
                    class="h-7 flex-1 rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                    @input="updateConfigField(editingNodeId, String(key), ($event.target as HTMLInputElement).value)"
                  />
                  <button class="text-destructive hover:text-destructive/80" @click="removeConfigField(editingNodeId, String(key))">
                    <X class="h-3 w-3" />
                  </button>
                </div>
                <div class="flex items-center gap-2">
                  <input
                    v-model="newConfigKey"
                    placeholder="key"
                    class="h-7 w-24 rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <input
                    v-model="newConfigValue"
                    placeholder="value"
                    class="h-7 flex-1 rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                  />
                  <Button variant="ghost" size="sm" class="h-7 w-7 cursor-pointer p-0" :disabled="!newConfigKey.trim()" @click="addConfigField(editingNodeId)">
                    <Plus class="h-3 w-3" />
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="edges" class="p-4">
          <p class="mb-3 text-xs font-semibold text-muted-foreground">边条件编辑器</p>
          <div v-if="!edges.length" class="py-8 text-center text-sm text-muted-foreground">暂无边连接。在画布中拖拽节点端口进行连线。</div>
          <div v-else class="space-y-3">
            <div
              v-for="edge in edges"
              :key="edge.id"
              class="rounded-lg border border-border/60 p-3 transition-colors"
              :class="{ 'border-cyan-500/40 bg-cyan-500/5': selectedEdgeId === edge.id }"
              @click="selectedEdgeId = edge.id"
            >
              <div class="mb-2 flex items-center gap-1 text-xs">
                <span class="rounded bg-muted/30 px-1.5 py-0.5 font-mono text-[10px]">{{ edge.source }}</span>
                <ArrowRight class="h-3 w-3 text-muted-foreground" />
                <span class="rounded bg-muted/30 px-1.5 py-0.5 font-mono text-[10px]">{{ edge.target }}</span>
              </div>
              <div class="space-y-1.5">
                <div class="space-y-0.5">
                  <label class="text-[10px] text-muted-foreground">条件表达式</label>
                  <input
                    :value="(edge.data as any)?.condition ?? 'true'"
                    class="h-7 w-full rounded border border-input bg-background px-2 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                    placeholder="e.g. risk_score > 80"
                    @input="updateEdgeCondition(edge.id, ($event.target as HTMLInputElement).value)"
                  />
                </div>
                <div class="space-y-0.5">
                  <label class="text-[10px] text-muted-foreground">优先级</label>
                  <input
                    type="number"
                    :value="(edge.data as any)?.priority ?? 0"
                    min="0"
                    max="9999"
                    class="h-7 w-full rounded border border-input bg-background px-2 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
                    @input="updateEdgePriority(edge.id, Number(($event.target as HTMLInputElement).value) || 0)"
                  />
                </div>
              </div>
              <div class="mt-2 flex justify-end">
                <Button variant="ghost" size="sm" class="h-6 cursor-pointer gap-1 px-2 text-[10px] text-destructive hover:text-destructive" @click.stop="removeEdge(edge.id)">
                  <Trash2 class="h-3 w-3" /> 删除
                </Button>
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="json" class="p-4">
          <p class="mb-2 text-xs font-semibold text-muted-foreground">完整 DSL JSON（高级模式）</p>
          <p class="mb-3 text-[10px] text-muted-foreground">编辑后点击"应用 JSON"将覆盖画布状态。</p>
          <textarea
            v-model="fullJsonText"
            rows="28"
            class="w-full rounded border border-input bg-background px-3 py-2 font-mono text-xs leading-5 focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <p v-if="fullJsonError" class="mt-1 text-[10px] text-destructive">{{ fullJsonError }}</p>
          <div class="mt-3 flex gap-2">
            <Button variant="outline" size="sm" class="flex-1 cursor-pointer" @click="syncJsonFromCanvas">
              从画布刷新
            </Button>
            <Button variant="default" size="sm" class="flex-1 cursor-pointer" @click="applyJsonToCanvas">
              应用 JSON
            </Button>
          </div>
        </TabsContent>
      </Tabs>
    </div>

    <!-- Leave confirmation dialog -->
    <Dialog v-model:open="showLeaveDialog">
      <DialogContent class="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>离开编辑器？</DialogTitle>
          <DialogDescription>当前有未保存的修改，离开后将丢失这些更改。</DialogDescription>
        </DialogHeader>
        <DialogFooter class="gap-2">
          <Button variant="outline" class="cursor-pointer" @click="showLeaveDialog = false">继续编辑</Button>
          <Button variant="destructive" class="cursor-pointer" @click="confirmLeave">不保存并离开</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="showPublishDialog">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>审批通过后发布</DialogTitle>
          <DialogDescription>输入审批理由，并键入 workflow_key `{{ workflowKey }}` 完成二次确认；若拒绝，则保留当前草稿。</DialogDescription>
        </DialogHeader>
        <div class="space-y-3">
          <div class="space-y-1.5">
            <p class="text-xs text-muted-foreground">审批理由</p>
            <textarea v-model="publishReason" class="min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"></textarea>
          </div>
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="space-y-1.5">
              <p class="text-xs text-muted-foreground">灰度比例</p>
              <input v-model.number="publishCanaryPercent" type="number" min="1" max="100" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div class="space-y-1.5">
              <p class="text-xs text-muted-foreground">生效时间</p>
              <input v-model="publishEffectiveAt" type="datetime-local" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
          </div>
          <div class="space-y-1.5">
            <p class="text-xs text-muted-foreground">二次确认</p>
            <input v-model="publishConfirmationText" type="text" :placeholder="workflowKey" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
          </div>
        </div>
        <DialogFooter class="gap-2">
          <Button variant="outline" class="cursor-pointer" @click="rejectPublishApproval">拒绝并保留草稿</Button>
          <Button class="cursor-pointer" :disabled="publishing" @click="submitPublish">确认发布</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>

    <Dialog v-model:open="showRollbackDialog">
      <DialogContent class="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>按版本回滚</DialogTitle>
          <DialogDescription>输入回滚原因，并键入 workflow_key `{{ workflowKey }}` 完成二次确认。</DialogDescription>
        </DialogHeader>
        <div class="space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <div class="space-y-1.5">
              <p class="text-xs text-muted-foreground">目标版本</p>
              <input v-model.number="rollbackTargetVersion" type="number" min="1" :max="versionTag" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
            </div>
            <div class="space-y-1.5">
              <p class="text-xs text-muted-foreground">当前已发布</p>
              <div class="flex h-9 items-center rounded-md border border-input bg-muted/20 px-3 text-sm text-muted-foreground">{{ publishedVersion ? `v${publishedVersion}` : '--' }}</div>
            </div>
          </div>
          <div class="space-y-1.5">
            <p class="text-xs text-muted-foreground">回滚原因</p>
            <textarea v-model="rollbackReason" class="min-h-[88px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"></textarea>
          </div>
          <div class="space-y-1.5">
            <p class="text-xs text-muted-foreground">二次确认</p>
            <input v-model="rollbackConfirmationText" type="text" :placeholder="workflowKey" class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring" />
          </div>
        </div>
        <DialogFooter class="gap-2">
          <Button variant="outline" class="cursor-pointer" @click="showRollbackDialog = false">取消</Button>
          <Button variant="destructive" class="cursor-pointer" :disabled="rollingBack" @click="submitRollback">确认回滚</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import {
  ConnectionMode,
  MarkerType,
  Position,
  VueFlow,
  type Connection,
  type Edge,
  type EdgeMouseEvent,
  type EdgeChange,
  type Node,
  type NodeChange,
  type NodeMouseEvent,
} from '@vue-flow/core'
import { Handle } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { NodeToolbar } from '@vue-flow/node-toolbar'
import { nanoid } from 'nanoid'
import {
  ArrowLeft,
  ArrowRight,
  Bell,
  CheckCircle,
  Copy,
  GitBranch,
  Plus,
  Save,
  ShieldCheck,
  Trash2,
  X,
  Zap,
} from 'lucide-vue-next'
import {
  workflowApi,
  type WorkflowCreatePayload,
  type WorkflowDefinitionState,
  type WorkflowDsl,
  type WorkflowEdge,
  type WorkflowNode,
  type WorkflowPublishPayload,
  type WorkflowRollbackPayload,
  type WorkflowUpdatePayload,
} from '@/api/workflow'
import { getRequestErrorMessage } from '@/api/client'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { hasPermission } from '@/composables/useAuthz'
import { Separator } from '@/components/ui/separator'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import '@vue-flow/controls/dist/style.css'

interface EditorNodeData {
  label: string
  nodeType: string
  timeout: number
  retryPolicy: {
    max_retries: number
    backoff_seconds: number
    backoff_multiplier: number
    retry_on: string[]
  }
  config: Record<string, unknown>
}

type EditorFlowNode = Node<EditorNodeData>
type EditorEdgeData = {
  condition: string
  priority: number
}
type EditorFlowEdge = Edge<EditorEdgeData>

const route = useRoute()
const router = useRouter()

const workflowId = computed(() => {
  const raw = route.params.id
  const num = Number(raw)
  return Number.isFinite(num) && num > 0 ? num : null
})
const isNewMode = computed(() => workflowId.value === null)

const nodes = ref<Node<EditorNodeData>[]>([])
const edges = ref<Edge[]>([])

const workflowName = ref('新建流程')
const workflowKey = ref('')
const workflowDescription = ref('')
const versionTag = ref(1)
const definitionState = ref<WorkflowDefinitionState>('DRAFT')
const publishedVersion = ref<number | null>(null)

const selectedNodeId = ref<string>('')
const selectedEdgeId = ref<string>('')
const activeTab = ref('properties')

const isDirty = ref(false)
const saving = ref(false)
const loading = ref(false)
const errorText = ref('')
const successText = ref('')
const autoSaveStatus = ref('')

const configJsonMode = ref(false)
const configJsonText = ref('{}')
const configJsonError = ref('')

const fullJsonText = ref('{}')
const fullJsonError = ref('')

const newConfigKey = ref('')
const newConfigValue = ref('')

const showLeaveDialog = ref(false)
const showPublishDialog = ref(false)
const showRollbackDialog = ref(false)
let pendingLeaveRoute: (() => void) | null = null

const publishReason = ref('')
const publishCanaryPercent = ref(100)
const publishEffectiveAt = ref('')
const publishConfirmationText = ref('')
const rollbackReason = ref('')
const rollbackTargetVersion = ref(1)
const rollbackConfirmationText = ref('')
const publishing = ref(false)
const rollingBack = ref(false)

const AUTO_SAVE_DELAY = 30_000
let autoSaveTimer: ReturnType<typeof setTimeout> | null = null

const canPublishWorkflow = computed(() => !isNewMode.value && hasPermission('workflow_publish'))
const canRollbackWorkflow = computed(() => !isNewMode.value && hasPermission('workflow_rollback') && publishedVersion.value !== null)

function makeDefaultRetryPolicy(): EditorNodeData['retryPolicy'] {
  return {
    max_retries: 0,
    backoff_seconds: 1,
    backoff_multiplier: 1,
    retry_on: [],
  }
}

function normalizeNodeConfig(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== 'object' || Array.isArray(value)) {
    return {}
  }
  return { ...(value as Record<string, unknown>) }
}

function normalizeRetryPolicy(value: Partial<EditorNodeData['retryPolicy']> | null | undefined): EditorNodeData['retryPolicy'] {
  return {
    max_retries: typeof value?.max_retries === 'number' ? value.max_retries : 0,
    backoff_seconds: typeof value?.backoff_seconds === 'number' ? value.backoff_seconds : 1,
    backoff_multiplier: typeof value?.backoff_multiplier === 'number' ? value.backoff_multiplier : 1,
    retry_on: Array.isArray(value?.retry_on) ? value.retry_on.map((item) => String(item)) : [],
  }
}

function getEditorNodeData(node: Pick<EditorFlowNode, 'data'> | null | undefined): EditorNodeData {
  const data = node?.data
  return {
    label: typeof data?.label === 'string' ? data.label : '',
    nodeType: typeof data?.nodeType === 'string' ? data.nodeType : 'action',
    timeout: typeof data?.timeout === 'number' ? data.timeout : 30,
    retryPolicy: normalizeRetryPolicy(data?.retryPolicy),
    config: normalizeNodeConfig(data?.config),
  }
}

function updateNodeData(nodeId: string, updater: (data: EditorNodeData) => EditorNodeData): void {
  const nextNodes = nodes.value.slice()
  const index = nextNodes.findIndex((node) => node.id === nodeId)
  if (index < 0) {
    return
  }
  nextNodes[index] = {
    ...nextNodes[index],
    data: updater(getEditorNodeData(nextNodes[index])),
  } as EditorFlowNode
  nodes.value = nextNodes
}

const nodeTypeIcon = (type: string) => {
  const map: Record<string, unknown> = {
    trigger: markRaw(Zap),
    condition: markRaw(GitBranch),
    action: markRaw(ShieldCheck),
    notification: markRaw(Bell),
    approval: markRaw(CheckCircle),
    ai: markRaw(ShieldCheck),
  }
  return map[type] || map.action
}

const editingNode = computed(() => {
  if (!selectedNodeId.value) return null
  return nodes.value.find((n) => n.id === selectedNodeId.value) || null
})

const editingNodeState = computed(() => {
  if (!editingNode.value) return null
  return {
    id: editingNode.value.id,
    data: getEditorNodeData(editingNode.value),
  }
})

const editingNodeId = computed(() => editingNodeState.value?.id || '')
const editingNodeDataState = computed(() => editingNodeState.value?.data || getEditorNodeData(undefined))
const flowNodesModel = computed<Node[]>({
  get: () => nodes.value as unknown as Node[],
  set: (value) => {
    nodes.value = value as EditorFlowNode[]
  },
})
const flowEdgesModel = computed<Edge[]>({
  get: () => edges.value as unknown as Edge[],
  set: (value) => {
    edges.value = value as EditorFlowEdge[]
  },
})

watch(editingNode, (node) => {
  if (node) {
    configJsonText.value = JSON.stringify(getEditorNodeData(node).config, null, 2)
    configJsonError.value = ''
  }
})

const markDirty = () => {
  isDirty.value = true
  scheduleAutoSave()
}

const scheduleAutoSave = () => {
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
  autoSaveTimer = setTimeout(async () => {
    if (!isDirty.value || saving.value) return
    autoSaveStatus.value = '自动保存中...'
    await saveDraft(true)
    autoSaveStatus.value = '已自动保存'
    setTimeout(() => { autoSaveStatus.value = '' }, 2000)
  }, AUTO_SAVE_DELAY)
}

const addNode = (type: string) => {
  const id = `${type}_${nanoid(6)}`
  const labelMap: Record<string, string> = {
    trigger: '触发器',
    condition: '条件判断',
    action: '执行动作',
    notification: '通知',
    approval: '人工审批',
    ai: 'AI 节点',
  }
  const newNode: EditorFlowNode = {
    id,
    type: 'custom',
    position: { x: 100 + Math.random() * 200, y: 80 + Math.random() * 300 },
    data: {
      label: labelMap[type] || type,
      nodeType: type,
      timeout: 30,
      retryPolicy: makeDefaultRetryPolicy(),
      config: {},
    },
  }
  nodes.value = [...nodes.value, newNode]
  selectedNodeId.value = id
  activeTab.value = 'properties'
  markDirty()
}

const removeNode = (nodeId: string) => {
  nodes.value = nodes.value.filter((n) => n.id !== nodeId)
  edges.value = edges.value.filter((e) => e.source !== nodeId && e.target !== nodeId)
  if (selectedNodeId.value === nodeId) selectedNodeId.value = ''
  markDirty()
}

const duplicateNode = (nodeId: string) => {
  const source = nodes.value.find((n) => n.id === nodeId)
  if (!source) return
  const sourceData = getEditorNodeData(source)
  const newId = `${sourceData.nodeType}_${nanoid(6)}`
  const clone: EditorFlowNode = {
    id: newId,
    type: 'custom',
    position: { x: (source.position?.x ?? 0) + 40, y: (source.position?.y ?? 0) + 40 },
    data: {
      ...JSON.parse(JSON.stringify(sourceData)),
      label: `${sourceData.label} (复制)`,
    },
  }
  nodes.value = [...nodes.value, clone]
  selectedNodeId.value = newId
  markDirty()
}

const onNodeClick = (event: NodeMouseEvent) => {
  selectedNodeId.value = event.node.id
  activeTab.value = 'properties'
}

const onEdgeClick = (event: EdgeMouseEvent) => {
  selectedEdgeId.value = event.edge.id
  activeTab.value = 'edges'
}

const onPaneClick = () => {
  selectedNodeId.value = ''
  selectedEdgeId.value = ''
}

const onConnect = (connection: Connection) => {
  if (!connection.source || !connection.target) return
  const edgeId = `edge_${nanoid(6)}`
  const newEdge: EditorFlowEdge = {
    id: edgeId,
    source: connection.source,
    target: connection.target,
    sourceHandle: connection.sourceHandle ?? undefined,
    targetHandle: connection.targetHandle ?? undefined,
    label: 'true',
    data: { condition: 'true', priority: 0 },
    markerEnd: MarkerType.ArrowClosed,
    style: { stroke: 'rgba(148,163,184,0.72)', strokeWidth: 1.2 },
    labelStyle: { fill: 'rgba(226,232,240,0.92)', fontSize: '11px', fontWeight: 500 },
    labelBgStyle: { fill: 'rgba(15,23,42,0.82)', fillOpacity: 0.95 },
    labelBgPadding: [6, 3] as [number, number],
    labelBgBorderRadius: 4,
  }
  edges.value = [...edges.value, newEdge]
  markDirty()
}

const onNodesChange = (_changes: NodeChange[]) => { markDirty() }
const onEdgesChange = (_changes: EdgeChange[]) => { markDirty() }

const updateNodeLabel = (nodeId: string, label: string) => {
  updateNodeData(nodeId, (data) => ({ ...data, label }))
  markDirty()
}

const updateNodeType = (nodeId: string, nodeType: string) => {
  updateNodeData(nodeId, (data) => ({ ...data, nodeType }))
  markDirty()
}

const updateNodeField = (nodeId: string, field: string, value: unknown) => {
  updateNodeData(nodeId, (data) => ({ ...data, [field]: value } as EditorNodeData))
  markDirty()
}

const updateRetryField = (nodeId: string, field: string, value: number) => {
  updateNodeData(nodeId, (data) => ({
    ...data,
    retryPolicy: { ...data.retryPolicy, [field]: value },
  }))
  markDirty()
}

const updateRetryOn = (nodeId: string, raw: string) => {
  const arr = raw.split(',').map((s) => s.trim()).filter(Boolean)
  updateNodeData(nodeId, (data) => ({
    ...data,
    retryPolicy: { ...data.retryPolicy, retry_on: arr },
  }))
  markDirty()
}

const updateConfigField = (nodeId: string, key: string, value: string) => {
  updateNodeData(nodeId, (data) => ({
    ...data,
    config: { ...data.config, [key]: value },
  }))
  markDirty()
}

const removeConfigField = (nodeId: string, key: string) => {
  updateNodeData(nodeId, (data) => {
    const config = { ...data.config }
    delete config[key]
    return { ...data, config }
  })
  markDirty()
}

const addConfigField = (nodeId: string) => {
  if (!newConfigKey.value.trim()) return
  updateConfigField(nodeId, newConfigKey.value.trim(), newConfigValue.value)
  newConfigKey.value = ''
  newConfigValue.value = ''
}

const onConfigJsonInput = (nodeId: string, raw: string) => {
  configJsonText.value = raw
  try {
    const parsed = JSON.parse(raw)
    if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) {
      configJsonError.value = 'config 必须是一个对象'
      return
    }
    configJsonError.value = ''
    updateNodeData(nodeId, (data) => ({
      ...data,
      config: parsed as Record<string, unknown>,
    }))
    markDirty()
  } catch {
    configJsonError.value = 'JSON 语法错误'
  }
}

const updateEdgeCondition = (edgeId: string, condition: string) => {
  edges.value = edges.value.map((e) => {
    if (e.id !== edgeId) return e
    return { ...e, label: condition, data: { ...(e.data as any), condition } }
  })
  markDirty()
}

const updateEdgePriority = (edgeId: string, priority: number) => {
  edges.value = edges.value.map((e) => {
    if (e.id !== edgeId) return e
    return { ...e, data: { ...(e.data as any), priority } }
  })
  markDirty()
}

const removeEdge = (edgeId: string) => {
  edges.value = edges.value.filter((e) => e.id !== edgeId)
  if (selectedEdgeId.value === edgeId) selectedEdgeId.value = ''
  markDirty()
}

const buildDsl = (): Record<string, unknown> => {
  const dslNodes: WorkflowNode[] = nodes.value.map((n) => {
    const data = getEditorNodeData(n)
    return {
      id: n.id,
      type: data.nodeType || 'action',
      name: data.label || n.id,
      config: data.config,
      timeout: data.timeout || 30,
      retry_policy: data.retryPolicy,
    }
  })

  const dslEdges: WorkflowEdge[] = edges.value.map((e) => ({
    from: e.source,
    to: e.target,
    condition: (e.data as any)?.condition || 'true',
    priority: (e.data as any)?.priority || 0,
  }))

  return {
    schema_version: '1.0.0',
    workflow_id: workflowKey.value || `wf-${nanoid(8)}`,
    version: versionTag.value,
    name: workflowName.value,
    description: workflowDescription.value || undefined,
    status: 'DRAFT',
    context: { inputs: {}, outputs: {} },
    runtime: {
      initial_state: 'QUEUED',
      terminal_states: ['SUCCESS', 'FAILED', 'CANCELLED', 'MANUAL_REQUIRED'],
      state_enum: ['QUEUED', 'RUNNING', 'RETRYING', 'SUCCESS', 'FAILED', 'MANUAL_REQUIRED', 'CANCELLED'],
    },
    nodes: dslNodes,
    edges: dslEdges,
    metadata: {
      canvas: nodes.value.map((n) => ({
        id: n.id,
        x: n.position?.x ?? 0,
        y: n.position?.y ?? 0,
      })),
    },
  }
}

const saveDraft = async (silent = false) => {
  if (saving.value) return
  saving.value = true
  errorText.value = ''
  successText.value = ''
  try {
    const dsl = buildDsl()
    if (isNewMode.value) {
      if (!workflowKey.value.trim()) {
        workflowKey.value = `wf-${nanoid(8)}`
      }
      const payload: WorkflowCreatePayload = {
        workflow_key: workflowKey.value,
        name: workflowName.value,
        description: workflowDescription.value || undefined,
        dsl,
        change_note: '初始创建',
      }
      const result = await workflowApi.createWorkflow(payload)
      isDirty.value = false
      versionTag.value = result.version_tag
      definitionState.value = result.definition_state
      publishedVersion.value = result.published_version
      if (!silent) successText.value = `流程创建成功 (id=${result.id})`
      router.replace({ path: `/workflow/${result.id}/edit` })
    } else {
      const payload: WorkflowUpdatePayload = {
        version_tag: versionTag.value,
        name: workflowName.value,
        description: workflowDescription.value || undefined,
        dsl,
        change_note: '草稿保存',
      }
      const result = await workflowApi.updateWorkflow(workflowId.value!, payload)
      isDirty.value = false
      versionTag.value = result.version_tag
      definitionState.value = result.definition_state
      publishedVersion.value = result.published_version
      if (!silent) successText.value = '草稿已保存'
    }
  } catch (err) {
    errorText.value = getRequestErrorMessage(err, '保存失败')
  } finally {
    saving.value = false
  }
}

const validateDraft = async () => {
  if (isDirty.value) {
    await saveDraft(true)
  }
  if (!workflowId.value) {
    errorText.value = '请先保存流程后再校验'
    return
  }
  try {
    const result = await workflowApi.validateWorkflow(workflowId.value)
    if (result.valid) {
      successText.value = `校验通过 (v${result.version})`
    } else {
      errorText.value = `校验失败(${result.summary.error_count}项): ${result.errors.map((item) => `${item.code} ${item.message}`).join('; ')}`
    }
  } catch (err) {
    errorText.value = getRequestErrorMessage(err, '校验请求失败')
  }
}

const resetPublishDialog = () => {
  publishReason.value = ''
  publishCanaryPercent.value = 100
  publishEffectiveAt.value = ''
  publishConfirmationText.value = ''
}

const resetRollbackDialog = () => {
  rollbackReason.value = ''
  rollbackTargetVersion.value = publishedVersion.value && publishedVersion.value > 1 ? publishedVersion.value - 1 : 1
  rollbackConfirmationText.value = ''
}

const openPublishDialog = () => {
  resetPublishDialog()
  showPublishDialog.value = true
}

const rejectPublishApproval = () => {
  showPublishDialog.value = false
  successText.value = '已拒绝发布，草稿已保留'
}

const openRollbackDialog = () => {
  resetRollbackDialog()
  showRollbackDialog.value = true
}

const submitPublish = async () => {
  if (!workflowId.value) {
    errorText.value = '请先保存流程后再发布'
    return
  }
  if (!publishReason.value.trim()) {
    errorText.value = '请输入审批理由'
    return
  }
  if (publishConfirmationText.value.trim() !== workflowKey.value) {
    errorText.value = '二次确认内容不正确'
    return
  }
  if (publishCanaryPercent.value < 1 || publishCanaryPercent.value > 100) {
    errorText.value = '灰度比例必须在 1 到 100 之间'
    return
  }
  if (isDirty.value) {
    await saveDraft(true)
    if (isDirty.value) return
  }
  publishing.value = true
  errorText.value = ''
  try {
    const payload: WorkflowPublishPayload = {
      version_tag: versionTag.value,
      canary_percent: publishCanaryPercent.value,
      effective_at: publishEffectiveAt.value ? new Date(publishEffectiveAt.value).toISOString() : undefined,
      approval_reason: publishReason.value.trim(),
      approval_passed: true,
      confirmation_text: publishConfirmationText.value.trim(),
    }
    const result = await workflowApi.publishWorkflow(workflowId.value, payload)
    showPublishDialog.value = false
    definitionState.value = result.definition_state
    publishedVersion.value = result.published_version
    successText.value = `发布成功：v${result.published_version ?? result.version}`
    await loadExistingWorkflow()
  } catch (err) {
    errorText.value = getRequestErrorMessage(err, '发布失败')
  } finally {
    publishing.value = false
  }
}

const submitRollback = async () => {
  if (!workflowId.value) {
    errorText.value = '请先保存流程后再回滚'
    return
  }
  if (!rollbackReason.value.trim()) {
    errorText.value = '请输入回滚原因'
    return
  }
  if (rollbackConfirmationText.value.trim() !== workflowKey.value) {
    errorText.value = '二次确认内容不正确'
    return
  }
  if (rollbackTargetVersion.value < 1 || rollbackTargetVersion.value > versionTag.value) {
    errorText.value = '目标版本超出范围'
    return
  }
  if (isDirty.value) {
    await saveDraft(true)
    if (isDirty.value) return
  }
  rollingBack.value = true
  errorText.value = ''
  try {
    const payload: WorkflowRollbackPayload = {
      target_version: rollbackTargetVersion.value,
      reason: rollbackReason.value.trim(),
      confirmation_text: rollbackConfirmationText.value.trim(),
    }
    const result = await workflowApi.rollbackWorkflow(workflowId.value, payload)
    showRollbackDialog.value = false
    definitionState.value = result.definition_state
    publishedVersion.value = result.published_version
    successText.value = `已回滚到 v${result.rolled_back_to_version}`
    await loadExistingWorkflow()
  } catch (err) {
    errorText.value = getRequestErrorMessage(err, '回滚失败')
  } finally {
    rollingBack.value = false
  }
}

const syncJsonFromCanvas = () => {
  fullJsonText.value = JSON.stringify(buildDsl(), null, 2)
  fullJsonError.value = ''
}

const applyJsonToCanvas = () => {
  try {
    const parsed = JSON.parse(fullJsonText.value)
    fullJsonError.value = ''
    loadDslToCanvas(parsed)
    markDirty()
    successText.value = 'JSON 已应用到画布'
  } catch {
    fullJsonError.value = 'JSON 语法错误，无法解析'
  }
}

const loadDslToCanvas = (dsl: Record<string, unknown>) => {
  const dslObj = dsl as Partial<WorkflowDsl & { metadata?: { canvas?: Array<{ id: string; x: number; y: number }> } }>
  workflowName.value = dslObj.name || workflowName.value
  workflowDescription.value = dslObj.description || ''
  if (dslObj.workflow_id) workflowKey.value = dslObj.workflow_id

  const canvasPositions = new Map<string, { x: number; y: number }>()
  if (Array.isArray(dslObj.metadata?.canvas)) {
    for (const item of dslObj.metadata!.canvas) {
      if (item.id) canvasPositions.set(item.id, { x: item.x ?? 0, y: item.y ?? 0 })
    }
  }

  const rawNodes = Array.isArray(dslObj.nodes) ? dslObj.nodes : []
  const rawEdges = Array.isArray(dslObj.edges) ? dslObj.edges : []

  nodes.value = rawNodes.map((n: any, i: number): EditorFlowNode => {
    const pos = canvasPositions.get(n.id) || layoutPosition(i, rawNodes.length)
    return {
      id: n.id || `node_${nanoid(6)}`,
      type: 'custom',
      position: pos,
      data: {
        label: n.name || n.id || `Node ${i + 1}`,
        nodeType: n.type || 'action',
        timeout: n.timeout || 30,
        retryPolicy: normalizeRetryPolicy(n.retry_policy),
        config: normalizeNodeConfig(n.config),
      },
    }
  })

  edges.value = rawEdges.map((e: any): EditorFlowEdge => ({
    id: `edge_${nanoid(6)}`,
    source: e.from || '',
    target: e.to || '',
    label: e.condition || 'true',
    data: { condition: e.condition || 'true', priority: e.priority || 0 },
    markerEnd: MarkerType.ArrowClosed,
    style: { stroke: 'rgba(148,163,184,0.72)', strokeWidth: 1.2 },
    labelStyle: { fill: 'rgba(226,232,240,0.92)', fontSize: '11px', fontWeight: 500 },
    labelBgStyle: { fill: 'rgba(15,23,42,0.82)', fillOpacity: 0.95 },
    labelBgPadding: [6, 3] as [number, number],
    labelBgBorderRadius: 4,
  }))

  selectedNodeId.value = nodes.value[0]?.id || ''
}

const layoutPosition = (index: number, total: number): { x: number; y: number } => {
  const cols = Math.max(3, Math.ceil(Math.sqrt(total)))
  const col = index % cols
  const row = Math.floor(index / cols)
  return { x: 100 + col * 280, y: 80 + row * 160 }
}

const loadExistingWorkflow = async () => {
  if (!workflowId.value) return
  loading.value = true
  errorText.value = ''
  try {
    const detail = await workflowApi.getWorkflowDetail(workflowId.value)
    workflowName.value = detail.workflow.name
    workflowKey.value = detail.workflow.workflow_key
    workflowDescription.value = detail.workflow.description || ''
    versionTag.value = detail.workflow.version_tag
    definitionState.value = detail.workflow.definition_state
    publishedVersion.value = detail.workflow.published_version
    rollbackTargetVersion.value = detail.workflow.published_version && detail.workflow.published_version > 1 ? detail.workflow.published_version - 1 : 1
    loadDslToCanvas(detail.dsl as unknown as Record<string, unknown>)
    isDirty.value = false
    syncJsonFromCanvas()
  } catch (err) {
    errorText.value = getRequestErrorMessage(err, '加载流程失败')
  } finally {
    loading.value = false
  }
}

const goBack = () => {
  if (isDirty.value) {
    pendingLeaveRoute = () => router.push('/workflow/catalog')
    showLeaveDialog.value = true
  } else {
    router.push('/workflow/catalog')
  }
}

const confirmLeave = () => {
  isDirty.value = false
  showLeaveDialog.value = false
  if (pendingLeaveRoute) {
    pendingLeaveRoute()
    pendingLeaveRoute = null
  }
}

onBeforeRouteLeave((_to, _from, next) => {
  if (!isDirty.value) {
    next()
    return
  }
  pendingLeaveRoute = () => next()
  showLeaveDialog.value = true
})

const beforeUnloadHandler = (e: BeforeUnloadEvent) => {
  if (isDirty.value) {
    e.preventDefault()
    e.returnValue = ''
  }
}

onMounted(() => {
  window.addEventListener('beforeunload', beforeUnloadHandler)
  if (!isNewMode.value) {
    loadExistingWorkflow()
  } else {
    syncJsonFromCanvas()
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('beforeunload', beforeUnloadHandler)
  if (autoSaveTimer) clearTimeout(autoSaveTimer)
})
</script>

<style scoped>
.editor-node {
  min-width: 170px;
  max-width: 220px;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.92), rgba(2, 6, 23, 0.96));
  box-shadow: 0 6px 20px rgba(2, 6, 23, 0.3);
  padding: 10px 12px;
  cursor: grab;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.editor-node--selected {
  border-color: rgba(34, 211, 238, 0.6);
  box-shadow: 0 0 0 2px rgba(34, 211, 238, 0.15), 0 6px 20px rgba(2, 6, 23, 0.3);
}

.editor-node--trigger { border-left: 3px solid rgba(250, 204, 21, 0.7); }
.editor-node--condition { border-left: 3px solid rgba(168, 85, 247, 0.7); }
.editor-node--action { border-left: 3px solid rgba(34, 211, 238, 0.7); }
.editor-node--notification { border-left: 3px solid rgba(251, 146, 60, 0.7); }
.editor-node--approval { border-left: 3px solid rgba(74, 222, 128, 0.7); }
.editor-node--ai { border-left: 3px solid rgba(129, 140, 248, 0.7); }

.editor-node__header {
  display: flex;
  align-items: center;
  gap: 6px;
  color: rgba(241, 245, 249, 0.95);
}

.editor-node__type {
  margin-top: 4px;
  color: rgba(148, 163, 184, 0.8);
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
  font-size: 10px;
}

.editor-node__handles {
  position: absolute;
  inset: 0;
  pointer-events: none;
}
</style>
