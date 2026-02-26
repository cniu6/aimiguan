<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">插件与联动</h1>
        <p class="text-sm text-muted-foreground">管理 MCP 插件、推送通道与外部系统联动状态</p>
      </div>

      <div class="grid gap-4 lg:grid-cols-3">
        <Card v-for="item in channels" :key="item.name">
          <CardHeader>
            <CardTitle class="text-base">{{ item.name }}</CardTitle>
          </CardHeader>
          <CardContent class="space-y-2 text-sm text-muted-foreground">
            <p>{{ item.desc }}</p>
            <p>
              状态：
              <span :class="item.enabled ? 'text-emerald-500' : 'text-amber-500'">
                {{ item.enabled ? '已启用' : '待配置' }}
              </span>
            </p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">联动 TODO</CardTitle>
        </CardHeader>
        <CardContent class="space-y-2 text-sm text-muted-foreground">
          <div class="rounded-md border border-border px-3 py-2">接入真实 MCP `stdio/sse` 并补充失败分类</div>
          <div class="rounded-md border border-border px-3 py-2">补齐 `push_channel` 配置与测试告警发送</div>
          <div class="rounded-md border border-border px-3 py-2">补齐外部防火墙回执链路与幂等键校验</div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

const channels = computed(() => [
  { name: 'MCP 执行器', desc: '交换机封禁与回滚工具调用链路', enabled: false },
  { name: '异常推送', desc: '钉钉 / 企微 / 邮件通知通道', enabled: false },
  { name: '防火墙同步', desc: '高风险 IP 外部防火墙封堵联动', enabled: false },
])
</script>
