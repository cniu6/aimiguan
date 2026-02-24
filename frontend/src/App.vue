<template>
  <router-view />
  <Toaster position="top-right" :theme="'dark'" rich-colors />
</template>

<script setup lang="ts">
import { Toaster } from '@/components/ui/sonner'
</script>