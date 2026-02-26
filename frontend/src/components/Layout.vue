<template>
  <Transition name="route-progress">
    <div v-if="isRouteChanging" class="route-progress" :style="{ transform: `scaleX(${routeProgress})` }" />
  </Transition>
  <div ref="shellRef" class="flex h-screen flex-col bg-background/50 text-foreground">
    <header class="border-b border-border bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div class="flex h-14 items-center px-4 sm:px-6">
        <div class="flex items-center gap-3">
          <Sheet>
            <SheetTrigger as-child>
              <Button variant="ghost" size="icon" class="cursor-pointer md:hidden">
                <PanelLeft class="size-4" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" class="w-[18rem] border-r border-border bg-sidebar p-0">
              <div class="border-b border-sidebar-border px-4 py-3">
                <p class="text-sm font-medium text-sidebar-foreground">{{ activeModeLabel }}</p>
              </div>
              <nav class="space-y-1 p-3">
                <router-link
                  v-for="item in currentSidebarItems"
                  :key="item.to"
                  :to="item.to"
                  class="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-colors duration-200 hover:bg-sidebar-accent cursor-pointer"
                  active-class="bg-sidebar-accent text-sidebar-accent-foreground"
                >
                  <component :is="item.icon" class="size-4" />
                  <span>{{ item.label }}</span>
                </router-link>
              </nav>
            </SheetContent>
          </Sheet>

          <div class="flex items-center gap-2">
            <ShieldCheck class="size-5 text-primary" />
            <span class="hidden text-sm font-semibold tracking-tight text-foreground sm:inline">AI 蜜罐</span>
          </div>
        </div>

        <div class="flex flex-1 justify-center">
          <Tabs
            :model-value="activeMode"
            class="hidden md:flex"
            @update:model-value="onModeChange"
          >
            <TabsList class="h-9 w-auto bg-muted/50 p-1 rounded-lg gap-1">
              <TabsTrigger 
                value="defense" 
                class="cursor-pointer px-3 text-xs sm:text-sm rounded-md transition-all duration-500 
                data-[state=active]:!bg-[#3B82F6] data-[state=active]:!text-white data-[state=active]:shadow-sm
                hover:text-[#3B82F6] data-[state=active]:hover:text-white"
              >
                防御坚守
              </TabsTrigger>
              <TabsTrigger 
                value="probe" 
                class="cursor-pointer px-3 text-xs sm:text-sm rounded-md transition-all duration-500 
                data-[state=active]:!bg-[#F97316] data-[state=active]:!text-white data-[state=active]:shadow-sm
                hover:text-[#F97316] data-[state=active]:hover:text-white"
              >
                主动探测
              </TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div class="flex items-center gap-2">
          <Sheet>
            <SheetTrigger as-child>
              <Button
                variant="ghost"
                size="icon"
                class="relative cursor-pointer text-muted-foreground"
              >
                <Bell class="size-4" />
                <span
                  v-if="unreadNotifications > 0"
                  class="absolute -top-0.5 -right-0.5 inline-flex h-2 w-2 rounded-full bg-red-500"
                />
              </Button>
            </SheetTrigger>
            <SheetContent side="right" class="w-[22rem] border-l border-border p-0">
              <div class="border-b border-border px-4 py-3">
                <div class="flex items-center justify-between">
                  <h3 class="text-sm font-semibold">通知中心</h3>
                  <Button
                    variant="ghost"
                    size="sm"
                    class="h-7 cursor-pointer text-xs"
                    @click="markAllNotificationsRead"
                  >
                    全部已读
                  </Button>
                </div>
              </div>
              <div class="max-h-[calc(100vh-4rem)] space-y-2 overflow-y-auto px-4 py-3">
                <div
                  v-for="item in notifications"
                  :key="item.id"
                  class="rounded-md border border-border bg-card px-3 py-2"
                >
                  <div class="flex items-center justify-between gap-2">
                    <p class="text-sm font-medium">{{ item.title }}</p>
                    <span
                      v-if="!item.read"
                      class="inline-flex h-1.5 w-1.5 rounded-full bg-blue-500"
                    />
                  </div>
                  <p class="mt-1 text-xs text-muted-foreground">{{ item.content }}</p>
                  <p class="mt-2 text-[11px] text-muted-foreground/80">{{ item.time }}</p>
                </div>
              </div>
            </SheetContent>
          </Sheet>

          <Button
            variant="ghost"
            size="icon"
            class="cursor-pointer text-muted-foreground"
            @click="goToSettings"
          >
            <Settings class="size-4" />
          </Button>

          <Button
            variant="ghost"
            size="icon"
            class="cursor-pointer text-muted-foreground"
            @click="toggleTheme"
          >
            <Moon v-if="isDarkMode" class="size-4" />
            <Sun v-else class="size-4" />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="icon" class="relative cursor-pointer text-muted-foreground">
                <Avatar class="size-8">
                  <AvatarFallback class="bg-primary/10 text-xs text-primary">
                    {{ username.charAt(0).toUpperCase() }}
                  </AvatarFallback>
                </Avatar>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" class="w-56">
              <DropdownMenuLabel>
                <div class="flex items-center justify-between">
                  <span class="text-sm text-foreground">{{ username }}</span>
                  <Badge :variant="roleBadgeVariant">{{ roleText }}</Badge>
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="cursor-pointer" @click="goToProfile">
                <UserRound class="mr-2 size-4" />
                用户中心
              </DropdownMenuItem>
              <DropdownMenuItem class="cursor-pointer" @click="goToSettings">
                <Settings class="mr-2 size-4" />
                系统设置
              </DropdownMenuItem>
              <DropdownMenuItem class="cursor-pointer" @click="goToSecuritySettings">
                <ShieldAlert class="mr-2 size-4" />
                安全设置
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem class="cursor-pointer text-destructive focus:text-destructive" @click="handleLogout">
                <LogOut class="mr-2 size-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div class="border-t border-border px-4 py-2 md:hidden">
        <Tabs :model-value="activeMode" @update:model-value="onModeChange">
          <TabsList class="grid w-full grid-cols-2 bg-muted/50 p-1 rounded-lg gap-1">
            <TabsTrigger 
              value="defense" 
              class="cursor-pointer rounded-md transition-all duration-500 
              data-[state=active]:!bg-[#3B82F6] data-[state=active]:!text-white data-[state=active]:shadow-sm
              hover:text-[#3B82F6] data-[state=active]:hover:text-white"
            >
              防御坚守
            </TabsTrigger>
            <TabsTrigger 
              value="probe" 
              class="cursor-pointer rounded-md transition-all duration-500 
              data-[state=active]:!bg-[#F97316] data-[state=active]:!text-white data-[state=active]:shadow-sm
              hover:text-[#F97316] data-[state=active]:hover:text-white"
            >
              主动探测
            </TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
    </header>

    <div class="relative flex min-h-0 flex-1 overflow-hidden">
      <div ref="maskWrapRef" class="pointer-events-none fixed inset-0 z-[100] hidden flex w-full h-full">
        <div ref="impactPulseRef" class="absolute top-1/2 left-1/2 size-20 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-primary opacity-0" />
        <div
          v-for="panelIndex in maskPanels"
          :key="`mask-panel-${panelIndex}`"
          :ref="setMaskPanelRef"
          class="h-full flex-1 bg-background/50 border-r border-border/50 last:border-r-0 origin-top"
        />
        <div ref="inkTopRef" class="absolute top-[30%] left-0 h-0.5 w-full bg-primary shadow-[0_0_15px_var(--primary)] opacity-0" />
        <div ref="inkBottomRef" class="absolute bottom-[30%] left-0 h-0.5 w-full bg-primary shadow-[0_0_15px_var(--primary)] opacity-0" />
        <div 
          ref="transitionTitleRef" 
          class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 text-6xl md:text-8xl font-black tracking-[0.5em] text-transparent bg-clip-text bg-gradient-to-b from-white via-white to-white/10 opacity-0 whitespace-nowrap z-50 select-none pointer-events-none"
          style="text-shadow: 0 0 40px var(--primary);"
        >
          {{ transitionTitleText }}
        </div>
      </div>

      <aside
        ref="sidebarRef"
        class="relative hidden shrink-0 border-r border-sidebar-border bg-sidebar transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] md:flex md:flex-col"
        :class="sidebarCollapsed ? 'px-2 py-3' : 'p-3'"
        :style="{ width: `${sidebarCurrentWidth}px` }"
      >
        <div
          class="mb-3 min-h-8 rounded-md border transition-all duration-500 ease-[cubic-bezier(0.4,0,0.2,1)] backdrop-blur-sm bg-background/60 flex items-center justify-center overflow-hidden"
          :class="[
            sidebarCollapsed ? 'px-2 py-2 text-center' : 'px-3 py-2',
            activeMode === 'defense' 
              ? 'border-blue-500 text-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.1)]' 
              : 'border-orange-500 text-orange-500 shadow-[0_0_15px_rgba(249,115,22,0.1)]'
          ]"
        >
          <p class="font-medium tracking-wide leading-none flex items-center justify-center" :class="sidebarCollapsed ? 'text-[11px]' : 'text-xs'">
            <span
              class="sidebar-mode-label"
              :class="sidebarCollapsed ? 'sidebar-mode-label-collapsed' : 'sidebar-mode-label-expanded'"
            >
              {{ sidebarCollapsed ? (activeMode === 'defense' ? '防御' : '探测') : activeModeLabel }}
            </span>
          </p>
        </div>

        <nav class="flex-1 space-y-1 overflow-hidden">
          <router-link
            v-for="item in currentSidebarItems"
            :key="item.to"
            :to="item.to"
            data-sidebar-item="true"
            :title="sidebarCollapsed ? item.label : undefined"
            class="flex items-center rounded-md py-2 text-sm text-sidebar-foreground transition-colors duration-200 hover:bg-sidebar-accent cursor-pointer"
            :class="sidebarCollapsed ? 'justify-center px-2' : 'gap-2 px-3'"
            active-class="bg-sidebar-accent text-sidebar-accent-foreground"
          >
            <component :is="item.icon" class="size-4" />
            <span
              class="sidebar-item-label"
              :class="sidebarCollapsed ? 'sidebar-item-label-collapsed' : 'sidebar-item-label-expanded'"
            >
              {{ item.label }}
            </span>
          </router-link>
        </nav>

        <div class="mt-2 border-t border-sidebar-border/70 pt-2">
          <button
            type="button"
            class="flex h-11 w-full items-center rounded-md text-sidebar-foreground transition-colors duration-200 hover:bg-sidebar-accent focus:outline-none focus:ring-2 focus:ring-ring cursor-pointer"
            :class="sidebarCollapsed ? 'justify-center px-2' : 'gap-2 px-3'"
            :title="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
            :aria-label="sidebarCollapsed ? '展开侧边栏' : '收起侧边栏'"
            @click="toggleSidebarCollapsed"
          >
            <ChevronRight
              class="size-4 transition-transform duration-300 ease-out"
              :class="sidebarCollapsed ? 'rotate-0' : 'rotate-180'"
            />
            <span
              class="sidebar-item-label text-sm"
              :class="sidebarCollapsed ? 'sidebar-item-label-collapsed' : 'sidebar-item-label-expanded'"
            >
              收起侧边栏
            </span>
          </button>
        </div>

        <div
          class="absolute top-0 -right-1 z-20 h-full w-2 cursor-col-resize"
          role="separator"
          aria-orientation="vertical"
          @mousedown="startSidebarResize"
        >
          <div
            class="mx-auto h-full w-px bg-transparent transition-colors duration-200 hover:bg-border"
            :class="isSidebarResizing ? 'bg-primary/60' : ''"
          />
        </div>
      </aside>

      <main
        ref="contentRef"
        class="min-w-0 flex-1 overflow-y-auto bg-background/50"
      >
        <div
          class="relative h-full transition-[opacity,transform,filter] duration-300 ease-out"
          :class="isRouteChanging ? 'content-loading' : 'content-ready'"
        >
          <div
            v-if="isRouteChanging"
            class="pointer-events-none absolute inset-0 z-20 route-content-overlay"
            :style="{ opacity: String(Math.min(0.16, Math.max(0.06, 1 - routeProgress))) }"
          />
          <router-view v-slot="{ Component, route: childRoute }">
            <Transition name="fade-slide" mode="out-in" appear>
              <div :key="childRoute.fullPath" class="route-page h-full">
                <component :is="Component" />
              </div>
            </Transition>
          </router-view>
        </div>
      </main>
    </div>

  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUpdate, onMounted, onUnmounted, ref, watch } from 'vue'
import type { ComponentPublicInstance } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '../api/auth'
import { Button } from '@/components/ui/button'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Sheet, SheetContent, SheetTrigger } from '@/components/ui/sheet'
import gsap from 'gsap'
import {
  Activity,
  Bell,
  BrainCircuit,
  ChevronRight,
  LogOut,
  Moon,
  PanelLeft,
  Radar,
  ScanSearch,
  Settings,
  ShieldAlert,
  ShieldCheck,
  Sun,
  UserRound,
} from 'lucide-vue-next'

type ModeKey = 'defense' | 'probe'

const router = useRouter()
const route = useRoute()

const username = ref('user')
const role = ref('viewer')
const notifications = ref([
  { id: 'n-1', title: '工作台状态', content: '页面切换不会影响后端任务运行。', time: '刚刚', read: false },
  { id: 'n-2', title: '审计任务完成', content: '最近一次导出任务已完成。', time: '5 分钟前', read: false },
  { id: 'n-3', title: '扫描任务提示', content: '存在待确认扫描结果。', time: '15 分钟前', read: true },
])
const shellRef = ref<HTMLElement | null>(null)
const sidebarRef = ref<HTMLElement | null>(null)

// 路由进度条状态
const isRouteChanging = ref(false)
const routeProgress = ref(0)
const isDarkMode = ref(false)
const THEME_KEY = 'theme'
const SIDEBAR_COLLAPSED_KEY = 'layout_sidebar_collapsed'
const SIDEBAR_WIDTH_STEP_KEY = 'layout_sidebar_width_step'
const sidebarWidthPresets = [160, 180, 200] as const
const minSidebarWidthStep = 0
const defaultSidebarWidthStep = 1
const maxSidebarWidthStep = sidebarWidthPresets.length - 1

const sidebarCollapsed = ref(false)
const sidebarWidthStep = ref(defaultSidebarWidthStep)
const isSidebarResizing = ref(false)
let sidebarResizeMoveHandler: ((event: MouseEvent) => void) | null = null
let sidebarResizeUpHandler: (() => void) | null = null

const normalizeSidebarWidthStep = (value: number) => {
  return Math.min(maxSidebarWidthStep, Math.max(minSidebarWidthStep, value))
}

const widthToStep = (width: number) => {
  let nearestStep = defaultSidebarWidthStep
  let nearestDiff = Number.POSITIVE_INFINITY

  sidebarWidthPresets.forEach((presetWidth, step) => {
    const diff = Math.abs(presetWidth - width)
    if (diff < nearestDiff) {
      nearestDiff = diff
      nearestStep = step
    }
  })

  return nearestStep
}

const getSidebarTargetWidth = () => {
  if (sidebarCollapsed.value) return 72
  return sidebarWidthPresets[sidebarWidthStep.value]
}

const sidebarAnimatedWidth = ref(getSidebarTargetWidth())
let sidebarWidthAnimationFrame: number | null = null

const stopSidebarWidthAnimation = () => {
  if (sidebarWidthAnimationFrame !== null) {
    cancelAnimationFrame(sidebarWidthAnimationFrame)
    sidebarWidthAnimationFrame = null
  }
}

const runSidebarWidthAnimation = () => {
  stopSidebarWidthAnimation()

  const animate = () => {
    const target = getSidebarTargetWidth()
    const current = sidebarAnimatedWidth.value
    const diff = target - current

    if (Math.abs(diff) < 0.5) {
      sidebarAnimatedWidth.value = target
      sidebarWidthAnimationFrame = null
      return
    }

    sidebarAnimatedWidth.value = current + diff * 0.18
    sidebarWidthAnimationFrame = requestAnimationFrame(animate)
  }

  sidebarWidthAnimationFrame = requestAnimationFrame(animate)
}

const sidebarCurrentWidth = computed(() => Math.round(sidebarAnimatedWidth.value))

const toggleSidebarCollapsed = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

const loadSidebarPreference = () => {
  const savedCollapsed = localStorage.getItem(SIDEBAR_COLLAPSED_KEY)
  if (savedCollapsed !== null) {
    sidebarCollapsed.value = savedCollapsed === '1' || savedCollapsed === 'true'
  }

  const savedStep = localStorage.getItem(SIDEBAR_WIDTH_STEP_KEY)
  if (savedStep !== null) {
    const parsedStep = Number.parseInt(savedStep, 10)
    if (!Number.isNaN(parsedStep)) {
      sidebarWidthStep.value = normalizeSidebarWidthStep(parsedStep)
    }
  }
}

const updateSidebarWidthByClientX = (clientX: number) => {
  const shellEl = shellRef.value
  if (!shellEl) return

  const shellLeft = shellEl.getBoundingClientRect().left
  const nextWidth = clientX - shellLeft
  const clampedWidth = Math.min(sidebarWidthPresets[maxSidebarWidthStep], Math.max(sidebarWidthPresets[minSidebarWidthStep], nextWidth))
  stopSidebarWidthAnimation()
  sidebarAnimatedWidth.value = clampedWidth
  sidebarWidthStep.value = widthToStep(clampedWidth)
}

const stopSidebarResize = () => {
  isSidebarResizing.value = false

  if (sidebarResizeMoveHandler) {
    window.removeEventListener('mousemove', sidebarResizeMoveHandler)
    sidebarResizeMoveHandler = null
  }

  if (sidebarResizeUpHandler) {
    window.removeEventListener('mouseup', sidebarResizeUpHandler)
    sidebarResizeUpHandler = null
  }

  if (!sidebarCollapsed.value) {
    runSidebarWidthAnimation()
  }
}

const startSidebarResize = (event: MouseEvent) => {
  if (sidebarCollapsed.value || event.button !== 0) return

  event.preventDefault()
  isSidebarResizing.value = true

  sidebarResizeMoveHandler = (moveEvent: MouseEvent) => {
    updateSidebarWidthByClientX(moveEvent.clientX)
  }

  sidebarResizeUpHandler = () => {
    stopSidebarResize()
  }

  window.addEventListener('mousemove', sidebarResizeMoveHandler)
  window.addEventListener('mouseup', sidebarResizeUpHandler)
}

watch(sidebarCollapsed, (collapsed) => {
  localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? '1' : '0')
})

watch([sidebarCollapsed, sidebarWidthStep], () => {
  if (isSidebarResizing.value) return
  runSidebarWidthAnimation()
})

watch(sidebarWidthStep, (step) => {
  localStorage.setItem(SIDEBAR_WIDTH_STEP_KEY, String(normalizeSidebarWidthStep(step)))
})

const applyTheme = (mode: 'light' | 'dark') => {
  const root = document.documentElement
  root.classList.toggle('dark', mode === 'dark')
  isDarkMode.value = mode === 'dark'
  localStorage.setItem(THEME_KEY, mode)
}

const initTheme = () => {
  const savedTheme = localStorage.getItem(THEME_KEY)
  if (savedTheme === 'light' || savedTheme === 'dark') {
    applyTheme(savedTheme)
    return
  }

  const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
  applyTheme(prefersDark ? 'dark' : 'light')
}

const toggleTheme = async (event?: MouseEvent) => {
  const newMode = isDarkMode.value ? 'light' : 'dark'
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

  if (reducedMotion) {
    applyTheme(newMode)
    return
  }

  const triggerElement = event?.currentTarget
  if (!(triggerElement instanceof HTMLElement)) {
    applyTheme(newMode)
    return
  }

  const rect = triggerElement.getBoundingClientRect()
  const x = rect.left + rect.width / 2
  const y = rect.top + rect.height / 2

  // 使用动画配置系统
  const { executeThemeAnimation, getAnimationConfig } = await import('@/composables/useThemeAnimation')
  const config = getAnimationConfig()
  
  // View Transitions API 会在内部切换主题，其他动画需要手动切换
  if (config.type === 'view') {
    const root = document.documentElement
    root.classList.add('view-transitioning')
    isDarkMode.value = newMode === 'dark'
    localStorage.setItem(THEME_KEY, newMode)
    try {
      await executeThemeAnimation({ x, y, reducedMotion })
    } finally {
      root.classList.remove('view-transitioning')
    }
  } else {
    // 其他动画：在动画中间切换主题
    const animationPromise = executeThemeAnimation({ x, y, reducedMotion })
    setTimeout(() => {
      applyTheme(newMode)
    }, config.duration / 2)
    await animationPromise
  }
}

const contentRef = ref<HTMLElement | null>(null)
const maskWrapRef = ref<HTMLElement | null>(null)
const maskPanelRefs = ref<HTMLElement[]>([])
const impactPulseRef = ref<HTMLElement | null>(null)
const inkTopRef = ref<HTMLElement | null>(null)
const inkBottomRef = ref<HTMLElement | null>(null)
const transitionTitleRef = ref<HTMLElement | null>(null)
const transitionTitleText = ref('')
const isModeSwitching = ref(false)
let modeTimeline: gsap.core.Timeline | null = null

const setMaskPanelRef = (el: Element | ComponentPublicInstance | null) => {
  const maybeElement = el instanceof HTMLElement
    ? el
    : (el && '$el' in el && el.$el instanceof HTMLElement ? el.$el : null)

  if (maybeElement) {
    maskPanelRefs.value.push(maybeElement)
  }
}

const maskPanels = Array.from({ length: 12 }, (_, i) => i)

onBeforeUpdate(() => {
  maskPanelRefs.value = []
})


const sidebarMap: Record<ModeKey, { to: string; label: string; icon: unknown }[]> = {
  defense: [
    { to: '/defense/realtime', label: '实时检测', icon: Activity },
    { to: '/defense/events', label: '威胁处置', icon: ShieldAlert },
    { to: '/defense/ai', label: 'AI 研判', icon: BrainCircuit },
  ],
  probe: [
    { to: '/probe/realtime', label: '实时检测', icon: Radar },
    { to: '/probe/scan', label: '扫描管理', icon: ScanSearch },
    { to: '/probe/ai', label: 'AI 分析', icon: BrainCircuit },
  ],
}

const activeMode = computed<ModeKey>(() => {
  if (route.path.startsWith('/probe')) return 'probe'
  return 'defense'
})

const activeModeLabel = computed(() => {
  return activeMode.value === 'defense' ? '防御坚守模式' : '主动探测模式'
})

const currentSidebarItems = computed(() => sidebarMap[activeMode.value])

const roleText = computed(() => {
  const map: Record<string, string> = { admin: '管理员', operator: '操作员', viewer: '查看者' }
  return map[role.value] || role.value
})

const roleBadgeVariant = computed(() => {
  return role.value === 'admin' ? ('default' as const) : ('secondary' as const)
})

const unreadNotifications = computed(() => notifications.value.filter((item) => !item.read).length)

// function removed

const resetAnimatedState = () => {
  if (shellRef.value) gsap.set(shellRef.value, { clearProps: 'all' })
  if (sidebarRef.value) gsap.set(sidebarRef.value, { clearProps: 'transform,opacity,filter' })
  if (contentRef.value) gsap.set(contentRef.value, { clearProps: 'all' })
  if (maskWrapRef.value) gsap.set(maskWrapRef.value, { autoAlpha: 0, display: 'none' })
  if (maskPanelRefs.value.length > 0) gsap.set(maskPanelRefs.value, { clearProps: 'all' })
  if (impactPulseRef.value) gsap.set(impactPulseRef.value, { autoAlpha: 0, scale: 0.4, clearProps: 'all' })
  if (inkTopRef.value) gsap.set(inkTopRef.value, { autoAlpha: 0, scaleX: 0, clearProps: 'all' })
  if (inkBottomRef.value) gsap.set(inkBottomRef.value, { autoAlpha: 0, scaleX: 0, clearProps: 'all' })
  if (transitionTitleRef.value) gsap.set(transitionTitleRef.value, { autoAlpha: 0, scale: 1, letterSpacing: '0.5em', clearProps: 'all' })
}

const runModeTransition = (targetMode: ModeKey) => {
  const sidebarEl = sidebarRef.value
  const contentEl = contentRef.value
  const shellEl = shellRef.value
  const maskWrapEl = maskWrapRef.value
  const pulseEl = impactPulseRef.value
  const topLineEl = inkTopRef.value
  const bottomLineEl = inkBottomRef.value
  const panels = maskPanelRefs.value
  const titleEl = transitionTitleRef.value

  const isProbe = targetMode === 'probe'
  const accentColor = isProbe ? '#f97316' : '#3b82f6' // Orange for Probe, Blue for Defense
  transitionTitleText.value = isProbe ? '主动探测' : '防御坚守'

  if (modeTimeline) {
    modeTimeline.kill()
    modeTimeline = null
  }

  isModeSwitching.value = true

  // Fallback
  if (!contentEl || !shellEl || !maskWrapEl) {
    void router.push(sidebarMap[targetMode][0].to).then(() => {
      isModeSwitching.value = false
    })
    return
  }

  // Initial States
  gsap.set(maskWrapEl, { display: 'flex', autoAlpha: 1 })
  gsap.set(panels, { 
    scaleY: 0, 
    transformOrigin: 'top', 
    backgroundColor: isProbe ? '#0c0a09' : '#0f172a', 
    borderColor: isProbe ? 'rgba(249, 115, 22, 0.2)' : 'rgba(59, 130, 246, 0.2)'
  })
  
  if (pulseEl) {
    gsap.set(pulseEl, { 
      autoAlpha: 0, 
      scale: 0,
      borderColor: accentColor,
      boxShadow: `0 0 30px ${accentColor}`
    })
  }

  if (topLineEl && bottomLineEl) {
    gsap.set([topLineEl, bottomLineEl], { 
      scaleX: 0, 
      autoAlpha: 0,
      backgroundColor: accentColor,
      boxShadow: `0 0 20px ${accentColor}`
    })
  }

  if (titleEl) {
    gsap.set(titleEl, {
      autoAlpha: 0,
      scale: 0.8,
      letterSpacing: '1em',
      textShadow: `0 0 0px ${accentColor}`
    })
  }

  modeTimeline = gsap.timeline({
    onComplete: () => {
      isModeSwitching.value = false
      modeTimeline = null
      resetAnimatedState()
    }
  })

  // --- Animation Sequence (Slower & Cinematic) ---
  
  // 1. Initiate: Content scales down
  modeTimeline
    .to(contentEl, {
      filter: 'blur(4px) grayscale(80%)',
      opacity: 0.6,
      duration: 0.6,
      ease: 'power2.inOut'
    }, 0)
    .to(shellEl, {
      backgroundColor: '#000',
      duration: 0.6
    }, 0)

  if (sidebarEl) {
    modeTimeline.to(sidebarEl, {
      scaleX: 1,
      filter: 'blur(4px) grayscale(80%)',
      opacity: 0.6,
      transformOrigin: 'center center',
      duration: 0.6,
      ease: 'power2.inOut'
    }, 0)
  }

  // 2. Tech Wipe: Panels slam down (Full Cover)
  modeTimeline.to(panels, {
    scaleY: 1,
    duration: 0.7,
    stagger: {
      amount: 0.3,
      from: isProbe ? 'start' : 'end',
      grid: [1, 12]
    },
    ease: 'expo.inOut'
  }, 0.2)

  // 3. Scan Lines: Zip across during close
  if (topLineEl && bottomLineEl) {
    modeTimeline.to([topLineEl, bottomLineEl], {
      autoAlpha: 1,
      scaleX: 1,
      duration: 0.5,
      ease: 'power2.inOut'
    }, 0.3)
  }

  // 4. TITLE REVEAL (The "Middle" Moment)
  // Starts when panels are mostly down (around 0.8s)
  if (titleEl) {
    modeTimeline
      .to(titleEl, {
        autoAlpha: 1,
        scale: 1,
        letterSpacing: '0.2em', // Compress tracking
        textShadow: `0 0 30px ${accentColor}`,
        duration: 0.8,
        ease: 'power4.out'
      }, 0.7) // Start appearing as panels finish closing
      
      // Glitch shake effect
      .to(titleEl, {
        x: 2,
        y: -2,
        duration: 0.05,
        repeat: 5,
        yoyo: true,
        ease: 'steps(1)'
      }, 0.8)
      
      // Hold for a moment (0.5s pause implicit in duration)
      .to(titleEl, {
        autoAlpha: 0,
        scale: 1.5,
        filter: 'blur(10px)',
        letterSpacing: '0.5em',
        duration: 0.4,
        ease: 'power2.in'
      }, 1.6) // Fade out after hold
  }

  // 5. Switch Router (Hidden behind panels)
  modeTimeline.add(() => {
    void router.push(sidebarMap[targetMode][0].to).then(() => {
      gsap.set(contentEl, {
        filter: 'blur(10px) brightness(1.5)',
        opacity: 0
      })

      if (sidebarEl) {
        gsap.set(sidebarEl, {
          filter: 'blur(10px) brightness(1.5)',
          scaleX: 1,
          opacity: 0,
          transformOrigin: 'center center'
        })
      }
    })
  }, 1.2) // Switch happens while text is visible

  // 6. Reveal: Panels retract (Starts after title fades out)
  const revealStart = 1.8 // Delayed start
  
  modeTimeline.to(panels, {
    scaleY: 0,
    transformOrigin: 'bottom',
    duration: 0.7,
    stagger: {
      amount: 0.2,
      from: isProbe ? 'end' : 'start'
    },
    ease: 'expo.inOut'
  }, revealStart)

  // 7. Lines fade out
  if (topLineEl && bottomLineEl) {
    modeTimeline.to([topLineEl, bottomLineEl], {
      scaleX: 0,
      autoAlpha: 0,
      transformOrigin: isProbe ? 'right' : 'left',
      duration: 0.4
    }, revealStart + 0.1)
  }

  // 8. Energy Burst (Sync with reveal)
  if (pulseEl) {
    modeTimeline
      .set(pulseEl, { autoAlpha: 1, scale: 0.1 }, revealStart)
      .to(pulseEl, {
        scale: 4,
        autoAlpha: 0,
        duration: 0.6,
        ease: 'power2.out'
      }, revealStart)
  }

  // 9. Content Returns
  modeTimeline.to(contentEl, {
    filter: 'blur(0px) brightness(1)',
    opacity: 1,
    duration: 0.8,
    ease: 'power3.out'
  }, revealStart + 0.2)

  if (sidebarEl) {
    modeTimeline.to(sidebarEl, {
      scaleX: 1,
      scaleY: 1,
      filter: 'blur(0px) brightness(1)',
      opacity: 1,
      duration: 0.8,
      ease: 'power3.out'
    }, revealStart + 0.2)
  }
  
  // 10. Restore Shell
  modeTimeline.to(shellEl, {
    backgroundColor: '',
    clearProps: 'backgroundColor',
    duration: 0.5
  }, revealStart + 0.3)
}

const switchMode = (mode: ModeKey) => {
  if (mode === activeMode.value) return
  if (isModeSwitching.value) return
  runModeTransition(mode)
}

const onModeChange = (nextMode: string | number) => {
  if (nextMode === 'defense' || nextMode === 'probe') {
    switchMode(nextMode)
  }
}

const goToSettings = () => {
  router.push('/settings')
}

const goToSecuritySettings = () => {
  router.push('/settings?tab=security')
}

const markAllNotificationsRead = () => {
  notifications.value = notifications.value.map((item) => ({ ...item, read: true }))
}

const goToProfile = () => {
  router.push('/profile')
}

// 路由进度条逻辑
let progressTimer: ReturnType<typeof setTimeout> | null = null

watch(() => route.fullPath, () => {
  isRouteChanging.value = true
  routeProgress.value = 0.25
  
  if (progressTimer) clearTimeout(progressTimer)
  
  progressTimer = setTimeout(() => {
    routeProgress.value = 0.68
  }, 180)
  
  nextTick(() => {
    setTimeout(() => {
      routeProgress.value = 1
      setTimeout(() => {
        isRouteChanging.value = false
        routeProgress.value = 0
      }, 220)
    }, 120)
  })
})

onMounted(() => {
  initTheme()
  loadSidebarPreference()
  sidebarAnimatedWidth.value = getSidebarTargetWidth()

  const userInfo = localStorage.getItem('user_info')
  if (userInfo) {
    const user = JSON.parse(userInfo)
    username.value = user.username || 'user'
    role.value = user.role || 'viewer'
  }

  resetAnimatedState()
})

onUnmounted(() => {
  if (modeTimeline) {
    modeTimeline.kill()
    modeTimeline = null
  }
  if (progressTimer) {
    clearTimeout(progressTimer)
    progressTimer = null
  }
  stopSidebarResize()
  stopSidebarWidthAnimation()
})

const handleLogout = async () => {
  try {
    await authApi.logout()
  } catch (err) {
    console.error('Logout failed:', err)
  } finally {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user_info')
    router.push('/login')
  }
}
</script>

<style scoped>
.sidebar-item-label {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  transform-origin: left center;
  transition: max-width 280ms ease, opacity 220ms ease, transform 280ms ease;
}

.sidebar-item-label-expanded {
  max-width: 9rem;
  opacity: 1;
  transform: translateX(0);
}

.sidebar-item-label-collapsed {
  max-width: 0;
  opacity: 0;
  transform: translateX(-6px);
}

.sidebar-mode-label {
  display: inline-block;
  overflow: hidden;
  white-space: nowrap;
  transition: max-width 280ms ease, opacity 220ms ease;
}

.sidebar-mode-label-expanded {
  max-width: 10rem;
  opacity: 1;
}

.sidebar-mode-label-collapsed {
  max-width: 2.5rem;
  opacity: 0.95;
}

@media (prefers-reduced-motion: reduce) {
  .sidebar-item-label,
  .sidebar-mode-label {
    transition: none;
  }
}
</style>
