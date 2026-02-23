<template>
  <div class="defense-dashboard">
    <div class="header">
      <h1>防御监控</h1>
      <p class="subtitle">实时威胁事件处置</p>
    </div>

    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-label">待处置事件</div>
        <div class="stat-value">{{ pendingCount }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">今日拦截</div>
        <div class="stat-value">{{ todayBlocked }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-label">高危 IP</div>
        <div class="stat-value">{{ highRiskCount }}</div>
      </div>
    </div>

    <div class="events-section">
      <h2>待处置事件</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="events.length === 0" class="empty">暂无待处置事件</div>
      <div v-else class="events-list">
        <div v-for="event in events" :key="event.id" class="event-card">
          <div class="event-header">
            <span class="event-ip">{{ event.ip }}</span>
            <span class="event-score" :class="getScoreClass(event.ai_score)">{{ event.ai_score }}</span>
          </div>
          <div class="event-body">
            <p class="event-reason">{{ event.ai_reason }}</p>
            <p class="event-source">来源: {{ event.source }}</p>
          </div>
          <div class="event-actions">
            <button @click="approveEvent(event.id)" class="btn-approve">批准封禁</button>
            <button @click="rejectEvent(event.id)" class="btn-reject">驳回</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { defenseApi } from '@/api/defense'

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

const getScoreClass = (score: number) => {
  if (score >= 80) return 'score-high'
  if (score >= 50) return 'score-medium'
  return 'score-low'
}

onMounted(() => {
  loadEvents()
})
</script>

<style scoped>
.defense-dashboard {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 8px;
}

.subtitle {
  color: #64748B;
  font-size: 14px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 16px;
  margin-bottom: 32px;
}

.stat-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
}

.stat-label {
  color: #64748B;
  font-size: 14px;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 600;
  color: #1E293B;
}

.events-section h2 {
  font-size: 20px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 16px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #64748B;
}

.events-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.event-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.event-ip {
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

.event-score {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
  font-weight: 600;
}

.score-high {
  background: #FEE2E2;
  color: #DC2626;
}

.score-medium {
  background: #FEF3C7;
  color: #D97706;
}

.score-low {
  background: #DBEAFE;
  color: #2563EB;
}

.event-body {
  margin-bottom: 16px;
}

.event-reason {
  color: #475569;
  margin-bottom: 8px;
}

.event-source {
  color: #94A3B8;
  font-size: 14px;
}

.event-actions {
  display: flex;
  gap: 12px;
}

.btn-approve, .btn-reject {
  padding: 8px 16px;
  border-radius: 6px;
  border: none;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-approve {
  background: #3B82F6;
  color: white;
}

.btn-approve:hover {
  background: #2563EB;
}

.btn-reject {
  background: #F1F5F9;
  color: #475569;
}

.btn-reject:hover {
  background: #E2E8F0;
}
</style>