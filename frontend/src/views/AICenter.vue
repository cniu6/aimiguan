<template>
  <div class="p-6 max-w-[1400px] mx-auto space-y-8">
    <!-- Header -->
    <div>
      <h1 class="text-2xl font-semibold text-foreground">AI 中枢</h1>
      <p class="text-sm text-muted-foreground mt-1">智能对话与分析</p>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-[2fr_1fr] gap-6">
      <!-- Chat section -->
      <Card class="flex flex-col h-[600px]">
        <CardHeader class="pb-3">
          <CardTitle class="text-base">AI 对话</CardTitle>
        </CardHeader>
        <CardContent class="flex-1 flex flex-col min-h-0 pt-0">
          <ScrollArea class="flex-1 pr-4">
            <div class="space-y-3 pb-2">
              <div v-if="messages.length === 0" class="flex flex-col items-center justify-center py-16 text-muted-foreground">
                <BrainCircuit class="size-10 opacity-30 mb-3" />
                <p class="text-sm">输入消息开始对话</p>
              </div>
              <div
                v-for="(msg, idx) in messages" :key="idx"
                class="flex"
                :class="msg.role === 'user' ? 'justify-end' : 'justify-start'"
              >
                <div
                  class="max-w-[80%] rounded-lg px-4 py-2.5 text-sm"
                  :class="msg.role === 'user'
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted text-foreground'"
                >
                  {{ msg.content }}
                </div>
              </div>
            </div>
          </ScrollArea>

          <Separator class="my-3" />

          <form @submit.prevent="sendMessage" class="flex gap-3">
            <Input
              v-model="inputMessage"
              placeholder="输入消息，如：分析 IP 1.2.3.4 ..."
              class="flex-1"
            />
            <Button type="submit" class="cursor-pointer" :disabled="!inputMessage.trim()">
              <Send class="size-4" />
              发送
            </Button>
          </form>
        </CardContent>
      </Card>

      <!-- Report section -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base">AI 报告</CardTitle>
        </CardHeader>
        <CardContent class="space-y-4 pt-0">
          <div class="flex gap-3">
            <Button variant="outline" size="sm" class="cursor-pointer" @click="generateReport('daily')">
              <FileText class="size-4" />
              生成日报
            </Button>
            <Button variant="outline" size="sm" class="cursor-pointer" @click="generateReport('weekly')">
              <FileText class="size-4" />
              生成周报
            </Button>
          </div>

          <Separator />

          <ScrollArea class="h-[440px]">
            <div v-if="reports.length === 0" class="text-center py-10 text-muted-foreground">
              <FileText class="size-10 mx-auto mb-3 opacity-30" />
              <p class="text-sm">暂无报告</p>
            </div>
            <div v-else class="space-y-3">
              <Card v-for="report in reports" :key="report.id" class="bg-muted/50">
                <CardContent class="pt-0 space-y-1">
                  <p class="font-medium text-sm text-foreground">{{ report.report_type }}</p>
                  <p class="text-sm text-muted-foreground line-clamp-2">{{ report.summary }}</p>
                  <p class="text-xs text-muted-foreground/60">{{ formatTime(report.created_at) }}</p>
                </CardContent>
              </Card>
            </div>
          </ScrollArea>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { aiApi } from '@/api/ai'
import { reportApi } from '@/api/report'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { ScrollArea } from '@/components/ui/scroll-area'
import { BrainCircuit, Send, FileText } from 'lucide-vue-next'

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

const formatTime = (time: string) => new Date(time).toLocaleString('zh-CN')

onMounted(() => { loadReports() })
</script>