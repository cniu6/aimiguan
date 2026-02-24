<script setup lang="ts">
import type { HTMLAttributes } from 'vue'
import 'media-chrome'

interface Props {
  class?: HTMLAttributes['class']
  style?: HTMLAttributes['style']
}

const props = defineProps<Props>()
</script>

<template>
  <media-controller
    audio
    data-slot="audio-player"
    :class="props.class"
    :style="[
      {
        '--media-background-color': 'transparent',
        '--media-button-icon-height': '1rem',
        '--media-button-icon-width': '1rem',
        '--media-control-background': 'transparent',
        '--media-control-hover-background': 'var(--accent)',
        '--media-font': 'var(--font-sans)',
        '--media-font-size': '10px',
        '--media-icon-color': 'currentColor',
        '--media-preview-time-background': 'var(--background)',
        '--media-preview-time-border-radius': 'var(--radius-md)',
        '--media-preview-time-text-shadow': 'none',
        '--media-primary-color': 'var(--primary)',
        '--media-range-bar-color': 'var(--primary)',
        '--media-range-track-background': 'var(--secondary)',
        '--media-secondary-color': 'var(--secondary)',
        '--media-text-color': 'var(--foreground)',
        '--media-tooltip-arrow-display': 'none',
        '--media-tooltip-background': 'var(--background)',
        '--media-tooltip-border-radius': 'var(--radius-md)',
      },
      props.style,
    ]"
  >
    <slot />
  </media-controller>
</template>
