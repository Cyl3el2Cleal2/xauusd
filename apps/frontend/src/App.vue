<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { initFlowbite } from 'flowbite'
import { onMounted } from 'vue'
import Navbar from './components/Navbar.vue'

onMounted(() => {
  initFlowbite()
})
</script>

<template>
  <Navbar />
  <RouterView />
</template>
