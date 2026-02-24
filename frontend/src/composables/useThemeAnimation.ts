import { viewTransition, type TransitionOptions } from './useThemeTransition'

/**
 * 主题动画 - 强制使用原生扩散效果
 */

export async function executeThemeAnimation(options: Omit<TransitionOptions, 'duration'>): Promise<void> {
  await viewTransition({ ...options, duration: 500 })
}

export function getAnimationConfig() {
  return { type: 'view', duration: 500, enabled: true }
}
