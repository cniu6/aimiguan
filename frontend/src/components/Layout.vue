<template>
  <div ref="shellRef" class="flex h-screen flex-col bg-background text-foreground">
    <header class="border-b border-border bg-card/95 backdrop-blur">
      <div class="flex h-16 items-center justify-between px-4 sm:px-6">
        <div class="flex items-center gap-3 sm:gap-6">
          <Sheet>
            <SheetTrigger as-child>
              <Button variant="ghost" size="icon" class="md:hidden">
                <PanelLeft class="size-4" />
              </Button>
            </SheetTrigger>
            <SheetContent side="left" class="border-r border-border p-0">
              <div class="border-b border-border px-4 py-3">
                <p class="text-sm font-medium text-foreground">{{ activeModeLabel }}</p>
              </div>
              <nav class="space-y-1 p-3">
                <router-link
                  v-for="item in currentSidebarItems"
                  :key="`mobile-${item.to}`"
                  :to="item.to"
                  class="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-[transform,opacity] duration-200 hover:translate-x-0.5 hover:bg-sidebar-accent"
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
            <span class="text-base font-semibold tracking-wide">AimiGuard</span>
          </div>
          <Tabs
            :model-value="activeMode"
            class="hidden md:flex"
            @update:model-value="onModeChange"
          >
            <TabsList class="h-9 bg-muted/60">
              <TabsTrigger value="defense" class="px-3 text-xs sm:text-sm">防御坚守</TabsTrigger>
              <TabsTrigger value="probe" class="px-3 text-xs sm:text-sm">主动探测</TabsTrigger>
            </TabsList>
          </Tabs>
        </div>

        <div class="flex items-center gap-2 sm:gap-3">
          <Button
            variant="ghost"
            size="icon"
            class="text-muted-foreground"
            @click="goToSettings"
          >
            <Settings class="size-4" />
          </Button>

          <DropdownMenu>
            <DropdownMenuTrigger as-child>
              <Button variant="ghost" size="icon" class="relative text-muted-foreground">
                <Avatar class="size-8">
                  <AvatarFallback class="bg-primary/15 text-xs text-primary">
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
              <DropdownMenuSeparator />
              <DropdownMenuItem class="cursor-pointer text-destructive focus:text-destructive" @click="handleLogout">
                <LogOut class="mr-2 size-4" />
                退出登录
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div class="border-t border-border/60 px-4 py-2 md:hidden">
        <Tabs :model-value="activeMode" @update:model-value="onModeChange">
          <TabsList class="grid w-full grid-cols-2 bg-muted/60">
            <TabsTrigger value="defense">防御坚守</TabsTrigger>
            <TabsTrigger value="probe">主动探测</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>
    </header>

    <div class="relative flex min-h-0 flex-1 overflow-hidden">
      <div ref="maskWrapRef" class="pointer-events-none absolute inset-0 z-30 hidden overflow-hidden">
        <div ref="impactPulseRef" class="absolute top-1/2 left-1/2 size-56 -translate-x-1/2 -translate-y-1/2 rounded-full border border-primary/50 opacity-0" />
        <div
          v-for="panelIndex in maskPanels"
          :key="`mask-panel-${panelIndex}`"
          :ref="setMaskPanelRef"
          class="absolute top-0 h-full"
          :style="{
            left: `${panelIndex * 12.5}%`,
            width: '12.5%',
            background: panelIndex % 2 === 0
              ? 'linear-gradient(180deg, rgba(3,8,14,0.98) 0%, rgba(8,19,36,0.9) 62%, rgba(20,54,112,0.78) 100%)'
              : 'linear-gradient(180deg, rgba(2,6,12,0.95) 0%, rgba(7,15,28,0.86) 60%, rgba(16,41,95,0.74) 100%)',
          }"
        />
        <div ref="inkTopRef" class="absolute top-[12%] left-0 h-px w-full bg-primary/50 opacity-0" />
        <div ref="inkBottomRef" class="absolute bottom-[12%] left-0 h-px w-full bg-primary/50 opacity-0" />
      </div>

      <aside
        ref="sidebarRef"
        class="hidden w-60 shrink-0 border-r border-border bg-sidebar px-3 py-4 md:block"
      >
        <p class="mb-3 px-2 text-xs font-medium tracking-wide text-muted-foreground">{{ activeModeLabel }}</p>
        <nav class="space-y-1">
          <router-link
            v-for="item in currentSidebarItems"
            :key="item.to"
            :to="item.to"
            data-sidebar-item="true"
            class="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-sidebar-foreground transition-[transform,opacity] duration-200 hover:translate-x-0.5 hover:bg-sidebar-accent"
            active-class="bg-sidebar-accent text-sidebar-accent-foreground"
          >
            <component :is="item.icon" class="size-4" />
            <span>{{ item.label }}</span>
          </router-link>
        </nav>
      </aside>

      <main
        ref="contentRef"
        class="min-w-0 flex-1 overflow-y-auto"
      >
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUpdate, onMounted, onUnmounted, ref } from 'vue'
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
  BrainCircuit,
  LogOut,
  PanelLeft,
  Radar,
  ScanSearch,
  Settings,
  ShieldAlert,
  ShieldCheck,
  UserRound
} from 'lucide-vue-next'

type ModeKey = 'defense' | 'probe'

const router = useRouter()
const route = useRoute()

const username = ref('user')
const role = ref('viewer')
const shellRef = ref<HTMLElement | null>(null)
const sidebarRef = ref<HTMLElement | null>(null)
const contentRef = ref<HTMLElement | null>(null)
const maskWrapRef = ref<HTMLElement | null>(null)
const maskPanelRefs = ref<HTMLElement[]>([])
const impactPulseRef = ref<HTMLElement | null>(null)
const inkTopRef = ref<HTMLElement | null>(null)
const inkBottomRef = ref<HTMLElement | null>(null)
const isModeSwitching = ref(false)
let modeTimeline: gsap.core.Timeline | null = null

const setMaskPanelRef = (el: Element | null) => {
  if (el instanceof HTMLElement) {
    maskPanelRefs.value.push(el)
  }
}

const maskPanels = [0, 1, 2, 3, 4, 5, 6, 7]

onBeforeUpdate(() => {
  maskPanelRefs.value = []
})

const modeTabs: { value: ModeKey; label: string }[] = [
  { value: 'defense', label: '防御坚守' },
  { value: 'probe', label: '主动探测' },
]

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

const getContentBlocks = () => {
  const contentEl = contentRef.value
  if (!contentEl) return [] as HTMLElement[]
  const root = contentEl.firstElementChild
  if (!(root instanceof HTMLElement)) return [] as HTMLElement[]

  const sections = Array.from(root.children).filter((node): node is HTMLElement => node instanceof HTMLElement)
  if (sections.length > 1) return sections
  return [root]
}

const resetAnimatedState = () => {
  if (shellRef.value) gsap.set(shellRef.value, { scale: 1, opacity: 1 })
  if (sidebarRef.value) gsap.set(sidebarRef.value, { x: 0, opacity: 1, clearProps: 'filter' })
  if (contentRef.value) gsap.set(contentRef.value, { x: 0, opacity: 1, scale: 1 })
  if (maskWrapRef.value) gsap.set(maskWrapRef.value, { autoAlpha: 0, display: 'none' })
  if (maskPanelRefs.value.length > 0) gsap.set(maskPanelRefs.value, { xPercent: 0, skewX: 0, yPercent: 0 })
  if (impactPulseRef.value) gsap.set(impactPulseRef.value, { autoAlpha: 0, scale: 0.4 })
  if (inkTopRef.value) gsap.set(inkTopRef.value, { autoAlpha: 0, scaleX: 0 })
  if (inkBottomRef.value) gsap.set(inkBottomRef.value, { autoAlpha: 0, scaleX: 0 })
}

const runModeTransition = (targetMode: ModeKey) => {
  const sidebarEl = sidebarRef.value
  const contentEl = contentRef.value
  const shellEl = shellRef.value
  const maskWrapEl = maskWrapRef.value
  const pulseEl = impactPulseRef.value
  const topLineEl = inkTopRef.value
  const bottomLineEl = inkBottomRef.value
  if (!sidebarEl || !contentEl || !shellEl || !maskWrapEl || !pulseEl || !topLineEl || !bottomLineEl || maskPanelRefs.value.length === 0) {
    router.push(sidebarMap[targetMode][0].to)
    return
  }

  const direction = targetMode === 'probe' ? 1 : -1
  const sidebarItems = sidebarEl.querySelectorAll('[data-sidebar-item]')
  const panels = maskPanelRefs.value

  if (modeTimeline) {
    modeTimeline.kill()
    modeTimeline = null
  }

  isModeSwitching.value = true
  gsap.set(maskWrapEl, { display: 'block', autoAlpha: 1 })
  gsap.set(panels, {
    xPercent: -direction * 145,
    skewX: direction * 10,
    yPercent: (index: number) => (index % 2 === 0 ? -5 : 5),
    transformOrigin: direction === 1 ? 'left center' : 'right center',
  })
  gsap.set(pulseEl, { autoAlpha: 0, scale: 0.4 })
  gsap.set([topLineEl, bottomLineEl], { autoAlpha: 0, scaleX: 0, transformOrigin: direction === 1 ? 'left center' : 'right center' })

  modeTimeline = gsap.timeline({
    defaults: { ease: 'power3.out' },
    onComplete: () => {
      isModeSwitching.value = false
      modeTimeline = null
      resetAnimatedState()
    },
  })

  modeTimeline
    .to([topLineEl, bottomLineEl], { autoAlpha: 1, scaleX: 1, duration: 0.18, ease: 'power2.out' }, 0)
    .to(panels, { xPercent: 0, skewX: 0, yPercent: 0, duration: 0.44, stagger: { each: 0.05, from: 'center' }, ease: 'expo.out' }, 0.01)
    .fromTo(pulseEl, { autoAlpha: 0, scale: 0.4 }, { autoAlpha: 0.28, scale: 1.65, duration: 0.34, ease: 'power2.out' }, 0.05)
    .to(contentEl, { x: direction * 82, opacity: 0.01, scale: 0.962, duration: 0.3, ease: 'power3.in' }, 0.05)
    .to(sidebarEl, { x: -direction * 36, opacity: 0.14, duration: 0.28, ease: 'power3.in' }, 0.05)
    .to(shellEl, { scale: 0.995, duration: 0.32 }, 0.06)
    .add(async () => {
      await router.push(sidebarMap[targetMode][0].to)
      await nextTick()
      const blocks = getContentBlocks()
      if (blocks.length > 0) {
        gsap.fromTo(
          blocks,
          { y: direction * 28, opacity: 0 },
          { y: 0, opacity: 1, duration: 0.48, stagger: 0.075, ease: 'power3.out' },
        )
      }
    }, 0.16)
    .to(pulseEl, { autoAlpha: 0, scale: 2.1, duration: 0.28, ease: 'power1.in' }, 0.24)
    .to(panels, { xPercent: direction * 148, skewX: -direction * 8, yPercent: (index: number) => (index % 2 === 0 ? 4 : -4), duration: 0.5, stagger: { each: 0.046, from: 'edges' }, ease: 'expo.inOut' }, 0.3)
    .to([topLineEl, bottomLineEl], { autoAlpha: 0, scaleX: 0, duration: 0.24, ease: 'power2.in' }, 0.42)
    .fromTo(contentEl, { x: -direction * 52, opacity: 0.04, scale: 0.972 }, { x: 0, opacity: 1, scale: 1, duration: 0.56, ease: 'power4.out' }, 0.4)
    .fromTo(sidebarEl, { x: direction * 26, opacity: 0.28 }, { x: 0, opacity: 1, duration: 0.42, ease: 'power3.out' }, 0.45)
    .fromTo(sidebarItems, { x: direction * 18, opacity: 0 }, { x: 0, opacity: 1, duration: 0.34, stagger: 0.045, ease: 'power2.out' }, 0.52)
    .to(shellEl, { scale: 1, duration: 0.34 }, 0.48)
}

const switchMode = (mode: ModeKey) => {
  if (mode === activeMode.value) return
  if (isModeSwitching.value) return
  runModeTransition(mode)
}

const onModeChange = (nextMode: string) => {
  if (nextMode === 'defense' || nextMode === 'probe') {
    switchMode(nextMode)
  }
}

const goToSettings = () => {
  router.push('/settings')
}

const goToProfile = () => {
  router.push('/profile')
}

onMounted(() => {
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
