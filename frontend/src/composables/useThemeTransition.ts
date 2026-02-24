import { gsap } from 'gsap'

/**
 * 主题切换动画系统
 * 使用 GSAP 实现视觉震撼的过渡效果
 */

export interface TransitionOptions {
  x: number
  y: number
  duration?: number
  reducedMotion?: boolean
}

/**
 * 创建涟漪扩散效果的遮罩元素
 */
function createRippleMask(x: number, y: number): HTMLDivElement {
  const mask = document.createElement('div')
  mask.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 9999;
    background: radial-gradient(circle at ${x}px ${y}px, transparent 0%, var(--background) 100%);
  `
  document.body.appendChild(mask)
  return mask
}

/**
 * 创建粒子效果容器
 */
function createParticles(x: number, y: number, isDark: boolean): HTMLDivElement[] {
  const particles: HTMLDivElement[] = []
  const particleCount = 12
  const colors = isDark 
    ? ['#3B82F6', '#6366F1', '#8B5CF6', '#EC4899']
    : ['#F59E0B', '#F97316', '#EF4444', '#EC4899']

  for (let i = 0; i < particleCount; i++) {
    const particle = document.createElement('div')
    const size = Math.random() * 6 + 4
    particle.style.cssText = `
      position: fixed;
      left: ${x}px;
      top: ${y}px;
      width: ${size}px;
      height: ${size}px;
      border-radius: 50%;
      background: ${colors[Math.floor(Math.random() * colors.length)]};
      pointer-events: none;
      z-index: 9998;
      opacity: 0.8;
    `
    document.body.appendChild(particle)
    particles.push(particle)
  }

  return particles
}

/**
 * 主题切换动画 - 涟漪扩散 + 分层动画 + 粒子效果
 */
export async function rippleTransition(options: TransitionOptions): Promise<void> {
  const { x, y, duration = 600, reducedMotion = false } = options

  if (reducedMotion) return

  const root = document.documentElement
  const isDark = root.classList.contains('dark')

  // 创建遮罩和粒子
  const mask = createRippleMask(x, y)
  const particles = createParticles(x, y, !isDark)

  // 计算最大半径
  const maxRadius = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y)
  )

  // 创建 GSAP 时间线
  const tl = gsap.timeline({
    onComplete: () => {
      mask.remove()
      particles.forEach(p => p.remove())
    }
  })

  // 1. 粒子爆发动画
  particles.forEach((particle, i) => {
    const angle = (i / particles.length) * Math.PI * 2
    const distance = 80 + Math.random() * 40
    const tx = Math.cos(angle) * distance
    const ty = Math.sin(angle) * distance

    tl.to(particle, {
      x: tx,
      y: ty,
      opacity: 0,
      scale: 0,
      duration: duration / 1000 * 0.6,
      ease: 'power2.out'
    }, 0)
  })

  // 2. 涟漪扩散动画
  tl.fromTo(mask,
    {
      background: `radial-gradient(circle at ${x}px ${y}px, transparent 0%, var(--background) 0%)`
    },
    {
      background: `radial-gradient(circle at ${x}px ${y}px, transparent ${maxRadius}px, var(--background) ${maxRadius}px)`,
      duration: duration / 1000,
      ease: 'power2.inOut'
    },
    0
  )

  // 3. 页面元素分层动画
  const elements = document.querySelectorAll('header, main, aside, footer, [class*="card"], [class*="sidebar"]')
  elements.forEach((el, i) => {
    tl.fromTo(el as HTMLElement,
      { opacity: 1, y: 0 },
      {
        opacity: 0.3,
        y: -5,
        duration: duration / 1000 * 0.3,
        ease: 'power1.inOut',
        yoyo: true,
        repeat: 1
      },
      i * 0.02
    )
  })

  await tl.play()
}

/**
 * 主题切换动画 - 3D 翻转效果
 */
export async function flipTransition(options: TransitionOptions): Promise<void> {
  const { duration = 500, reducedMotion = false } = options

  if (reducedMotion) return

  const body = document.body

  const tl = gsap.timeline()

  // 3D 翻转动画
  tl.to(body, {
    rotateY: 90,
    duration: duration / 2000,
    ease: 'power2.in',
    transformPerspective: 1000,
    transformOrigin: 'center center'
  })
  .to(body, {
    rotateY: 0,
    duration: duration / 2000,
    ease: 'power2.out'
  })

  await tl.play()
}

/**
 * 主题切换动画 - 滑动遮罩效果
 */
export async function slideTransition(options: TransitionOptions): Promise<void> {
  const { x, duration = 600, reducedMotion = false } = options

  if (reducedMotion) return

  const mask = document.createElement('div')
  const isFromLeft = x < window.innerWidth / 2

  mask.style.cssText = `
    position: fixed;
    top: 0;
    ${isFromLeft ? 'left: 0' : 'right: 0'};
    width: 0;
    height: 100vh;
    background: var(--background);
    pointer-events: none;
    z-index: 9999;
  `
  document.body.appendChild(mask)

  const tl = gsap.timeline({
    onComplete: () => mask.remove()
  })

  tl.to(mask, {
    width: '100vw',
    duration: duration / 2000,
    ease: 'power2.inOut'
  })
  .to(mask, {
    width: 0,
    [isFromLeft ? 'left' : 'right']: 'auto',
    [isFromLeft ? 'right' : 'left']: 0,
    duration: duration / 2000,
    ease: 'power2.inOut'
  })

  await tl.play()
}

/**
 * 主题切换动画 - 光束扫描效果
 */
export async function beamTransition(options: TransitionOptions): Promise<void> {
  const { x, y, duration = 700, reducedMotion = false } = options

  if (reducedMotion) return

  const root = document.documentElement
  const isDark = root.classList.contains('dark')

  // 创建光束元素
  const beam = document.createElement('div')
  beam.style.cssText = `
    position: fixed;
    left: ${x}px;
    top: ${y}px;
    width: 2px;
    height: 100vh;
    background: linear-gradient(to bottom, 
      transparent 0%, 
      ${isDark ? '#3B82F6' : '#F59E0B'} 50%, 
      transparent 100%);
    pointer-events: none;
    z-index: 9999;
    transform: translateX(-50%) scaleY(0);
    box-shadow: 0 0 20px ${isDark ? '#3B82F6' : '#F59E0B'};
  `
  document.body.appendChild(beam)

  const tl = gsap.timeline({
    onComplete: () => beam.remove()
  })

  // 光束展开
  tl.to(beam, {
    scaleY: 1,
    duration: duration / 3000,
    ease: 'power2.out'
  })
  // 光束扫描
  .to(beam, {
    left: window.innerWidth,
    duration: duration / 1500,
    ease: 'none'
  })
  // 光束收缩
  .to(beam, {
    scaleY: 0,
    duration: duration / 3000,
    ease: 'power2.in'
  })

  await tl.play()
}

/**
 * 主题切换动画 - 组合效果（推荐）
 */
export async function epicTransition(options: TransitionOptions): Promise<void> {
  const { x, y, duration = 650, reducedMotion = false } = options

  if (reducedMotion) return

  const root = document.documentElement
  const isDark = root.classList.contains('dark')

  // 创建多层遮罩
  const overlay = document.createElement('div')
  overlay.style.cssText = `
    position: fixed;
    top: 0;
    left: 0;
    width: 100vw;
    height: 100vh;
    pointer-events: none;
    z-index: 9999;
    background: radial-gradient(circle at ${x}px ${y}px, 
      transparent 0%, 
      var(--background) 100%);
  `
  document.body.appendChild(overlay)

  // 创建光环效果
  const ring = document.createElement('div')
  ring.style.cssText = `
    position: fixed;
    left: ${x}px;
    top: ${y}px;
    width: 40px;
    height: 40px;
    border: 3px solid ${isDark ? '#3B82F6' : '#F59E0B'};
    border-radius: 50%;
    pointer-events: none;
    z-index: 10000;
    transform: translate(-50%, -50%);
    opacity: 0.8;
    box-shadow: 0 0 20px ${isDark ? '#3B82F6' : '#F59E0B'};
  `
  document.body.appendChild(ring)

  // 创建粒子
  const particles = createParticles(x, y, !isDark)

  const maxRadius = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y)
  )

  const tl = gsap.timeline({
    onComplete: () => {
      overlay.remove()
      ring.remove()
      particles.forEach(p => p.remove())
    }
  })

  // 1. 光环扩散
  tl.to(ring, {
    width: maxRadius * 2,
    height: maxRadius * 2,
    opacity: 0,
    duration: duration / 1000,
    ease: 'power2.out'
  }, 0)

  // 2. 粒子爆发
  particles.forEach((particle, i) => {
    const angle = (i / particles.length) * Math.PI * 2
    const distance = 100 + Math.random() * 60
    const tx = Math.cos(angle) * distance
    const ty = Math.sin(angle) * distance

    tl.to(particle, {
      x: tx,
      y: ty,
      opacity: 0,
      scale: 0,
      rotation: Math.random() * 360,
      duration: duration / 1000 * 0.7,
      ease: 'power3.out'
    }, 0)
  })

  // 3. 遮罩扩散
  tl.fromTo(overlay,
    {
      background: `radial-gradient(circle at ${x}px ${y}px, transparent 0%, var(--background) 0%)`
    },
    {
      background: `radial-gradient(circle at ${x}px ${y}px, transparent ${maxRadius}px, var(--background) ${maxRadius}px)`,
      duration: duration / 1000,
      ease: 'power2.inOut'
    },
    0
  )

  // 4. 页面元素波浪式动画
  const elements = Array.from(document.querySelectorAll('header, main, aside, nav, [class*="card"]'))
  elements.forEach((el, i) => {
    tl.fromTo(el as HTMLElement,
      { 
        opacity: 1, 
        scale: 1,
        filter: 'blur(0px)'
      },
      {
        opacity: 0.5,
        scale: 0.98,
        filter: 'blur(2px)',
        duration: duration / 1000 * 0.25,
        ease: 'power1.inOut',
        yoyo: true,
        repeat: 1
      },
      i * 0.015
    )
  })

  await tl.play()
}

/**
 * 主题切换动画 - View Transitions API 扩散效果（推荐）
 * 使用浏览器原生 API，性能更好，代码更简洁
 */
export async function viewTransition(options: TransitionOptions): Promise<void> {
  const { x, y, duration = 300, reducedMotion = false } = options

  if (reducedMotion) return

  // 检查浏览器是否支持 View Transitions API
  if (!document.startViewTransition) {
    console.warn('View Transitions API not supported')
    return
  }

  const root = document.documentElement

  // 计算以鼠标为圆心的最大半径
  const endRadius = Math.hypot(
    Math.max(x, window.innerWidth - x),
    Math.max(y, window.innerHeight - y)
  )

  // 设置 CSS 变量供动画使用
  root.style.setProperty('--x', `${x}px`)
  root.style.setProperty('--y', `${y}px`)
  root.style.setProperty('--r', `${endRadius}px`)
  root.style.setProperty('--duration', `${duration}ms`)

  // 启动视图过渡并切换主题
  const transition = document.startViewTransition(() => {
    root.classList.toggle('dark')
  })

  await transition.ready
  await transition.finished
}

/**
 * 导出默认动画（推荐使用）
 */
export const themeTransition = viewTransition
