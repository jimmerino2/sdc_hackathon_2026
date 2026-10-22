<script setup lang="ts">
import { computed } from 'vue';
import { useRoute } from 'vue-router';
import Icon from './Icon.vue';
import Logo from './Logo.vue';
import { go, type Step } from '../router';

/** The app layout after onboarding. It stays mounted while the learner switches tabs; only the content slot changes. */
const route = useRoute();
const tabFor: Record<string, 'learn' | 'roles' | 'profile'> = { pathway: 'learn', suggested: 'roles', role: 'roles', profile: 'profile' };
const active = computed(() => tabFor[route.name as string]);
const items: { id: 'learn' | 'roles' | 'profile'; label: string; icon: string; to: Step }[] = [
  { id: 'learn', label: 'Learn', icon: 'route', to: 'pathway' },
  { id: 'roles', label: 'Roles', icon: 'tup', to: 'suggested' },
  { id: 'profile', label: 'Profile', icon: 'user', to: 'profile' },
];
</script>

<template>
  <div class="layout">
    <aside>
      <Logo class="brand" to="pathway" />
      <nav>
        <RouterLink v-for="i in items" :key="i.id" :to="go(i.to)" :class="{ on: i.id === active }">
          <Icon :name="i.icon" :size="20" /> {{ i.label }}
        </RouterLink>
      </nav>
    </aside>
    <div class="content"><slot /></div>
  </div>
</template>

<style scoped>
.layout { display: flex; min-height: 100vh; }
aside { width: 240px; flex: none; border-right: 2px solid var(--line); padding: 20px 16px; position: sticky; top: 0; height: 100vh; }
.brand { margin: 0 0 28px 6px; }
nav { display: flex; flex-direction: column; gap: 6px; }
nav a {
  display: flex; align-items: center; gap: 14px; padding: 14px 16px; border-radius: 14px; border: 2px solid transparent;
  font-weight: 900; font-size: 13px; letter-spacing: .08em; text-transform: uppercase; color: var(--muted);
}
nav a { transition: background .15s, color .15s; }
nav a:hover { background: rgba(255, 193, 7, .1); color: var(--ink); }
nav a:active { translate: 0 1px; }
nav a.on { background: var(--cream); border-color: var(--yellow); color: var(--ink); }
.content { flex: 1; min-width: 0; padding: 32px 40px 80px; }
@media (max-width: 860px) {
  .layout { flex-direction: column; }
  aside { width: 100%; height: auto; position: static; border-right: 0; border-bottom: 2px solid var(--line); display: flex; align-items: center; gap: 12px; overflow-x: auto; }
  .brand { margin: 0; }
  nav { flex-direction: row; }
  nav a { padding: 10px 12px; font-size: 11px; white-space: nowrap; }
  .content { padding: 24px 16px 80px; }
}
</style>
