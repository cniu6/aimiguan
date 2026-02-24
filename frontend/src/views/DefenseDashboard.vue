<template>
  <div class="p-6 max-w-[1400px] mx-auto space-y-6">
    <!-- Header -->
    <div class="space-y-1">
      <h1 class="text-3xl font-bold tracking-tight text-foreground">防御监控</h1>
      <p class="text-muted-foreground">实时威胁事件处置</p>
    </div>

    <!-- Stats -->
    <div class="grid gap-4 md:grid-cols-3">
      <Card v-for="stat in stats" :key="stat.label">
        <CardHeader class="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle class="text-sm font-medium">{{ stat.label }}</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="text-2xl font-bold">{{ stat.value }}</div>
        </CardContent>
      </Card>
    </div>

    <!-- Events -->
    <div class="space-y-4">
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold tracking-tight">待处置事件</h2>
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
        <Card v-for="event in events" :key="event.id" class="overflow-hidden transition-colors hover:bg-accent/50">
          <CardHeader class="pb-3">
            <div class="flex items-center justify-between">
              <code class="text-sm font-semibold">{{ event.ip }}</code>
              <Badge :variant="getScoreVariant(event.ai_score)" :class="getScoreColor(event.ai_score)">
                {{ event.ai_score }} 分
              </Badge>
            </div>
          </CardHeader>
          <CardContent class="space-y-3">
            <p class="text-sm text-muted-foreground leading-relaxed">{{ event.ai_reason }}</p>
            <p class="text-xs text-muted-foreground">来源: {{ event.source }}</p>
            <div class="flex gap-2 pt-2">
              <Button size="sm" class="cursor-pointer gap-2" @click="approveEvent(event.id)">
                <ShieldCheck class="size-4" />
                批准封禁
              </Button>
              <Button variant="outline" size="sm" class="cursor-pointer" @click="rejectEvent(event.id)">
                驳回
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { defenseApi } from '@/api/defense'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { ShieldCheck } from 'lucide-vue-next'

interface ThreatEvent {
  id: number
  ip: string
  source: string
  ai_score: number
  ai_reason: string
  status: string
  created_at: string
}

const events = ref<ThreatEvent[]>([])
const loading = ref(false)
const pendingCount = ref(0)
const todayBlocked = ref(0)
const highRiskCount = ref(0)

const stats = computed(() => [
  { label: '待处置事件', value: pendingCount.value },
  { label: '今日拦截', value: todayBlocked.value },
  { label: '高危 IP', value: highRiskCount.value },
])

const loadEvents = async () => {
  loading.value = true
  try {
    const data = await defenseApi.getPendingEvents()
    events.value = data
    pendingCount.value = data.length
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

const getScoreVariant = (score: number) => {
  return score >= 80 ? 'destructive' as const : 'secondary' as const
}

const getScoreColor = (score: number) => {
  if (score >= 80) return ''
  if (score >= 50) return 'bg-amber-500/20 text-amber-400 border-amber-500/30'
  return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
}

onMounted(() => {
  loadEvents()
})
</script>