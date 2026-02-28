import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

type ModeKey = 'defense' | 'probe'

const lastActiveMode = ref<ModeKey>('defense')

export function useActiveMode() {
  const route = useRoute()

  // 判断当前路由是否为中性页面
  const isNeutralPage = computed(() => {
    const path = route.path
    return path === '/settings' || 
           path === '/profile' || 
           path === '/integrations' || 
           path === '/audit'
  })

  // 当前激活的模式
  const activeMode = computed<ModeKey>(() => {
    if (route.path.startsWith('/defense')) return 'defense'
    if (route.path.startsWith('/probe')) return 'probe'
    return lastActiveMode.value
  })

  // 监听路由变化，更新 lastActiveMode
  watch(
    () => route.path,
    (newPath) => {
      if (newPath.startsWith('/defense')) {
        lastActiveMode.value = 'defense'
      } else if (newPath.startsWith('/probe')) {
        lastActiveMode.value = 'probe'
      }
    },
    { immediate: true }
  )

  return {
    activeMode,
    lastActiveMode,
    isNeutralPage
  }
}
