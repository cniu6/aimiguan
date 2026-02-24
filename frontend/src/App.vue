<template>
  <ParticleBackground />
  <router-view />
  <Toaster position="top-right" rich-colors />
</template>

<script setup lang="ts">
import { Toaster } from '@/components/ui/sonner'
import ParticleBackground from '@/components/ParticleBackground.vue'
</script>