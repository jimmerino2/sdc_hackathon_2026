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
type Item = { id: TabId; label: string; icon: string; to: Step };
const items: Item[] = [
  { id: 'learn', label: 'Learn', icon: 'route', to: 'pathway' },
  { id: 'roles', label: 'Roles', icon: 'tup', to: 'suggested' },
  { id: 'profile', label: 'Profile', icon: 'user', to: 'profile' },
];
/** The market-insight tabs, grouped together just above Log out. */
const insights: Item[] = [
  { id: 'outlook', label: 'AI outlook', icon: 'sparkles', to: 'outlook' },
  { id: 'occupations', label: 'Occupations', icon: 'chart-bar', to: 'occupations' },
];
const groups = [items, insights];
/** Active tab; the highlight pill springs to it within its group. */
const KEY = 'jobee_nav_tab';
const shown = ref<TabId | undefined>((sessionStorage.getItem(KEY) as TabId | null) ?? active.value);
const pillIdx = (g: Item[]) => g.findIndex((i) => i.id === shown.value);
// The layout stays mounted across tabs, so the pill springs whenever the active tab changes.
watch(active, (id) => { shown.value = id; if (id) sessionStorage.setItem(KEY, id); });
onMounted(async () => {
  await nextTick();
  requestAnimationFrame(() => { shown.value = active.value; if (active.value) sessionStorage.setItem(KEY, active.value); });
});
</script>

<template>
  <div class="layout">
    <aside>
      <nav class="jb jb-nav" aria-label="Main">
        <Logo class="brand jb-nav__logo" to="pathway" />
        <div v-for="(g, n) in groups" :key="n" class="jb-nav__list" :class="{ 'jb-nav__insights': g === insights }" :style="{ '--idx': Math.max(0, pillIdx(g)) }">
          <span v-show="pillIdx(g) >= 0" class="jb-nav__pill" aria-hidden="true" />
          <RouterLink v-for="i in g" :key="i.id" :to="go(i.to)" class="jb-nav__item" :aria-current="i.id === active ? 'page' : undefined">
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
.jb-nav__insights { margin-top: auto; padding-top: 16px; border-top: 2px solid var(--line); }
/* The pill is positioned from the padding edge, so it skips the divider's padding. */
.jb-nav__insights .jb-nav__pill { top: 16px; }
.jb-nav__logout { margin-top: 8px; width: 100%; }
@media (max-width: 860px) {
  .jb-nav__insights { margin-top: 0; padding-top: 0; border-top: 0; padding-left: 12px; border-left: 2px solid var(--line); }
  .jb-nav__logout { margin-top: 0; margin-left: auto; width: auto; }
  .layout { flex-direction: column; }
  aside { width: 100%; height: auto; position: static; border-right: 0; border-bottom: 2px solid var(--line); overflow-x: auto; }
  .jb-nav { flex-direction: row; align-items: center; gap: 12px; }
  .jb-nav__logo { padding: 0; }
  .content { padding: 24px 16px 80px; }
}
</style>
