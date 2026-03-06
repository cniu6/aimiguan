<template>
  <div class="p-6 max-w-[1400px] mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight text-foreground">防御监控</h1>
        <p class="text-muted-foreground">实时威胁事件处置</p>
      </div>
      <Button variant="outline" size="sm" class="cursor-pointer gap-1.5" :disabled="loading" @click="loadEvents">
        <RefreshCw class="size-3.5" :class="loading ? 'animate-spin' : ''" />
        刷新
      </Button>
    </div>

    <!-- Stats -->
    <div class="grid gap-4 md:grid-cols-3">
      <Card v-for="stat in stats" :key="stat.label">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{ stat.label }}</CardTitle>
          <component :is="stat.icon" class="size-4 text-muted-foreground/60" />
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold" :class="stat.color">{{ stat.value }}</div>
        </CardContent>
      </Card>
    </div>

    <!-- Events -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold tracking-tight">待处置事件</h2>
        <span class="text-xs text-muted-foreground">点击 IP 可查看 Nmap 扫描详情</span>
      </div>

      <!-- Loading skeleton -->
      <div v-if="loading" class="space-y-3">
        <Skeleton v-for="i in 3" :key="i" class="h-[140px] w-full rounded-lg" />
      </div>

      <!-- Empty -->
      <Card v-else-if="events.length === 0" class="border-dashed">
        <CardContent class="flex flex-col items-center justify-center py-12">
          <ShieldCheck class="size-12 text-muted-foreground/40 mb-4" />
          <p class="text-sm text-muted-foreground">暂无待处置事件</p>
        </CardContent>
      </Card>

      <!-- Event list -->
      <div v-else class="space-y-3">
        <Card
          v-for="event in events"
          :key="event.id"
          class="overflow-hidden transition-colors hover:bg-accent/50"
        >
          <CardHeader class="pb-3">
            <div class="flex items-center justify-between">
              <!-- 可点击的 IP，触发 Nmap 关联查询 -->
              <button
                class="flex items-center gap-1.5 group cursor-pointer"
                @click="showIpInfo(event.ip)"
              >
                <code class="text-sm font-semibold group-hover:text-primary transition-colors">{{ event.ip }}</code>
                <Search class="size-3 text-muted-foreground/50 group-hover:text-primary transition-colors" />
              </button>
              <div class="flex items-center gap-2">
                <span class="text-xs text-muted-foreground">{{ formatTime(event.created_at) }}</span>
                <Badge :variant="getScoreVariant(event.ai_score)" :class="getScoreColor(event.ai_score)">
                  {{ event.ai_score }} 分
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent class="space-y-3">
            <p class="text-sm text-muted-foreground leading-relaxed">{{ event.ai_reason }}</p>
            <div class="flex items-center gap-4 text-xs text-muted-foreground">
              <span>来源: <span class="text-foreground">{{ event.source }}</span></span>
              <span v-if="event.status">状态: <Badge variant="outline" class="text-xs h-4">{{ event.status }}</Badge></span>
            </div>
            <div class="flex gap-2 pt-2">
              <Button size="sm" class="cursor-pointer gap-2" @click="approveEvent(event.id)">
                <ShieldCheck class="size-4" />
                批准封禁
              </Button>
              <Button variant="outline" size="sm" class="cursor-pointer" @click="rejectEvent(event.id)">
                驳回
              </Button>
              <Button variant="ghost" size="sm" class="cursor-pointer gap-1.5 ml-auto text-xs" @click="showIpInfo(event.ip)">
                <Search class="size-3.5" />
                查扫描
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- IP 关联查询弹窗 -->
    <div
      v-if="ipInfoOpen"
      class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
      @click.self="ipInfoOpen = false"
    >
      <div class="mx-4 w-full max-w-lg rounded-xl border border-border bg-background shadow-2xl">
        <!-- 弹窗头 -->
        <div class="flex items-center justify-between border-b border-border px-5 py-4">
          <div class="flex items-center gap-2">
            <Monitor class="size-4 text-primary" />
            <span class="font-semibold text-sm">IP 扫描详情</span>
            <code class="text-xs text-muted-foreground ml-1">{{ currentIp }}</code>
          </div>
          <button class="text-muted-foreground hover:text-foreground transition-colors" @click="ipInfoOpen = false">
            <X class="size-4" />
          </button>
        </div>

        <!-- 弹窗体 -->
        <div class="p-5 space-y-4">
          <!-- 加载中 -->
          <div v-if="ipInfoLoading" class="space-y-3">
            <Skeleton v-for="i in 4" :key="i" class="h-8 w-full rounded" />
          </div>

          <!-- 无数据 -->
          <div v-else-if="!ipInfo" class="py-8 text-center">
            <Monitor class="size-10 text-muted-foreground/30 mx-auto mb-3" />
            <p class="text-sm text-muted-foreground">未找到该 IP 的 Nmap 扫描记录</p>
            <p class="text-xs text-muted-foreground mt-1">请先在「探测扫描」中对该 IP 范围执行扫描</p>
          </div>

          <!-- 主机信息 -->
          <template v-else>
            <div class="grid grid-cols-2 gap-3 text-sm">
              <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
                <p class="text-xs text-muted-foreground">操作系统</p>
                <p class="font-medium">{{ ipInfo.os_type || '未识别' }}</p>
                <p v-if="ipInfo.os_accuracy" class="text-xs text-muted-foreground">精确度 {{ ipInfo.os_accuracy }}%</p>
              </div>
              <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
                <p class="text-xs text-muted-foreground">主机名 / 厂商</p>
                <p class="font-medium">{{ ipInfo.hostname || '—' }}</p>
                <p class="text-xs text-muted-foreground">{{ ipInfo.vendor || '未知厂商' }}</p>
              </div>
              <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
                <p class="text-xs text-muted-foreground">MAC 地址</p>
                <code class="text-xs">{{ ipInfo.mac_address || '—' }}</code>
              </div>
              <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
                <p class="text-xs text-muted-foreground">开放端口数</p>
                <p class="font-semibold text-primary">{{ ipInfo.open_ports?.length ?? 0 }}</p>
              </div>
            </div>

            <!-- 开放端口与服务 -->
            <div v-if="ipInfo.services?.length" class="space-y-1.5">
              <p class="text-xs font-medium text-muted-foreground">开放服务</p>
              <div class="rounded-lg border border-border overflow-hidden">
                <table class="w-full text-xs">
                  <thead>
                    <tr class="bg-muted/40 border-b border-border">
                      <th class="px-3 py-1.5 text-left text-muted-foreground font-medium">端口</th>
                      <th class="px-3 py-1.5 text-left text-muted-foreground font-medium">协议</th>
                      <th class="px-3 py-1.5 text-left text-muted-foreground font-medium">服务</th>
                      <th class="px-3 py-1.5 text-left text-muted-foreground font-medium">版本</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="svc in ipInfo.services"
                      :key="svc.port"
                      class="border-b border-border/50 hover:bg-muted/20"
                    >
                      <td class="px-3 py-1.5 font-mono font-semibold">{{ svc.port }}</td>
                      <td class="px-3 py-1.5 text-muted-foreground">{{ svc.protocol }}</td>
                      <td class="px-3 py-1.5">{{ svc.service || '—' }}</td>
                      <td class="px-3 py-1.5 text-muted-foreground truncate max-w-[120px]">
                        {{ [svc.product, svc.version].filter(Boolean).join(' ') || '—' }}
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
            <div v-else-if="ipInfo.open_ports?.length" class="text-xs text-muted-foreground">
              开放端口: {{ ipInfo.open_ports.join(', ') }}
            </div>

            <p class="text-xs text-muted-foreground text-right">
              扫描时间: {{ formatTime(ipInfo.scanned_at) }}
            </p>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { defenseApi } from '@/api/defense'
import { apiClient } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Monitor, RefreshCw, Search, ShieldAlert, ShieldCheck, X } from 'lucide-vue-next'

interface ThreatEvent {
  id: number
  ip: string
  source: string
  ai_score: number
  ai_reason: string
  status: string
  created_at: string
}

interface IpScanInfo {
  ip: string
  hostname: string | null
  mac_address: string | null
  vendor: string | null
  state: string | null
  os_type: string | null
  os_accuracy: string | null
  open_ports: number[]
  services: {
    port: number
    protocol: string
    service: string
    product: string
    version: string
    extrainfo: string
  }[]
  scan_task_id: number
  scanned_at: string
}

const events = ref<ThreatEvent[]>([])
const loading = ref(false)
const pendingCount = ref(0)
const todayBlocked = ref(0)
const highRiskCount = ref(0)

// IP 关联查询
const ipInfoOpen = ref(false)
const ipInfoLoading = ref(false)
const currentIp = ref('')
const ipInfo = ref<IpScanInfo | null>(null)

const stats = computed(() => [
  {
    label: '待处置事件',
    value: pendingCount.value,
    icon: ShieldAlert,
    color: pendingCount.value > 0 ? 'text-amber-400' : 'text-foreground',
  },
  {
    label: '今日拦截',
    value: todayBlocked.value,
    icon: ShieldCheck,
    color: 'text-emerald-400',
  },
  {
    label: '高危 IP（≥80分）',
    value: highRiskCount.value,
    icon: ShieldAlert,
    color: highRiskCount.value > 0 ? 'text-red-400' : 'text-foreground',
  },
])

const loadEvents = async () => {
  loading.value = true
  try {
    const data = await defenseApi.getPendingEvents()
    // getPendingEvents 返回的是 response 对象，需要取 data
    const list = Array.isArray(data) ? data : (data as any)?.data?.items ?? []
    events.value = list
    pendingCount.value = list.length
    highRiskCount.value = list.filter((e: ThreatEvent) => e.ai_score >= 80).length
  } catch (error) {
    console.error('Failed to load events:', error)
  } finally {
    loading.value = false
  }
}

const approveEvent = async (eventId: number) => {
  try {
    await defenseApi.approveEvent(eventId, '管理员批准')
    await loadEvents()
  } catch (error) {
    console.error('Failed to approve event:', error)
  }
}

const rejectEvent = async (eventId: number) => {
  try {
    await defenseApi.rejectEvent(eventId, '管理员驳回')
    await loadEvents()
  } catch (error) {
    console.error('Failed to reject event:', error)
  }
}

const showIpInfo = async (ip: string) => {
  currentIp.value = ip
  ipInfo.value = null
  ipInfoOpen.value = true
  ipInfoLoading.value = true
  try {
    const res = await apiClient.get(`/defense/ip-info/${ip}`)
    ipInfo.value = res.data ?? null
  } catch {
    ipInfo.value = null
  } finally {
    ipInfoLoading.value = false
  }
}

const getScoreVariant = (score: number) =>
  score >= 80 ? ('destructive' as const) : ('secondary' as const)

const getScoreColor = (score: number) => {
  if (score >= 80) return ''
  if (score >= 50) return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
}

const formatTime = (t: string) =>
  t ? new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

onMounted(loadEvents)
</script>
