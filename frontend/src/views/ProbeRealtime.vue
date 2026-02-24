<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1400px] space-y-6">
      <div>
        <h1 class="text-2xl font-semibold">实时检测</h1>
        <p class="mt-1 text-sm text-muted-foreground">主动探测模式下的实时扫描监控大屏</p>
      </div>

      <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardHeader><CardTitle class="text-base">运行中任务</CardTitle></CardHeader>
          <CardContent class="text-3xl font-semibold">7</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle class="text-base">今日扫描资产</CardTitle></CardHeader>
          <CardContent class="text-3xl font-semibold">142</CardContent>
        </Card>
        <Card>
          <CardHeader><CardTitle class="text-base">高危漏洞命中</CardTitle></CardHeader>
          <CardContent class="text-3xl font-semibold">19</CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle class="text-base">实时探测流</CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid gap-3 text-sm text-muted-foreground md:grid-cols-2">
            <div class="rounded-md border border-border bg-card p-3">[01:31:05] 任务启动: 172.16.10.0/24</div>
            <div class="rounded-md border border-border bg-card p-3">[01:31:12] 端口发现: 22, 445, 3389</div>
            <div class="rounded-md border border-border bg-card p-3">[01:31:18] NSE 命中: smb-vuln-ms17-010</div>
            <div class="rounded-md border border-border bg-card p-3">[01:31:26] AI 解读完成: 风险等级 HIGH</div>
          </div>
        </CardContent>
      </Card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
</script>
