<template>
  <div class="ai-center">
    <div class="header">
      <h1>AI 中枢</h1>
      <p class="subtitle">智能对话与分析</p>
    </div>

    <div class="content-grid">
      <div class="chat-section">
        <h2>AI 对话</h2>
        <div class="chat-container">
          <div class="messages">
            <div v-for="(msg, idx) in messages" :key="idx" class="message" :class="msg.role">
              <div class="message-content">{{ msg.content }}</div>
            </div>
          </div>
          <div class="input-area">
            <input
              v-model="inputMessage"
              @keyup.enter="sendMessage"
              type="text"
              placeholder="输入消息..."
            />
            <button @click="sendMessage" class="btn-send">发送</button>
          </div>
        </div>
      </div>

      <div class="report-section">
        <h2>AI 报告</h2>
        <div class="report-types">
          <button @click="generateReport('daily')" class="report-btn">生成日报</button>
          <button @click="generateReport('weekly')" class="report-btn">生成周报</button>
        </div>
        <div v-if="reports.length > 0" class="reports-list">
          <div v-for="report in reports" :key="report.id" class="report-item">
            <div class="report-type">{{ report.report_type }}</div>
            <div class="report-summary">{{ report.summary }}</div>
            <div class="report-time">{{ formatTime(report.created_at) }}</div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { aiApi } from '@/api/ai'
import { reportApi } from '@/api/report'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface Report {
  id: number
  report_type: string
  summary: string
  created_at: string
}

const messages = ref<Message[]>([])
const inputMessage = ref('')
const reports = ref<Report[]>([])

const sendMessage = async () => {
  if (!inputMessage.value.trim()) return

  const userMessage = inputMessage.value
  messages.value.push({ role: 'user', content: userMessage })
  inputMessage.value = ''

  try {
    const response = await aiApi.chat(userMessage)
    messages.value.push({ role: 'assistant', content: response.message })
  } catch (error) {
    console.error('Failed to send message:', error)
    messages.value.push({ role: 'assistant', content: '抱歉，发生错误' })
  }
}

const generateReport = async (type: string) => {
  try {
    await reportApi.generate(type)
    await loadReports()
  } catch (error) {
    console.error('Failed to generate report:', error)
  }
}

const loadReports = async () => {
  try {
    const data = await reportApi.getReports()
    reports.value = data
  } catch (error) {
    console.error('Failed to load reports:', error)
  }
}

const formatTime = (time: string) => {
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadReports()
})
</script>

<style scoped>
.ai-center {
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

.content-grid {
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: 24px;
}

.chat-section, .report-section {
  background: white;
  padding: 24px;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
}

.chat-section h2, .report-section h2 {
  font-size: 18px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 16px;
}

.chat-container {
  display: flex;
  flex-direction: column;
  height: 500px;
}

.messages {
  flex: 1;
  overflow-y: auto;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.message {
  padding: 12px 16px;
  border-radius: 8px;
  max-width: 80%;
}

.message.user {
  background: #3B82F6;
  color: white;
  align-self: flex-end;
}

.message.assistant {
  background: #F1F5F9;
  color: #1E293B;
  align-self: flex-start;
}

.input-area {
  display: flex;
  gap: 12px;
}

.input-area input {
  flex: 1;
  padding: 10px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 14px;
}

.btn-send {
  padding: 10px 20px;
  background: #3B82F6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-send:hover {
  background: #2563EB;
}

.report-types {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}

.report-btn {
  padding: 10px 20px;
  background: #F1F5F9;
  color: #475569;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.report-btn:hover {
  background: #E2E8F0;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-item {
  padding: 16px;
  background: #F8FAFC;
  border-radius: 6px;
}

.report-type {
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 8px;
}

.report-summary {
  color: #64748B;
  font-size: 14px;
  margin-bottom: 8px;
}

.report-time {
  color: #94A3B8;
  font-size: 12px;
}

@media (max-width: 768px) {
  .content-grid {
    grid-template-columns: 1fr;
  }
}
</style>