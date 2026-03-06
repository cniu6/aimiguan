<template>
  <div class="p-6 max-w-[1400px] mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight text-foreground">防御监控</h1>
        <p class="text-muted-foreground">威胁事件处置 & HFish 攻击日志</p>
      </div>
      <Button variant="outline" size="sm" class="cursor-pointer gap-1.5" :disabled="loading" @click="onRefresh">
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

    <!-- Tabs: 待处置事件 / 攻击日志 -->
    <Tabs v-model="activeTab" class="space-y-4">
      <TabsList class="bg-muted/50">
        <TabsTrigger value="events" class="gap-2">
          <ShieldAlert class="size-4" />
          待处置事件
          <Badge v-if="pendingCount > 0" variant="secondary" class="ml-1 h-5 px-1.5 text-xs bg-amber-500/20 text-amber-400">{{ pendingCount }}</Badge>
        </TabsTrigger>
        <TabsTrigger value="logs" class="gap-2">
          <Activity class="size-4" />
          HFish 攻击日志
          <Badge v-if="logTotal > 0" variant="secondary" class="ml-1 h-5 px-1.5 text-xs">{{ logTotal }}</Badge>
        </TabsTrigger>
      </TabsList>

      <!-- ===== Tab: 待处置事件 ===== -->
      <TabsContent value="events" class="space-y-3">
        <div v-if="loading" class="space-y-3">
          <Skeleton v-for="i in 3" :key="i" class="h-[140px] w-full rounded-lg" />
        </div>
        <Card v-else-if="events.length === 0" class="border-dashed">
          <CardContent class="flex flex-col items-center justify-center py-12">
            <ShieldCheck class="size-12 text-muted-foreground/40 mb-4" />
            <p class="text-sm text-muted-foreground">暂无待处置事件</p>
          </CardContent>
        </Card>
        <div v-else class="space-y-3">
          <Card
            v-for="event in events"
            :key="event.id"
            class="overflow-hidden transition-colors hover:bg-accent/50"
          >
            <CardHeader class="pb-3">
              <div class="flex items-center justify-between">
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
      </TabsContent>

      <!-- ===== Tab: HFish 攻击日志 ===== -->
      <TabsContent value="logs" class="space-y-4">
        <!-- 筛选栏 -->
        <div class="flex items-center gap-3 flex-wrap">
          <!-- 威胁等级筛选 -->
          <div class="flex gap-1 flex-wrap">
            <Button
              v-for="lv in ['', '高', '中', '低']"
              :key="lv"
              :variant="logThreatFilter === lv ? 'default' : 'outline'"
              size="sm"
              class="cursor-pointer"
              @click="logThreatFilter = lv; loadLogs(0)"
            >
              <span v-if="lv === ''" class="text-xs">全部</span>
              <span v-else :class="threatLevelClass(lv)" class="text-xs font-medium">{{ lv }}危</span>
            </Button>
          </div>

          <!-- 服务名筛选 -->
          <select
            v-model="logServiceFilter"
            class="h-8 rounded-md border border-border bg-background px-2 text-sm text-foreground"
            @change="loadLogs(0)"
          >
            <option value="">全部服务</option>
            <option v-for="svc in serviceOptions" :key="svc" :value="svc">{{ svc }}</option>
          </select>

          <Button variant="outline" size="sm" class="cursor-pointer gap-1 ml-auto" :disabled="logLoading" @click="loadLogs(logOffset)">
            <RefreshCw class="size-3.5" :class="logLoading ? 'animate-spin' : ''" />
            刷新
          </Button>
        </div>

        <!-- 日志表格 -->
        <div class="rounded-lg border border-border overflow-hidden">
          <table class="w-full text-sm">
            <thead>
              <tr class="bg-muted/30 border-b border-border">
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">攻击 IP</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">归属地</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">蜜罐节点</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">服务/端口</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">威胁等级</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">时间</th>
                <th class="px-4 py-2.5 text-left text-xs font-medium text-muted-foreground">操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="logLoading">
                <td colspan="7" class="text-center py-10 text-muted-foreground text-sm">加载中...</td>
              </tr>
              <tr v-else-if="logs.length === 0">
                <td colspan="7" class="py-12">
                  <div class="flex flex-col items-center gap-2 text-muted-foreground">
                    <Activity class="size-10 opacity-30" />
                    <span class="text-sm">暂无攻击日志</span>
                  </div>
                </td>
              </tr>
              <tr
                v-for="log in logs"
                :key="log.id"
                class="border-b border-border/50 hover:bg-muted/20"
              >
                <td class="px-4 py-2.5">
                  <button
                    class="font-mono text-xs font-medium hover:text-primary transition-colors flex items-center gap-1 cursor-pointer"
                    @click="showIpInfo(log.attack_ip)"
                  >
                    {{ log.attack_ip }}
                    <Search class="size-2.5 opacity-50" />
                  </button>
                </td>
                <td class="px-4 py-2.5 text-xs text-muted-foreground">{{ log.ip_location || '—' }}</td>
                <td class="px-4 py-2.5 text-xs text-muted-foreground">{{ log.client_name || log.client_id || '—' }}</td>
                <td class="px-4 py-2.5 text-xs">
                  <span class="font-medium">{{ log.service_name }}</span>
                  <span v-if="log.service_port" class="text-muted-foreground ml-1">:{{ log.service_port }}</span>
                </td>
                <td class="px-4 py-2.5">
                  <Badge :class="threatBadgeClass(log.threat_level)" class="text-xs">{{ log.threat_level || '—' }}</Badge>
                </td>
                <td class="px-4 py-2.5 text-xs text-muted-foreground">{{ log.create_time_str }}</td>
                <td class="px-4 py-2.5">
                  <Button variant="ghost" size="sm" class="cursor-pointer h-6 text-xs gap-1" @click="showIpInfo(log.attack_ip)">
                    <Search class="size-3" />
                    扫描
                  </Button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- 分页 -->
        <div class="flex items-center justify-between text-sm text-muted-foreground">
          <span>共 {{ logTotal }} 条记录</span>
          <div class="flex items-center gap-2">
            <Button variant="outline" size="sm" class="cursor-pointer" :disabled="logOffset === 0 || logLoading" @click="loadLogs(logOffset - LOG_LIMIT)">
              上一页
            </Button>
            <span class="text-xs px-2">第 {{ Math.floor(logOffset / LOG_LIMIT) + 1 }} 页</span>
            <Button variant="outline" size="sm" class="cursor-pointer" :disabled="logOffset + LOG_LIMIT >= logTotal || logLoading" @click="loadLogs(logOffset + LOG_LIMIT)">
              下一页
            </Button>
          </div>
        </div>
      </TabsContent>
    </Tabs>

    <!-- IP 关联查询弹窗 -->
    <NmapHostDetailDialog
      v-model:open="ipInfoOpen"
      :ip="currentIp"
      :host="ipInfo"
      :loading="ipInfoLoading"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref, onMounted, watch } from 'vue'
import { defenseApi, type HFishLog } from '@/api/defense'
import { apiClient } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Activity, Monitor, RefreshCw, Search, ShieldAlert, ShieldCheck, X } from 'lucide-vue-next'
import NmapHostDetailDialog from '@/components/NmapHostDetailDialog.vue'

interface ThreatEvent {
  id: number; ip: string; source: string; ai_score: number; ai_reason: string; status: string; created_at: string
}
interface IpScanInfo {
  ip: string; hostname: string | null; mac_address: string | null; vendor: string | null; state: string | null
  os_type: string | null; os_accuracy: string | null; open_ports: number[]; scanned_at: string
  services: { port: number; protocol: string; service: string; product: string; version: string; extrainfo: string }[]
}

const LOG_LIMIT = 50

const activeTab = ref('events')
const loading = ref(false)
const events = ref<ThreatEvent[]>([])
const pendingCount = ref(0)
const todayBlocked = ref(0)
const highRiskCount = ref(0)

// 攻击日志
const logs = ref<HFishLog[]>([])
const logLoading = ref(false)
const logOffset = ref(0)
const logTotal = ref(0)
const logThreatFilter = ref('')
const logServiceFilter = ref('')
const serviceOptions = ref<string[]>([])

// IP 弹窗
const ipInfoOpen = ref(false)
const ipInfoLoading = ref(false)
const currentIp = ref('')
const ipInfo = ref<IpScanInfo | null>(null)

const stats = computed(() => [
  { label: '待处置事件', value: pendingCount.value, icon: ShieldAlert, color: pendingCount.value > 0 ? 'text-amber-400' : 'text-foreground' },
  { label: '今日拦截', value: todayBlocked.value, icon: ShieldCheck, color: 'text-emerald-400' },
  { label: '高危 IP（≥80分）', value: highRiskCount.value, icon: ShieldAlert, color: highRiskCount.value > 0 ? 'text-red-400' : 'text-foreground' },
])

const loadEvents = async () => {
  loading.value = true
  try {
    const data = await defenseApi.getPendingEvents()
    const list = Array.isArray(data) ? data : (data as any)?.data?.items ?? []
    events.value = list
    pendingCount.value = list.length
    highRiskCount.value = list.filter((e: ThreatEvent) => e.ai_score >= 80).length
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

const loadLogs = async (offset = 0) => {
  logLoading.value = true
  logOffset.value = offset
  try {
    const result = await defenseApi.getHFishLogs({
      limit: LOG_LIMIT,
      offset,
      threat_level: logThreatFilter.value || undefined,
      service_name: logServiceFilter.value || undefined,
    })
    logs.value = result.items
    logTotal.value = result.total
    // 首次加载时拉取服务下拉选项
    if (offset === 0 && !serviceOptions.value.length) {
      try {
        const stats = await defenseApi.getHFishStats()
        serviceOptions.value = (stats.service_stats ?? []).map((s: any) => s.name).filter(Boolean)
      } catch { /* ignore */ }
    }
  } catch (e) {
    console.error(e)
  } finally {
    logLoading.value = false
  }
}

const approveEvent = async (id: number) => {
  try { await defenseApi.approveEvent(id, '管理员批准'); await loadEvents() } catch (e) { console.error(e) }
}
const rejectEvent = async (id: number) => {
  try { await defenseApi.rejectEvent(id, '管理员驳回'); await loadEvents() } catch (e) { console.error(e) }
}

const showIpInfo = async (ip: string) => {
  currentIp.value = ip; ipInfo.value = null; ipInfoOpen.value = true; ipInfoLoading.value = true
  try {
    const res = await apiClient.get(`/defense/ip-info/${ip}`)
    ipInfo.value = res.data ?? null
  } catch { ipInfo.value = null } finally { ipInfoLoading.value = false }
}

const onRefresh = () => {
  if (activeTab.value === 'events') loadEvents()
  else loadLogs(logOffset.value)
}

// 切到日志 Tab 时自动加载
watch(activeTab, (tab) => {
  if (tab === 'logs' && logs.value.length === 0) loadLogs(0)
})

const threatLevelClass = (lv: string) => {
  if (lv === '高') return 'text-red-400'
  if (lv === '中') return 'text-amber-400'
  return 'text-blue-400'
}
const threatBadgeClass = (lv: string) => {
  if (lv === '高') return 'bg-red-500/15 text-red-400 border-red-500/30'
  if (lv === '中') return 'bg-amber-500/15 text-amber-400 border-amber-500/30'
  if (lv === '低') return 'bg-blue-500/15 text-blue-400 border-blue-500/30'
  return 'bg-muted text-muted-foreground'
}
const getScoreVariant = (score: number) => score >= 80 ? ('destructive' as const) : ('secondary' as const)
const getScoreColor = (score: number) => {
  if (score >= 80) return ''
  if (score >= 50) return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
}
const formatTime = (t: string) =>
  t ? new Date(t).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) : '—'

onMounted(loadEvents)
</script>
