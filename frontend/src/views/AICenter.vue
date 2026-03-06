<template>
  <div class="flex h-[calc(100vh-64px)] overflow-hidden">
    <!-- 左侧：会话历史 -->
    <aside class="w-56 shrink-0 border-r border-border bg-muted/20 flex flex-col">
      <div class="flex items-center justify-between px-3 py-3 border-b border-border">
        <span class="text-xs font-semibold text-muted-foreground uppercase tracking-wide">历史会话</span>
        <Button variant="ghost" size="icon" class="size-6 cursor-pointer" title="新建会话" @click="newSession">
          <Plus class="size-3.5" />
        </Button>
      </div>
      <div class="flex-1 overflow-y-auto p-2 space-y-1">
        <div v-if="sessionsLoading" class="space-y-1.5">
          <Skeleton v-for="i in 4" :key="i" class="h-10 w-full rounded" />
        </div>
        <div v-else-if="sessions.length === 0" class="py-8 text-center text-xs text-muted-foreground">
          暂无历史会话
        </div>
        <button
          v-for="s in sessions"
          :key="s.id"
          :class="[
            'w-full rounded-md px-2.5 py-2 text-left text-xs transition-colors',
            currentSessionId === s.id
              ? 'bg-primary/15 text-primary'
              : 'hover:bg-muted text-muted-foreground hover:text-foreground',
          ]"
          @click="loadSession(s)"
        >
          <p class="truncate font-medium">{{ s.context_type || 'AI 对话' }}</p>
          <p class="text-[10px] opacity-60 mt-0.5">{{ formatTime(s.started_at) }}</p>
        </button>
      </div>
    </aside>

    <!-- 中：对话区 -->
    <div class="flex flex-1 flex-col min-w-0">
      <!-- 对话头部 -->
      <div class="flex items-center justify-between border-b border-border px-5 py-3">
        <div class="flex items-center gap-2">
          <BrainCircuit class="size-4 text-primary" />
          <span class="font-semibold text-sm">AI 对话</span>
          <Badge v-if="currentSessionId" variant="outline" class="text-[10px] h-4">Session #{{ currentSessionId }}</Badge>
        </div>
        <Button variant="ghost" size="sm" class="cursor-pointer text-xs gap-1 text-muted-foreground" @click="newSession">
          <Plus class="size-3" />
          新建
        </Button>
      </div>

      <!-- 消息列表 -->
      <div ref="msgContainer" class="flex-1 overflow-y-auto px-5 py-4 space-y-4">
        <div v-if="messages.length === 0 && !aiThinking" class="flex flex-col items-center justify-center h-full text-muted-foreground">
          <BrainCircuit class="size-12 opacity-20 mb-4" />
          <p class="text-sm">输入消息开始对话</p>
          <p class="text-xs mt-1 opacity-60">支持询问告警分析、扫描解读、修复建议等</p>
        </div>

        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          class="flex"
          :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
        >
          <!-- AI 头像 -->
          <div v-if="msg.role === 'assistant'" class="size-7 rounded-full bg-primary/15 flex items-center justify-center mr-2.5 shrink-0 mt-0.5">
            <BrainCircuit class="size-3.5 text-primary" />
          </div>

          <div
            class="max-w-[75%] rounded-xl px-4 py-2.5 text-sm leading-relaxed"
            :class="msg.role === 'user'
              ? 'bg-primary text-primary-foreground rounded-tr-sm'
              : 'bg-muted text-foreground rounded-tl-sm'"
          >
            {{ msg.content }}
            <p class="text-[10px] mt-1.5 opacity-50">{{ formatTime(msg.created_at) }}</p>
          </div>

          <!-- 用户头像 -->
          <div v-if="msg.role === 'user'" class="size-7 rounded-full bg-muted flex items-center justify-center ml-2.5 shrink-0 mt-0.5">
            <User class="size-3.5 text-muted-foreground" />
          </div>
        </div>

        <!-- AI 思考中 -->
        <div v-if="aiThinking" class="flex justify-start">
          <div class="size-7 rounded-full bg-primary/15 flex items-center justify-center mr-2.5 shrink-0">
            <BrainCircuit class="size-3.5 text-primary animate-pulse" />
          </div>
          <div class="bg-muted rounded-xl rounded-tl-sm px-4 py-2.5">
            <div class="flex gap-1 items-center h-4">
              <span class="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style="animation-delay:0ms" />
              <span class="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style="animation-delay:150ms" />
              <span class="size-1.5 rounded-full bg-muted-foreground/60 animate-bounce" style="animation-delay:300ms" />
            </div>
          </div>
        </div>
      </div>

      <!-- 输入框 -->
      <div class="border-t border-border px-5 py-3">
        <form class="flex gap-2" @submit.prevent="sendMessage">
          <Input
            v-model="inputMessage"
            placeholder="询问告警分析、漏洞解读、修复建议…"
            class="flex-1"
            :disabled="aiThinking"
            @keydown.enter.exact.prevent="sendMessage"
          />
          <Button type="submit" class="cursor-pointer gap-1.5 shrink-0" :disabled="!inputMessage.trim() || aiThinking">
            <Send class="size-4" />
            发送
          </Button>
        </form>
        <p class="text-[10px] text-muted-foreground mt-1.5 px-1">Enter 发送 · 可在对话中引用事件 ID 或扫描任务 ID</p>
      </div>
    </div>

    <!-- 右侧：报告 + TTS -->
    <aside class="w-64 shrink-0 border-l border-border flex flex-col">
      <!-- 标签切换 -->
      <div class="flex border-b border-border">
        <button
          v-for="tab in rightTabs"
          :key="tab.key"
          :class="[
            'flex-1 py-2.5 text-xs font-medium text-center border-b-2 transition-colors',
            rightTab === tab.key
              ? 'border-primary text-primary'
              : 'border-transparent text-muted-foreground hover:text-foreground',
          ]"
          @click="rightTab = tab.key"
        >{{ tab.label }}</button>
      </div>

      <!-- 报告面板 -->
      <div v-show="rightTab === 'report'" class="flex flex-col flex-1 min-h-0">
        <div class="px-3 py-2.5 border-b border-border space-y-2">
          <div class="grid grid-cols-2 gap-1.5">
            <Button variant="outline" size="sm" class="cursor-pointer text-xs gap-1" :disabled="reportGenerating" @click="generateReport('daily')">
              <FileText class="size-3" /> 日报
            </Button>
            <Button variant="outline" size="sm" class="cursor-pointer text-xs gap-1" :disabled="reportGenerating" @click="generateReport('weekly')">
              <FileText class="size-3" /> 周报
            </Button>
          </div>
          <Button variant="outline" size="sm" class="cursor-pointer text-xs gap-1 w-full" :disabled="reportGenerating" @click="generateReport('scan')">
            <FileText class="size-3" /> 扫描报告
          </Button>
          <p v-if="reportGenerating" class="text-[10px] text-muted-foreground text-center animate-pulse">生成中…</p>
          <p v-if="reportMsg" class="text-[10px] text-center" :class="reportMsgOk ? 'text-emerald-400' : 'text-destructive'">{{ reportMsg }}</p>
        </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-1.5">
          <div v-if="reportsLoading" class="space-y-1.5">
            <Skeleton v-for="i in 3" :key="i" class="h-16 w-full rounded" />
          </div>
          <div v-else-if="reports.length === 0" class="py-8 text-center text-xs text-muted-foreground">暂无报告</div>
          <div
            v-for="r in reports"
            :key="r.id"
            class="rounded-lg border border-border p-2.5 space-y-1 cursor-pointer hover:bg-muted/40 transition-colors"
            @click="selectedReport = selectedReport?.id === r.id ? null : r"
          >
            <div class="flex items-center justify-between">
              <Badge variant="outline" class="text-[10px] h-4 capitalize">{{ r.report_type }}</Badge>
              <span class="text-[10px] text-muted-foreground">{{ formatDate(r.created_at) }}</span>
            </div>
            <p class="text-xs text-muted-foreground line-clamp-2">{{ r.summary }}</p>
            <div v-if="selectedReport?.id === r.id" class="text-[10px] text-muted-foreground pt-1 border-t border-border mt-1 space-y-0.5">
              <p>trace: <code>{{ r.trace_id?.slice(0, 16) }}</code></p>
              <p>path: {{ r.detail_path }}</p>
            </div>
          </div>
        </div>
      </div>

      <!-- TTS 面板 -->
      <div v-show="rightTab === 'tts'" class="flex flex-col flex-1 min-h-0">
        <div class="px-3 py-2.5 border-b border-border space-y-2">
          <textarea
            v-model="ttsText"
            rows="3"
            placeholder="输入文本，将其转为语音…"
            class="w-full rounded-md border border-input bg-background px-2.5 py-2 text-xs placeholder:text-muted-foreground resize-none focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <Button size="sm" class="cursor-pointer text-xs gap-1 w-full" :disabled="!ttsText.trim() || ttsCreating" @click="createTTS">
            <Volume2 class="size-3" />
            {{ ttsCreating ? '创建中…' : '创建 TTS 任务' }}
          </Button>
          <p v-if="ttsMsg" class="text-[10px] text-center" :class="ttsMsgOk ? 'text-emerald-400' : 'text-destructive'">{{ ttsMsg }}</p>
        </div>
        <div class="flex-1 overflow-y-auto p-2 space-y-1.5">
          <div v-if="ttsLoading" class="space-y-1.5">
            <Skeleton v-for="i in 3" :key="i" class="h-12 w-full rounded" />
          </div>
          <div v-else-if="ttsTasks.length === 0" class="py-8 text-center text-xs text-muted-foreground">暂无 TTS 任务</div>
          <div
            v-for="t in ttsTasks"
            :key="t.id"
            class="rounded-lg border border-border p-2.5 space-y-1"
          >
            <div class="flex items-center justify-between">
              <span class="text-[10px] text-muted-foreground">#{{ t.id }}</span>
              <Badge
                :class="ttsStateColor(t.state)"
                class="text-[10px] h-4"
              >{{ t.state }}</Badge>
            </div>
            <p class="text-xs text-muted-foreground line-clamp-2">{{ t.text_preview }}</p>
            <div v-if="t.state === 'PENDING'" class="pt-1">
              <Button variant="outline" size="sm" class="cursor-pointer text-[10px] h-5 w-full gap-1" @click="processTTS(t.id)">
                <Play class="size-2.5" /> 模拟处理
              </Button>
            </div>
            <div v-if="t.audio_path" class="text-[10px] text-emerald-400 truncate">{{ t.audio_path }}</div>
          </div>
        </div>
      </div>
    </aside>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onMounted, ref } from 'vue'
import { aiApi } from '@/api/ai'
import { reportApi } from '@/api/report'
import { ttsApi, type TTSTask } from '@/api/tts'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { BrainCircuit, FileText, Play, Plus, Send, User, Volume2 } from 'lucide-vue-next'

interface Message {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

interface Session {
  id: number
  context_type: string | null
  started_at: string
  expires_at: string | null
}

interface Report {
  id: number
  report_type: string
  summary: string
  detail_path: string | null
  trace_id: string | null
  created_at: string
}

// ── 右侧标签 ──
const rightTabs = [
  { key: 'report', label: '报告' },
  { key: 'tts', label: 'TTS' },
]
const rightTab = ref('report')

// ── 状态 ──
const messages = ref<Message[]>([])
const inputMessage = ref('')
const aiThinking = ref(false)
const currentSessionId = ref<number | null>(null)
const msgContainer = ref<HTMLElement | null>(null)

const sessions = ref<Session[]>([])
const sessionsLoading = ref(false)

const reports = ref<Report[]>([])
const reportsLoading = ref(false)
const reportGenerating = ref(false)
const reportMsg = ref('')
const reportMsgOk = ref(true)
const selectedReport = ref<Report | null>(null)

// TTS
const ttsText = ref('')
const ttsCreating = ref(false)
const ttsMsg = ref('')
const ttsMsgOk = ref(true)
const ttsTasks = ref<TTSTask[]>([])
const ttsLoading = ref(false)

// ── 会话管理 ──
const newSession = () => {
  currentSessionId.value = null
  messages.value = []
  inputMessage.value = ''
}

const loadSessions = async () => {
  sessionsLoading.value = true
  try {
    const data: any = await aiApi.getSessions()
    sessions.value = Array.isArray(data) ? data : (data?.data ?? [])
  } catch {
    sessions.value = []
  } finally {
    sessionsLoading.value = false
  }
}

const loadSession = async (s: Session) => {
  currentSessionId.value = s.id
  messages.value = []
  try {
    const msgs: any = await aiApi.getSessionMessages(s.id)
    const list = Array.isArray(msgs) ? msgs : (msgs?.data ?? [])
    messages.value = list.map((m: any) => ({
      role: m.role,
      content: m.content,
      created_at: m.created_at,
    }))
    await scrollToBottom()
  } catch {
    messages.value = []
  }
}

// ── 发送消息（带 session_id） ──
const sendMessage = async () => {
  const text = inputMessage.value.trim()
  if (!text || aiThinking.value) return

  const now = new Date().toISOString()
  messages.value.push({ role: 'user', content: text, created_at: now })
  inputMessage.value = ''
  aiThinking.value = true
  await scrollToBottom()

  try {
    const res: any = await aiApi.chat(text, currentSessionId.value ?? undefined)
    const data = res?.data ?? res
    const sessionId = data?.session_id ?? res?.session_id
    const reply = data?.message ?? res?.message ?? '（无响应）'

    if (sessionId && !currentSessionId.value) {
      currentSessionId.value = sessionId
      await loadSessions()
    }

    messages.value.push({ role: 'assistant', content: reply, created_at: new Date().toISOString() })
  } catch {
    messages.value.push({ role: 'assistant', content: '抱歉，服务暂时不可用，请稍后重试。', created_at: new Date().toISOString() })
  } finally {
    aiThinking.value = false
    await scrollToBottom()
  }
}

// ── 报告 ──
const loadReports = async () => {
  reportsLoading.value = true
  try {
    const data: any = await reportApi.getReports()
    const list = data?.items ?? (Array.isArray(data) ? data : (data?.data ?? []))
    reports.value = Array.isArray(list) ? list : []
  } catch {
    reports.value = []
  } finally {
    reportsLoading.value = false
  }
}

const generateReport = async (type: string) => {
  reportGenerating.value = true
  reportMsg.value = ''
  try {
    await reportApi.generate(type)
    reportMsg.value = '报告已生成'
    reportMsgOk.value = true
    await loadReports()
  } catch {
    reportMsg.value = '生成失败'
    reportMsgOk.value = false
  } finally {
    reportGenerating.value = false
    setTimeout(() => { reportMsg.value = '' }, 3000)
  }
}

// ── TTS ──
const loadTTS = async () => {
  ttsLoading.value = true
  try {
    const data = await ttsApi.listTasks({ page: 1, page_size: 20 })
    ttsTasks.value = data?.items ?? []
  } catch {
    ttsTasks.value = []
  } finally {
    ttsLoading.value = false
  }
}

const createTTS = async () => {
  const text = ttsText.value.trim()
  if (!text) return
  ttsCreating.value = true
  ttsMsg.value = ''
  try {
    await ttsApi.createTask(text)
    ttsText.value = ''
    ttsMsgOk.value = true
    ttsMsg.value = 'TTS 任务已创建'
    await loadTTS()
  } catch {
    ttsMsgOk.value = false
    ttsMsg.value = '创建失败'
  } finally {
    ttsCreating.value = false
    setTimeout(() => { ttsMsg.value = '' }, 3000)
  }
}

const processTTS = async (taskId: number) => {
  try {
    await ttsApi.processTask(taskId)
    await loadTTS()
  } catch { /* ignore */ }
}

const ttsStateColor = (s: string) => {
  const m: Record<string, string> = {
    PENDING: 'bg-amber-500/15 text-amber-400 border-amber-500/30',
    PROCESSING: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
    SUCCESS: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
    FAILED: 'bg-destructive/15 text-destructive border-destructive/30',
  }
  return m[s] || 'bg-muted text-muted-foreground'
}

// ── 工具函数 ──
const scrollToBottom = async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}

const formatTime = (t: string) =>
  t ? new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : ''

const formatDate = (t: string) =>
  t ? new Date(t).toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit' }) : ''

onMounted(() => {
  loadSessions()
  loadReports()
  loadTTS()
})
</script>
