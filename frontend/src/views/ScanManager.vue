<template>
  <div class="p-6 max-w-[1400px] mx-auto space-y-6">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <div class="space-y-1">
        <h1 class="text-3xl font-bold tracking-tight text-foreground">扫描管理</h1>
        <p class="text-muted-foreground">创建和管理扫描任务</p>
      </div>
      <Dialog v-model:open="showCreateModal">
        <DialogTrigger as-child>
          <Button class="cursor-pointer gap-2">
            <Plus class="size-4" />
            新建扫描
          </Button>
        </DialogTrigger>
        <DialogContent class="sm:max-w-[425px]">
          <DialogHeader>
            <DialogTitle>新建扫描任务</DialogTitle>
            <DialogDescription>输入目标地址和扫描工具创建新任务</DialogDescription>
          </DialogHeader>
          <form @submit.prevent="createTask" class="space-y-4 pt-2">
            <div class="space-y-2">
              <Label for="target">目标地址</Label>
              <Input id="target" v-model="newTask.target" placeholder="192.168.1.1" />
            </div>
            <div class="space-y-2">
              <Label for="tool">扫描工具</Label>
              <Select v-model="newTask.tool_name">
                <SelectTrigger>
                  <SelectValue placeholder="选择工具" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="nmap">Nmap</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button variant="outline" type="button" class="cursor-pointer" @click="showCreateModal = false">取消</Button>
              <Button type="submit" class="cursor-pointer">创建</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>

    <!-- Tasks -->
    <div class="space-y-4">
      <h2 class="text-xl font-semibold tracking-tight">扫描任务</h2>

      <div v-if="loading" class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Skeleton v-for="i in 3" :key="i" class="h-[160px] w-full rounded-lg" />
      </div>

      <Card v-else-if="tasks.length === 0" class="border-dashed">
        <CardContent class="flex flex-col items-center justify-center py-12">
          <Search class="size-12 text-muted-foreground/40 mb-4" />
          <p class="text-sm text-muted-foreground">暂无扫描任务</p>
        </CardContent>
      </Card>

      <div v-else class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        <Card v-for="task in tasks" :key="task.id" class="overflow-hidden transition-colors hover:bg-accent/50">
          <CardHeader class="pb-3">
            <div class="flex items-center justify-between">
              <code class="text-sm font-semibold">{{ task.target }}</code>
              <Badge :variant="getStateVariant(task.state)" :class="getStateColor(task.state)">
                {{ task.state }}
              </Badge>
            </div>
          </CardHeader>
          <CardContent class="space-y-3">
            <p class="text-sm text-muted-foreground">工具: {{ task.tool_name }}</p>
            <p class="text-xs text-muted-foreground">{{ formatTime(task.created_at) }}</p>
            <Button variant="outline" size="sm" class="w-full cursor-pointer gap-2" @click="viewTask(task.id)">
              <Eye class="size-4" />
              查看详情
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { scanApi } from '@/api/scan'
import { Card, CardContent, CardHeader } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Plus, Search, Eye } from 'lucide-vue-next'

interface ScanTask {
  id: number
  target: string
  tool_name: string
  state: string
  created_at: string
}

const tasks = ref<ScanTask[]>([])
const loading = ref(false)
const showCreateModal = ref(false)
const newTask = ref({ target: '', tool_name: 'nmap' })

const loadTasks = async () => {
  loading.value = true
  try {
    const data = await scanApi.getTasks()
    tasks.value = data
  } catch (error) {
    console.error('Failed to load tasks:', error)
  } finally {
    loading.value = false
  }
}

const createTask = async () => {
  try {
    await scanApi.createTask(newTask.value)
    showCreateModal.value = false
    newTask.value = { target: '', tool_name: 'nmap' }
    await loadTasks()
  } catch (error) {
    console.error('Failed to create task:', error)
  }
}

const viewTask = (taskId: number) => {
  console.log('View task:', taskId)
}

const getStateVariant = (state: string) => {
  return state === 'FAILED' ? 'destructive' as const : 'secondary' as const
}

const getStateColor = (state: string) => {
  const map: Record<string, string> = {
    PENDING: 'bg-muted text-muted-foreground',
    RUNNING: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    COMPLETED: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    FAILED: '',
  }
  return map[state] || ''
}

const formatTime = (time: string) => new Date(time).toLocaleString('zh-CN')

onMounted(() => { loadTasks() })
</script>