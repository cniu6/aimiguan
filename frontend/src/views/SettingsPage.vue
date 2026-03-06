<template>
  <div class="p-6">
    <div class="mx-auto max-w-[1200px] space-y-6">
      <!-- Header -->
      <div class="space-y-1">
        <h1 class="text-2xl font-semibold">系统设置</h1>
        <p class="text-sm text-muted-foreground">系统级配置与管理入口</p>
      </div>

      <!-- 系统运行架构说明 -->
      <Card>
        <CardHeader class="pb-3 flex-row items-center justify-between">
          <div class="space-y-0.5">
            <CardTitle class="text-base flex items-center gap-2">
              <Shield class="size-4 text-primary" />
              系统运行架构
            </CardTitle>
            <p class="text-xs text-muted-foreground">防御坚守与主动探测的运行机制说明</p>
          </div>
          <Badge class="bg-blue-500/15 text-blue-400 border-blue-500/30">
            防御坚守持续运行中
          </Badge>
        </CardHeader>
        <CardContent class="space-y-3">
          <div class="grid gap-3 sm:grid-cols-2">
            <!-- 防御坚守 -->
            <div class="rounded-lg border-2 border-blue-500/40 bg-blue-500/5 p-4">
              <div class="flex items-center gap-2 mb-1.5">
                <Shield class="size-4 text-blue-400" />
                <span class="font-semibold text-sm text-blue-400">防御坚守（始终运行）</span>
              </div>
              <p class="text-xs text-muted-foreground leading-relaxed">
                后台持续采集 HFish 蜜罐告警、AI 评分、审批执行封禁，全程自动运行，无需手动开启。
                这是系统的<span class="text-foreground font-medium">默认且唯一持续状态</span>。
              </p>
            </div>
            <!-- 主动探测 -->
            <div class="rounded-lg border-2 border-orange-500/40 bg-orange-500/5 p-4">
              <div class="flex items-center gap-2 mb-1.5">
                <ScanSearch class="size-4 text-orange-400" />
                <span class="font-semibold text-sm text-orange-400">主动探测（手动触发）</span>
              </div>
              <p class="text-xs text-muted-foreground leading-relaxed">
                主动探测任务需在顶栏切换到<span class="text-foreground font-medium">「主动探测」面板</span>后，
                手动添加扫描任务来触发。不存在系统级"主动模式"开关，避免资源持续消耗。
              </p>
            </div>
          </div>
          <div class="rounded-md bg-muted/30 border border-border px-3 py-2.5 text-xs text-muted-foreground space-y-1">
            <p class="flex items-center gap-1.5">
              <span class="inline-block size-1.5 rounded-full bg-blue-400 shrink-0"></span>
              顶栏「防御坚守 / 主动探测」切换的是<strong class="text-foreground">展示面板</strong>，不影响后端任何运行状态。
            </p>
            <p class="flex items-center gap-1.5">
              <span class="inline-block size-1.5 rounded-full bg-orange-400 shrink-0"></span>
              如需执行主动探测，请切换到主动探测面板 → 扫描管理 → 新建扫描任务。
            </p>
          </div>
        </CardContent>
      </Card>

      <!-- 版本信息 -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base flex items-center gap-2">
            <Info class="size-4 text-muted-foreground" />
            版本信息
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="versionLoading" class="space-y-2">
            <Skeleton v-for="i in 4" :key="i" class="h-6 w-full rounded" />
          </div>
          <div v-else class="grid gap-2 sm:grid-cols-2 text-sm">
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">应用版本</span>
              <code class="font-semibold">{{ version.app_version }}</code>
            </div>
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">Git Commit</span>
              <code class="font-semibold">{{ version.git_commit?.slice(0, 8) }}</code>
            </div>
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">Schema 版本</span>
              <code class="font-semibold">{{ version.schema_version }}</code>
            </div>
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">运行环境</span>
              <Badge variant="outline" class="text-xs h-5">{{ version.env }}</Badge>
            </div>
            <div class="sm:col-span-2 flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">构建时间</span>
              <span>{{ formatTime(version.build_time) }}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- 当前用户信息 -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base flex items-center gap-2">
            <UserCircle class="size-4 text-muted-foreground" />
            当前用户
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div v-if="profileLoading" class="space-y-2">
            <Skeleton v-for="i in 3" :key="i" class="h-6 w-full rounded" />
          </div>
          <div v-else class="space-y-2 text-sm">
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">用户名</span>
              <span class="font-semibold">{{ profile.username }}</span>
            </div>
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">角色</span>
              <Badge variant="outline" class="text-xs capitalize">{{ profile.role }}</Badge>
            </div>
            <div class="flex justify-between rounded-md border border-border px-3 py-2">
              <span class="text-muted-foreground">邮箱</span>
              <span>{{ profile.email || '—' }}</span>
            </div>
            <div class="rounded-md border border-border px-3 py-2">
              <p class="text-muted-foreground mb-1.5">权限点</p>
              <div class="flex flex-wrap gap-1">
                <Badge
                  v-for="perm in profile.permissions"
                  :key="perm"
                  variant="outline"
                  class="text-[10px] h-4 font-mono"
                >{{ perm }}</Badge>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <!-- 快捷导航 -->
      <Card>
        <CardHeader class="pb-3">
          <CardTitle class="text-base flex items-center gap-2">
            <Info class="size-4 text-muted-foreground" />
            更多设置
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div class="grid gap-2 sm:grid-cols-2 text-sm">
            <router-link
              to="/integrations"
              class="flex items-center gap-2 rounded-md border border-border px-3 py-2.5 hover:bg-muted/30 transition-colors"
            >
              <Shield class="size-4 text-cyan-400 shrink-0" />
              <div>
                <p class="font-medium">插件与联动</p>
                <p class="text-xs text-muted-foreground">HFish / Nmap / 推送通道 / 设备凭证管理</p>
              </div>
            </router-link>
            <router-link
              to="/audit"
              class="flex items-center gap-2 rounded-md border border-border px-3 py-2.5 hover:bg-muted/30 transition-colors"
            >
              <Info class="size-4 text-amber-400 shrink-0" />
              <div>
                <p class="font-medium">审计日志</p>
                <p class="text-xs text-muted-foreground">查看系统操作审计记录</p>
              </div>
            </router-link>
          </div>
        </CardContent>
      </Card>

    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { apiClient } from '@/api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import { Info, ScanSearch, Shield, UserCircle } from 'lucide-vue-next'

// ── 版本 ──
const versionLoading = ref(false)
const version = ref({ app_version: '—', git_commit: '—', schema_version: '—', env: '—', build_time: '' })

// ── 用户 ──
const profileLoading = ref(false)
const profile = ref<{ username: string; role: string; email: string | null; permissions: string[] }>({
  username: '—', role: '—', email: null, permissions: [],
})

const loadVersion = async () => {
  versionLoading.value = true
  try {
    const res: any = await apiClient.get('/system/version')
    const data = res?.data ?? res
    version.value = {
      app_version: data?.app_version ?? '—',
      git_commit: data?.git_commit ?? '—',
      schema_version: data?.schema_version ?? '—',
      env: data?.env ?? '—',
      build_time: data?.build_time ?? '',
    }
  } catch {
    // ignore
  } finally {
    versionLoading.value = false
  }
}

const loadProfile = async () => {
  profileLoading.value = true
  try {
    const res: any = await apiClient.get('/system/profile')
    const data = res?.data ?? res
    profile.value = {
      username: data?.username ?? '—',
      role: data?.role ?? '—',
      email: data?.email ?? null,
      permissions: data?.permissions ?? [],
    }
  } catch {
    // ignore
  } finally {
    profileLoading.value = false
  }
}

const formatTime = (t: string) =>
  t ? new Date(t).toLocaleString('zh-CN') : '—'

onMounted(() => {
  loadVersion()
  loadProfile()
})
</script>
