<script setup lang="ts">
import { Monitor, X } from 'lucide-vue-next'
import { Skeleton } from '@/components/ui/skeleton'

export interface NmapHostInfo {
  ip?: string
  mac_address?: string | null
  vendor?: string | null
  hostname?: string | null
  state?: string | null
  os_type?: string | null
  os_accuracy?: string | null
  open_ports?: number[]
  services?: {
    port: number | string
    protocol?: string
    service?: string
    product?: string
    version?: string
    extrainfo?: string
  }[]
  scanned_at?: string | null
}

const props = withDefaults(defineProps<{
  open: boolean
  ip?: string
  host: NmapHostInfo | null
  loading?: boolean
  title?: string
}>(), {
  loading: false,
  title: 'IP 扫描详情',
})

const emit = defineEmits<{ 'update:open': [value: boolean] }>()

const close = () => emit('update:open', false)

const formatTime = (t?: string | null) => {
  if (!t) return '—'
  return t.replace('T', ' ').slice(0, 19)
}
</script>

<template>
  <div
    v-if="open"
    class="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
    @click.self="close"
  >
    <div class="mx-4 w-full max-w-lg rounded-xl border border-border bg-background shadow-2xl max-h-[80vh] flex flex-col">
      <!-- 标题栏 -->
      <div class="flex items-center justify-between border-b border-border px-5 py-4 shrink-0">
        <div class="flex items-center gap-2">
          <Monitor class="size-4 text-primary" />
          <span class="font-semibold text-sm">{{ title }}</span>
          <code v-if="ip" class="text-xs text-muted-foreground ml-1">{{ ip }}</code>
        </div>
        <button class="text-muted-foreground hover:text-foreground transition-colors" @click="close">
          <X class="size-4" />
        </button>
      </div>

      <!-- 内容 -->
      <div class="p-5 space-y-4 overflow-y-auto">
        <!-- 加载骨架 -->
        <div v-if="loading" class="space-y-3">
          <Skeleton v-for="i in 4" :key="i" class="h-8 w-full rounded" />
        </div>

        <!-- 未找到记录 -->
        <div v-else-if="!host" class="py-8 text-center">
          <Monitor class="size-10 text-muted-foreground/30 mx-auto mb-3" />
          <p class="text-sm text-muted-foreground">未找到该 IP 的 Nmap 扫描记录</p>
          <p class="text-xs text-muted-foreground mt-1">请先在「探测扫描」中对该 IP 范围执行扫描</p>
        </div>

        <!-- 主机信息 -->
        <template v-else>
          <div class="grid grid-cols-2 gap-3 text-sm">
            <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
              <p class="text-xs text-muted-foreground">操作系统</p>
              <p class="font-medium">{{ host.os_type || '未识别' }}</p>
              <p v-if="host.os_accuracy" class="text-xs text-muted-foreground">精确度 {{ host.os_accuracy }}%</p>
            </div>
            <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
              <p class="text-xs text-muted-foreground">主机名 / 厂商</p>
              <p class="font-medium">{{ host.hostname || '—' }}</p>
              <p class="text-xs text-muted-foreground">{{ host.vendor || '未知厂商' }}</p>
            </div>
            <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
              <p class="text-xs text-muted-foreground">MAC 地址</p>
              <code class="text-xs">{{ host.mac_address || '—' }}</code>
            </div>
            <div class="rounded-lg border border-border px-3 py-2.5 space-y-0.5">
              <p class="text-xs text-muted-foreground">开放端口数</p>
              <p class="font-semibold text-primary">{{ host.open_ports?.length ?? 0 }}</p>
            </div>
          </div>

          <!-- 开放服务 -->
          <div v-if="host.services?.length" class="space-y-1.5">
            <p class="text-xs font-medium text-muted-foreground">开放服务（{{ host.services.length }} 个）</p>
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
                    v-for="svc in host.services"
                    :key="svc.port"
                    class="border-b border-border/50 hover:bg-muted/20"
                  >
                    <td class="px-3 py-1.5 font-mono font-semibold">{{ svc.port }}</td>
                    <td class="px-3 py-1.5 text-muted-foreground">{{ svc.protocol || 'tcp' }}</td>
                    <td class="px-3 py-1.5">{{ svc.service || '—' }}</td>
                    <td class="px-3 py-1.5 text-muted-foreground truncate max-w-[120px]">
                      {{ [svc.product, svc.version].filter(Boolean).join(' ') || '—' }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div v-else-if="host.open_ports?.length" class="text-xs text-muted-foreground">
            开放端口: {{ host.open_ports.join(', ') }}
          </div>

          <p class="text-xs text-muted-foreground text-right">
            扫描时间: {{ formatTime(host.scanned_at) }}
          </p>
        </template>
      </div>
    </div>
  </div>
</template>
