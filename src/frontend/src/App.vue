<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="screen" mode="out-in">
      <component :is="Component" :key="route.fullPath" />
    </Transition>
  </RouterView>
</template>
