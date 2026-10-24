<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import '../learn.css';
import Icon from './Icon.vue';
import Logo from './Logo.vue';
import { go, router, type Step } from '../router';
import { signOut } from '../state';

function logout() {
  signOut();
  sessionStorage.removeItem(KEY);
  router.push(go('landing'));
}

/** The app layout after onboarding. It stays mounted while the learner switches tabs; only the content slot changes. */
const route = useRoute();
type TabId = 'learn' | 'roles' | 'outlook' | 'occupations' | 'profile';
const tabFor: Record<string, TabId> = { pathway: 'learn', suggested: 'roles', role: 'roles', outlook: 'outlook', occupations: 'occupations', profile: 'profile' };
const active = computed(() => tabFor[route.name as string]);
const items: { id: TabId; label: string; icon: string; to: Step }[] = [
  { id: 'learn', label: 'Learn', icon: 'route', to: 'pathway' },
  { id: 'roles', label: 'Roles', icon: 'tup', to: 'suggested' },
  { id: 'outlook', label: 'AI outlook', icon: 'sparkles', to: 'outlook' },
  { id: 'occupations', label: 'Occupations', icon: 'chart-bar', to: 'occupations' },
  { id: 'profile', label: 'Profile', icon: 'user', to: 'profile' },
];
/** Position of the active item; the highlight pill springs to it. */
const idx = computed(() => Math.max(0, items.findIndex((i) => i.id === active.value)));
const KEY = 'jobee_nav_idx';
const shown = ref(Number(sessionStorage.getItem(KEY) ?? idx.value));
// The layout stays mounted across tabs, so the pill springs whenever the active tab changes.
watch(idx, (i) => { shown.value = i; sessionStorage.setItem(KEY, String(i)); });
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
        <button type="button" class="jb-nav__item jb-nav__logout" @click="logout">
          <Icon name="logout" :size="22" /><span>Log out</span>
        </button>
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
aside { display: flex; }
.jb-nav { display: flex; flex-direction: column; flex: 1; }
.jb-nav__logout { margin-top: auto; width: 100%; }
@media (max-width: 860px) {
  .jb-nav__logout { margin-top: 0; margin-left: auto; width: auto; }
  .layout { flex-direction: column; }
  aside { width: 100%; height: auto; position: static; border-right: 0; border-bottom: 2px solid var(--line); overflow-x: auto; }
  .jb-nav { flex-direction: row; align-items: center; gap: 12px; }
  .jb-nav__logo { padding: 0; }
  .content { padding: 24px 16px 80px; }
}
</style>
