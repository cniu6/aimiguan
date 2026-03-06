<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1200px] space-y-6">
      <!-- Header -->
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">插件与联动</h1>
        <p class="text-sm text-muted-foreground">管理 HFish 蜜罐接入、Nmap 网络扫描和推送通道配置</p>
      </div>

      <!-- ── HFish 配置 ── -->
      <Card>
        <CardHeader class="flex-row items-center justify-between pb-3">
          <div class="space-y-0.5">
            <CardTitle class="text-base flex items-center gap-2">
              <Bug class="size-4 text-amber-400" />
              HFish 蜜罐接入
            </CardTitle>
            <p class="text-xs text-muted-foreground">配置 HFish API 连接，启用蜜罐攻击日志自动同步</p>
          </div>
          <Badge :class="hfishConfig.enabled ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-muted text-muted-foreground'">
            {{ hfishConfig.enabled ? '已启用' : '未启用' }}
          </Badge>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-1.5">
              <label class="text-sm font-medium">HFish 地址（host:port）</label>
              <input
                v-model="hfishForm.host_port"
                type="text"
                placeholder="127.0.0.1:4433"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium">API 密钥</label>
              <input
                v-model="hfishForm.api_key"
                type="password"
                placeholder="留空则不修改当前密钥"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium">同步间隔（秒）</label>
              <input
                v-model.number="hfishForm.sync_interval"
                type="number"
                min="10"
                max="86400"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <p class="text-xs text-muted-foreground">最小 10 秒，建议 60 秒</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium">启用状态</label>
              <div class="flex items-center gap-3 pt-1.5">
                <button
                  type="button"
                  :class="[
                    'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors',
                    hfishForm.enabled ? 'bg-primary' : 'bg-input',
                  ]"
                  @click="hfishForm.enabled = !hfishForm.enabled"
                >
                  <span
                    :class="[
                      'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                      hfishForm.enabled ? 'translate-x-4' : 'translate-x-0',
                    ]"
                  />
                </button>
                <span class="text-sm text-muted-foreground">{{ hfishForm.enabled ? '自动同步已开启' : '自动同步已关闭' }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 pt-2 border-t border-border">
            <Button size="sm" class="cursor-pointer" :disabled="hfishSaving" @click="saveHFishConfig">
              <span v-if="hfishSaving">保存中…</span>
              <span v-else>保存配置</span>
            </Button>
            <Button
              variant="outline"
              size="sm"
              class="cursor-pointer gap-1.5"
              :disabled="!hfishConfig.enabled || hfishSyncing"
              @click="triggerHFishSync"
            >
              <RefreshCw class="size-3.5" :class="hfishSyncing ? 'animate-spin' : ''" />
              立即同步
            </Button>
            <span v-if="hfishMsg" :class="hfishMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs ml-1">
              {{ hfishMsg }}
            </span>
          </div>
        </CardContent>
      </Card>

      <!-- ── Nmap 配置 ── -->
      <Card>
        <CardHeader class="flex-row items-center justify-between pb-3">
          <div class="space-y-0.5">
            <CardTitle class="text-base flex items-center gap-2">
              <Radar class="size-4 text-blue-400" />
              Nmap 网络扫描
            </CardTitle>
            <p class="text-xs text-muted-foreground">配置 Nmap 可执行路径与扫描目标，启用定时探测</p>
          </div>
          <Badge :class="nmapConfig.enabled ? 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30' : 'bg-muted text-muted-foreground'">
            {{ nmapConfig.enabled ? '已启用' : '未启用' }}
          </Badge>
        </CardHeader>
        <CardContent class="space-y-4">
          <div class="grid gap-4 md:grid-cols-2">
            <div class="space-y-1.5 md:col-span-2">
              <label class="text-sm font-medium">Nmap 可执行路径</label>
              <input
                v-model="nmapForm.nmap_path"
                type="text"
                placeholder="C:\nmap\nmap.exe 或 /usr/bin/nmap"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>
            <div class="space-y-1.5 md:col-span-2">
              <label class="text-sm font-medium">扫描 IP 范围（每行一个）</label>
              <textarea
                v-model="nmapIpRangesText"
                rows="3"
                placeholder="192.168.1.0/24&#10;10.0.0.1-255&#10;172.16.0.100"
                class="w-full rounded-md border border-input bg-background px-3 py-2 text-sm shadow-sm placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring resize-none font-mono"
              />
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium">扫描间隔（秒）</label>
              <input
                v-model.number="nmapForm.scan_interval"
                type="number"
                min="60"
                class="h-9 w-full rounded-md border border-input bg-background px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
              />
              <p class="text-xs text-muted-foreground">默认 604800（7天）</p>
            </div>
            <div class="space-y-1.5">
              <label class="text-sm font-medium">启用状态</label>
              <div class="flex items-center gap-3 pt-1.5">
                <button
                  type="button"
                  :class="[
                    'relative inline-flex h-5 w-9 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors',
                    nmapForm.enabled ? 'bg-primary' : 'bg-input',
                  ]"
                  @click="nmapForm.enabled = !nmapForm.enabled"
                >
                  <span
                    :class="[
                      'pointer-events-none inline-block size-4 rounded-full bg-white shadow-lg ring-0 transition-transform',
                      nmapForm.enabled ? 'translate-x-4' : 'translate-x-0',
                    ]"
                  />
                </button>
                <span class="text-sm text-muted-foreground">{{ nmapForm.enabled ? '定时扫描已开启' : '定时扫描已关闭' }}</span>
              </div>
            </div>
          </div>

          <div class="flex items-center gap-2 pt-2 border-t border-border">
            <Button size="sm" class="cursor-pointer" :disabled="nmapSaving" @click="saveNmapConfig">
              <span v-if="nmapSaving">保存中…</span>
              <span v-else>保存配置</span>
            </Button>
            <span v-if="nmapMsg" :class="nmapMsgOk ? 'text-emerald-400' : 'text-destructive'" class="text-xs ml-1">
              {{ nmapMsg }}
            </span>
          </div>
        </CardContent>
      </Card>

      <!-- ── 其他联动状态 ── -->
      <div class="grid gap-4 md:grid-cols-3">
        <Card v-for="item in otherChannels" :key="item.name" class="opacity-70">
          <CardHeader class="pb-2">
            <CardTitle class="text-sm flex items-center gap-2">
              <component :is="item.icon" class="size-4 text-muted-foreground" />
              {{ item.name }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-xs text-muted-foreground">
            <p>{{ item.desc }}</p>
            <Badge class="bg-muted text-muted-foreground text-xs">待配置</Badge>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { Bug, RefreshCw, Shield, Bell, Zap } from 'lucide-vue-next'
import { defenseApi, type HFishConfig } from '@/api/defense'
import { scanApi } from '@/api/scan'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

// ── HFish 状态 ──
const hfishConfig = ref<HFishConfig>({ host_port: null, sync_interval: 60, enabled: false })
const hfishForm = reactive({ host_port: '', api_key: '', sync_interval: 60, enabled: false })
const hfishSaving = ref(false)
const hfishSyncing = ref(false)
const hfishMsg = ref('')
const hfishMsgOk = ref(true)

// ── Nmap 状态 ──
const nmapConfig = ref({ nmap_path: null as string | null, ip_ranges: [] as string[], scan_interval: 604800, enabled: false })
const nmapForm = reactive({ nmap_path: '', scan_interval: 604800, enabled: false })
const nmapIpRangesText = ref('')
const nmapSaving = ref(false)
const nmapMsg = ref('')
const nmapMsgOk = ref(true)

const showMsg = (msgRef: typeof hfishMsg, okRef: typeof hfishMsgOk, msg: string, ok: boolean) => {
  msgRef.value = msg
  okRef.value = ok
  setTimeout(() => { msgRef.value = '' }, 3000)
}

const loadHFishConfig = async () => {
  try {
    const cfg = await defenseApi.getHFishConfig()
    hfishConfig.value = cfg
    hfishForm.host_port = cfg.host_port ?? ''
    hfishForm.api_key = ''
    hfishForm.sync_interval = cfg.sync_interval
    hfishForm.enabled = cfg.enabled
  } catch {
    // 配置可能未初始化，忽略
  }
}

const loadNmapConfig = async () => {
  try {
    const cfg = await scanApi.getNmapConfig()
    nmapConfig.value = cfg
    nmapForm.nmap_path = cfg.nmap_path ?? ''
    nmapForm.scan_interval = cfg.scan_interval
    nmapForm.enabled = cfg.enabled
    nmapIpRangesText.value = cfg.ip_ranges.join('\n')
  } catch {
    // 未初始化忽略
  }
}

const saveHFishConfig = async () => {
  if (!hfishForm.host_port.trim()) {
    showMsg(hfishMsg, hfishMsgOk, '请填写 HFish 地址', false)
    return
  }
  hfishSaving.value = true
  try {
    await defenseApi.saveHFishConfig({
      host_port: hfishForm.host_port.trim(),
      api_key: hfishForm.api_key || '',
      sync_interval: hfishForm.sync_interval,
      enabled: hfishForm.enabled,
    })
    hfishConfig.value.enabled = hfishForm.enabled
    showMsg(hfishMsg, hfishMsgOk, '配置已保存', true)
  } catch (e: any) {
    showMsg(hfishMsg, hfishMsgOk, e?.response?.data?.detail || '保存失败', false)
  } finally {
    hfishSaving.value = false
  }
}

const triggerHFishSync = async () => {
  hfishSyncing.value = true
  try {
    const res: any = await defenseApi.triggerHFishSync()
    showMsg(hfishMsg, hfishMsgOk, res?.data?.message || '同步完成', true)
  } catch (e: any) {
    showMsg(hfishMsg, hfishMsgOk, e?.response?.data?.detail || '同步失败', false)
  } finally {
    hfishSyncing.value = false
  }
}

const saveNmapConfig = async () => {
  if (!nmapForm.nmap_path.trim()) {
    showMsg(nmapMsg, nmapMsgOk, '请填写 Nmap 路径', false)
    return
  }
  const ipRanges = nmapIpRangesText.value.split('\n').map(s => s.trim()).filter(Boolean)
  if (ipRanges.length === 0) {
    showMsg(nmapMsg, nmapMsgOk, '请填写至少一个扫描目标', false)
    return
  }
  nmapSaving.value = true
  try {
    await scanApi.saveNmapConfig({
      nmap_path: nmapForm.nmap_path.trim(),
      ip_ranges: ipRanges,
      scan_interval: nmapForm.scan_interval,
      enabled: nmapForm.enabled,
    })
    nmapConfig.value.enabled = nmapForm.enabled
    showMsg(nmapMsg, nmapMsgOk, '配置已保存', true)
  } catch (e: any) {
    showMsg(nmapMsg, nmapMsgOk, e?.response?.data?.detail || '保存失败', false)
  } finally {
    nmapSaving.value = false
  }
}

// Radar 图标用 Lucide 没有，用 Zap 代替
const Radar = Zap

const otherChannels = [
  { name: 'MCP 执行器', desc: '交换机封禁与回滚工具调用链路（stdio/sse 通信）', icon: Shield },
  { name: '异常推送', desc: '钉钉 / 企微 / 邮件通知通道配置', icon: Bell },
  { name: '防火墙同步', desc: '高风险 IP 外部防火墙封堵联动', icon: Zap },
]

onMounted(() => {
  loadHFishConfig()
  loadNmapConfig()
})
</script>
