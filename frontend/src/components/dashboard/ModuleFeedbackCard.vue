<script setup lang="ts">
import { RefreshCw } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'

withDefaults(defineProps<{
  title: string
  description: string
  error?: string | null
  logs?: string[]
}>(), {
  error: null,
  logs: () => [],
})

defineEmits<{
  retry: []
}>()
</script>

<template>
  <div class="ops-feedback">
    <div class="ops-feedback-header">
      <div class="space-y-1">
        <p class="ops-feedback-title">{{ title }}</p>
        <p class="ops-feedback-copy">{{ description }}</p>
        <p v-if="error" class="ops-feedback-copy text-amber-300">{{ error }}</p>
      </div>
      <span class="ops-feedback-badge">需要处理</span>
    </div>

    <div class="ops-feedback-actions">
      <Button variant="outline" size="sm" class="cursor-pointer gap-1.5 rounded-full px-4" @click="$emit('retry')">
        <RefreshCw class="size-3.5" />
        重试
      </Button>

      <details v-if="logs.length" class="ops-feedback-details">
        <summary class="ops-feedback-link">查看日志</summary>
        <div class="ops-feedback-log-list">
          <pre v-for="(item, index) in logs" :key="`${index}-${item}`" class="ops-feedback-log">{{ item }}</pre>
        </div>
      </details>
    </div>
  </div>
</template>
