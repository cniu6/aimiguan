<template>
  <div class="scan-manager">
    <div class="header">
      <h1>扫描管理</h1>
      <button @click="showCreateModal = true" class="btn-primary">新建扫描</button>
    </div>

    <div class="tasks-section">
      <h2>扫描任务</h2>
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="tasks.length === 0" class="empty">暂无扫描任务</div>
      <div v-else class="tasks-list">
        <div v-for="task in tasks" :key="task.id" class="task-card">
          <div class="task-header">
            <span class="task-target">{{ task.target }}</span>
            <span class="task-state" :class="getStateClass(task.state)">{{ task.state }}</span>
          </div>
          <div class="task-body">
            <p class="task-tool">工具: {{ task.tool_name }}</p>
            <p class="task-time">创建时间: {{ formatTime(task.created_at) }}</p>
          </div>
          <div class="task-actions">
            <button @click="viewTask(task.id)" class="btn-view">查看详情</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Create Modal -->
    <div v-if="showCreateModal" class="modal-overlay" @click="showCreateModal = false">
      <div class="modal-content" @click.stop>
        <h3>新建扫描任务</h3>
        <div class="form-group">
          <label>目标地址</label>
          <input v-model="newTask.target" type="text" placeholder="192.168.1.1" />
        </div>
        <div class="form-group">
          <label>扫描工具</label>
          <select v-model="newTask.tool_name">
            <option value="nmap">Nmap</option>
          </select>
        </div>
        <div class="modal-actions">
          <button @click="createTask" class="btn-primary">创建</button>
          <button @click="showCreateModal = false" class="btn-secondary">取消</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { scanApi } from '@/api/scan'

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
const newTask = ref({
  target: '',
  tool_name: 'nmap'
})

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
  // TODO: Navigate to task detail page
}

const getStateClass = (state: string) => {
  const stateMap: Record<string, string> = {
    'PENDING': 'state-pending',
    'RUNNING': 'state-running',
    'COMPLETED': 'state-completed',
    'FAILED': 'state-failed'
  }
  return stateMap[state] || 'state-pending'
}

const formatTime = (time: string) => {
  return new Date(time).toLocaleString('zh-CN')
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.scan-manager {
  padding: 24px;
  max-width: 1400px;
  margin: 0 auto;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 32px;
}

.header h1 {
  font-size: 28px;
  font-weight: 600;
  color: #1E293B;
}

.btn-primary {
  padding: 10px 20px;
  background: #3B82F6;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-primary:hover {
  background: #2563EB;
}

.tasks-section h2 {
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

.tasks-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

.task-card {
  background: white;
  padding: 20px;
  border-radius: 8px;
  border: 1px solid #E2E8F0;
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-target {
  font-size: 16px;
  font-weight: 600;
  color: #1E293B;
}

.task-state {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 600;
}

.state-pending {
  background: #F1F5F9;
  color: #64748B;
}

.state-running {
  background: #DBEAFE;
  color: #2563EB;
}

.state-completed {
  background: #D1FAE5;
  color: #059669;
}

.state-failed {
  background: #FEE2E2;
  color: #DC2626;
}

.task-body {
  margin-bottom: 16px;
}

.task-tool, .task-time {
  color: #64748B;
  font-size: 14px;
  margin-bottom: 4px;
}

.btn-view {
  padding: 8px 16px;
  background: #F1F5F9;
  color: #475569;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-view:hover {
  background: #E2E8F0;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 24px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
}

.modal-content h3 {
  font-size: 20px;
  font-weight: 600;
  color: #1E293B;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  color: #475569;
  font-size: 14px;
  margin-bottom: 8px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px;
  border: 1px solid #E2E8F0;
  border-radius: 6px;
  font-size: 14px;
}

.modal-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  margin-top: 24px;
}

.btn-secondary {
  padding: 10px 20px;
  background: #F1F5F9;
  color: #475569;
  border: none;
  border-radius: 6px;
  font-size: 14px;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-secondary:hover {
  background: #E2E8F0;
}
</style>