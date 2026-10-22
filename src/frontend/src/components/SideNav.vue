<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue';
import '../learn.css';
import Icon from './Icon.vue';
import Logo from './Logo.vue';
import { go, type Step } from '../router';

const props = defineProps<{ active: 'learn' | 'roles' | 'profile' }>();
const items: { id: 'learn' | 'roles' | 'profile'; label: string; icon: string; to: Step }[] = [
  { id: 'learn', label: 'Learn', icon: 'route', to: 'pathway' },
  { id: 'roles', label: 'Roles', icon: 'tup', to: 'suggested' },
  { id: 'profile', label: 'Profile', icon: 'user', to: 'profile' },
];
/** Position of the active item; the highlight pill springs to it. */
const idx = computed(() => Math.max(0, items.findIndex((i) => i.id === props.active)));
// Each page mounts its own nav, so start the pill where the last page left it and let it spring across.
const KEY = 'jobee_nav_idx';
const shown = ref(Number(sessionStorage.getItem(KEY) ?? idx.value));
onMounted(async () => {
  await nextTick();
  requestAnimationFrame(() => { shown.value = idx.value; sessionStorage.setItem(KEY, String(idx.value)); });
});
</script>

<template>
  <div class="layout">
    <aside>
      <nav class="jb jb-nav" aria-label="Main">
        <Logo class="brand jb-nav__logo" to="pathway" />
        <div class="jb-nav__list" :style="{ '--idx': shown }">
          <span class="jb-nav__pill" aria-hidden="true" />
          <RouterLink v-for="i in items" :key="i.id" :to="go(i.to)" class="jb-nav__item" :aria-current="i.id === active ? 'page' : undefined">
            <Icon :name="i.icon" :size="22" /><span>{{ i.label }}</span>
          </RouterLink>
        </div>
      </nav>
    </aside>
    <div class="content"><slot /></div>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }
aside { width: 240px; flex: none; border-right: 2px solid var(--line); padding: 20px 16px; position: sticky; top: 0; height: 100vh; }
.content { flex: 1; min-width: 0; padding: 32px 40px 80px; }
.jb-nav__item { text-decoration: none; }
@media (max-width: 860px) {
  .layout { flex-direction: column; }
  aside { width: 100%; height: auto; position: static; border-right: 0; border-bottom: 2px solid var(--line); overflow-x: auto; }
  .jb-nav { display: flex; align-items: center; gap: 12px; }
  .jb-nav__logo { padding: 0; }
  .content { padding: 24px 16px 80px; }
}
</style>
