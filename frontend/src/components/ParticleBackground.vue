<template>
  <canvas ref="canvas" class="fixed inset-0 pointer-events-none" style="z-index: 0;" />
</template>

<script setup lang="ts">
import { computed, ref, onMounted, onUnmounted } from 'vue'
import { useActiveMode } from '@/composables/useActiveMode'

const { activeMode } = useActiveMode()
const canvas = ref<HTMLCanvasElement>()
let ctx: CanvasRenderingContext2D | null = null
let particles: Particle[] = []
let animationId: number

const isProbeMode = computed(() => activeMode.value === 'probe')

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
}

const config = {
  particleCount: 80,
  particleSpeed: 0.3,
  lineDistance: 150,
  particleRadius: 2
}

function initCanvas() {
  if (!canvas.value) return
  
  canvas.value.width = window.innerWidth
  canvas.value.height = window.innerHeight
  ctx = canvas.value.getContext('2d')
  
  particles = Array.from({ length: config.particleCount }, () => ({
    x: Math.random() * canvas.value!.width,
    y: Math.random() * canvas.value!.height,
    vx: (Math.random() - 0.5) * config.particleSpeed,
    vy: (Math.random() - 0.5) * config.particleSpeed,
    radius: config.particleRadius
  }))
}

function animate() {
  if (!ctx || !canvas.value) return
  
  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)
  
  const particleColor = isProbeMode.value ? 'rgba(249, 115, 22, 0.6)' : 'rgba(59, 130, 246, 0.6)'
  const lineColor = isProbeMode.value ? 'rgba(249, 115, 22, 0.15)' : 'rgba(59, 130, 246, 0.15)'
  
  particles.forEach((p, i) => {
    p.x += p.vx
    p.y += p.vy
    
    if (p.x < 0 || p.x > canvas.value!.width) p.vx *= -1
    if (p.y < 0 || p.y > canvas.value!.height) p.vy *= -1
    
    ctx!.beginPath()
    ctx!.arc(p.x, p.y, p.radius, 0, Math.PI * 2)
    ctx!.fillStyle = particleColor
    ctx!.fill()
    
    for (let j = i + 1; j < particles.length; j++) {
      const p2 = particles[j]
      const dx = p.x - p2.x
      const dy = p.y - p2.y
      const distance = Math.sqrt(dx * dx + dy * dy)
      
      if (distance < config.lineDistance) {
        ctx!.beginPath()
        ctx!.moveTo(p.x, p.y)
        ctx!.lineTo(p2.x, p2.y)
        ctx!.strokeStyle = lineColor
        ctx!.lineWidth = 1
        ctx!.stroke()
      }
    }
  })
  
  animationId = requestAnimationFrame(animate)
}

function handleResize() {
  initCanvas()
}

onMounted(() => {
  initCanvas()
  animate()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  cancelAnimationFrame(animationId)
  window.removeEventListener('resize', handleResize)
})
</script>
