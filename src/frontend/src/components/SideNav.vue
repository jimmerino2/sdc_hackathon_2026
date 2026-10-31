<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";
import "../learn.css";
import Icon from "./Icon.vue";
import Logo from "./Logo.vue";
import { go, router, type Step } from "../router";
import { signOut } from "../state";

function logout() {
  signOut();
  sessionStorage.removeItem(KEY);
  router.push(go("landing"));
}

/** The app layout after onboarding. It stays mounted while the learner switches tabs; only the content slot changes. */
const route = useRoute();
type TabId = 'learn' | 'roles' | 'challenges' | 'social' | 'outlook' | 'occupations' | 'benchmark' | 'profile';
const tabFor: Record<string, TabId> = { pathway: 'learn', suggested: 'roles', role: 'roles', challenges: 'challenges', hive: 'challenges', social: 'social', outlook: 'outlook', occupations: 'occupations', benchmark: 'benchmark', profile: 'profile' };
const active = computed(() => tabFor[route.name as string]);
type Item = { id: TabId; label: string; icon: string; to: Step };
/** A collapsed entry: its tabs open in a dropdown on hover or keyboard focus. */
type Menu = { id: string; label: string; icon: string; children: Item[] };
type Entry = Item | Menu;
const isMenu = (e: Entry): e is Menu => 'children' in e;
const holds = (e: Entry, id: TabId | undefined) => e.id === id || (isMenu(e) && e.children.some((c) => c.id === id));
const items: Entry[] = [
  { id: 'learn', label: 'Learn', icon: 'route', to: 'pathway' },
  { id: 'roles', label: 'Roles', icon: 'tup', to: 'suggested' },
  { id: 'community', label: 'Community', icon: 'users', children: [
    { id: 'challenges', label: 'Challenges', icon: 'trophy', to: 'challenges' },
    { id: 'social', label: 'Social', icon: 'users', to: 'social' },
  ] },
  { id: 'profile', label: 'Profile', icon: 'user', to: 'profile' },
];
/** The market-insight tabs, grouped together just above Log out. */
const insights: Entry[] = [
  { id: 'insights', label: 'Insights', icon: 'sparkles', children: [
    { id: 'outlook', label: 'AI outlook', icon: 'sparkles', to: 'outlook' },
    { id: 'occupations', label: 'Occupations', icon: 'chart-bar', to: 'occupations' },
    // A dev tool, so it stays out of the deployed app's nav.
    ...(import.meta.env.DEV ? [{ id: 'benchmark', label: 'Benchmark', icon: 'brain', to: 'benchmark' } as Item] : []),
  ] },
];
const groups = [items, insights];
/** The open dropdown's Menu id. */
const open = ref<string>();
/** Active tab; the highlight pill springs to it within its group. */
const KEY = "jobee_nav_tab";
const shown = ref<TabId | undefined>((sessionStorage.getItem(KEY) as TabId | null) ?? active.value);
const pillIdx = (g: Entry[]) => g.findIndex((e) => holds(e, shown.value));
// The layout stays mounted across tabs, so the pill springs whenever the active tab changes.
watch(active, (id) => { shown.value = id; open.value = undefined; if (id) sessionStorage.setItem(KEY, id); });
onMounted(async () => {
  await nextTick();
  requestAnimationFrame(() => {
    shown.value = active.value;
    if (active.value) sessionStorage.setItem(KEY, active.value);
  });
});
</script>

<template>
  <div class="layout">
    <aside>
      <nav class="jb jb-nav" aria-label="Main">
        <Logo class="brand jb-nav__logo" to="pathway" />
        <div
          v-for="(g, n) in groups"
          :key="n"
          class="jb-nav__list"
          :class="{ 'jb-nav__insights': g === insights }"
          :style="{ '--idx': Math.max(0, pillIdx(g)) }"
        >
          <span v-show="pillIdx(g) >= 0" class="jb-nav__pill" aria-hidden="true" />
                    <template v-for="i in g" :key="i.id">
            <div
              v-if="isMenu(i)"
              class="jb-nav__group"
              :class="{ 'is-open': open === i.id, 'is-bottom': g === insights }"
              @mouseenter="open = i.id"
              @mouseleave="open = undefined"
              @focusin="open = i.id"
              @focusout="open = undefined"
              @keydown.esc="open = undefined"
            >
              <button
                type="button"
                class="jb-nav__item jb-nav__trigger"
                :class="{ 'is-current': holds(i, active) }"
                aria-haspopup="true"
                :aria-expanded="open === i.id"
              >
                <Icon :name="i.icon" :size="22" /><span>{{ i.label }}</span
                ><Icon name="chevron" :size="18" class="jb-nav__caret" />
              </button>
              <div class="jb-nav__flyout">
                <div class="jb-nav__panel">
                  <RouterLink
                    v-for="c in i.children"
                    :key="c.id"
                    :to="go(c.to)"
                    class="jb-nav__item"
                    :aria-current="c.id === active ? 'page' : undefined"
                  >
                    <Icon :name="c.icon" :size="22" /><span>{{ c.label }}</span>
                  </RouterLink>
                </div>
              </div>
            </div>
            <RouterLink v-else :to="go(i.to)" class="jb-nav__item" :aria-current="i.id === active ? 'page' : undefined">
              <Icon :name="i.icon" :size="22" /><span>{{ i.label }}</span>
            </RouterLink>
          </template>
                  </div>
        <RouterLink :to="go('privacy')" class="jb-nav__item jb-nav__privacy"
          ><Icon name="shield-check" :size="22" /><span>Privacy</span></RouterLink
        >
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
/* z-index keeps the dropdowns over the page content, and under its modals. */
aside { width: 240px; flex: none; border-right: 2px solid var(--line); padding: 20px 16px; position: sticky; top: 0; height: 100vh; z-index: 20; }
.content { flex: 1; min-width: 0; padding: 32px 40px 80px; }
.jb-nav__item { text-decoration: none; }
aside { display: flex; }
.jb-nav { display: flex; flex-direction: column; flex: 1; }
.jb-nav__insights { margin-top: auto; padding-top: 16px; border-top: 2px solid var(--line); }
/* The pill is positioned from the padding edge, so it skips the divider's padding. */
.jb-nav__insights .jb-nav__pill { top: 16px; }
.jb-nav__group { position: relative; }
.jb-nav__trigger { width: 100%; }
.jb-nav__trigger.is-current { color: var(--text); }
.jb-nav__trigger.is-current svg { color: var(--accent-text); }
.jb-nav__item .jb-nav__caret, .jb-nav__item:hover .jb-nav__caret { margin-left: auto; transform: rotate(-90deg); color: var(--text-muted); }
@media (min-width: 861px) {
  /* The left padding bridges the gap to the sidebar, so the hover survives the move across it. */
  .jb-nav__flyout { display: none; position: absolute; top: 0; left: 100%; padding-left: 24px; }
  .jb-nav__group.is-bottom .jb-nav__flyout { top: auto; bottom: 0; }
  .jb-nav__group.is-open .jb-nav__flyout { display: block; }
  .jb-nav__panel { display: flex; flex-direction: column; gap: 4px; width: 230px; padding: 8px; background: var(--surface-raised); border: 2px solid var(--line); border-radius: var(--radius-md); box-shadow: 0 3px 0 var(--line); }
  .jb-nav__panel .jb-nav__item[aria-current="page"] { background: var(--honey-tint); }
}
.jb-nav__privacy { margin-top: 8px; width: 100%; }
.jb-nav__logout { margin-top: 2px; width: 100%; }
@media (max-width: 860px) {
  .jb-nav__insights { margin-top: 0; padding-top: 0; border-top: 0; padding-left: 12px; border-left: 2px solid var(--line); }
  /* Touch has no hover, and the row already scrolls, so the tabs stay flat here. */
  .jb-nav__trigger { display: none; }
  .jb-nav__group, .jb-nav__flyout, .jb-nav__panel { display: contents; }
  .jb-nav__privacy { margin-top: 0; margin-left: auto; width: auto; }
  .jb-nav__logout { margin-top: 0; width: auto; }
  .layout { flex-direction: column; }
  aside { width: 100%; height: auto; position: static; border-right: 0; border-bottom: 2px solid var(--line); overflow-x: auto; }
  .jb-nav { flex-direction: row; align-items: center; gap: 12px; }
  .jb-nav__logo { padding: 0; }
  .content { padding: 24px 16px 80px; }
}
</style>
