<script setup lang="ts">
import PersonaSwitcher from './components/PersonaSwitcher.vue';
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="screen" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </Transition>
  </RouterView>
  <PersonaSwitcher />
</template>
