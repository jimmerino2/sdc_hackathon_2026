<script setup lang="ts">
import SideNav from './components/SideNav.vue';
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="screen" mode="out-in">
      <!-- Tabs share one sidebar layout, keyed once, so switching tabs only animates the content. -->
      <SideNav v-if="route.meta.tabs" key="tabs">
        <Transition name="tab" mode="out-in">
          <component :is="Component" :key="route.fullPath" />
        </Transition>
      </SideNav>
      <component :is="Component" v-else :key="route.fullPath" />
    </Transition>
  </RouterView>
</template>
