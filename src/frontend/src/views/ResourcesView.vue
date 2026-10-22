<script setup lang="ts">
import { computed, onMounted } from 'vue';
import SideNav from '../components/SideNav.vue';
import Icon from '../components/Icon.vue';
import Bubble from '../components/Bubble.vue';
import type { RoadmapSource } from '../api/roadmap';
import { skillLabel } from '../data/skills';
import { loadRoadmap, useFlow } from '../state';
import { go } from '../router';

const { state } = useFlow();
const kinds: Record<RoadmapSource['source_type'], { label: string; icon: string }> = {
  project: { label: 'Project', icon: 'code' },
  certificate: { label: 'Certificate', icon: 'grad' },
  video: { label: 'Video', icon: 'play' },
  activity: { label: 'Practice', icon: 'target' },
};

const roadmap = computed(() => state.value.roadmap.data);
/** The roadmap's skills in learning order (section, then unit), each with where to learn it. */
const groups = computed(() =>
  (roadmap.value?.sections ?? []).flatMap((sec) => sec.units.flatMap((u) => u.nodes)).map((n) => ({ node: n, items: n.sources })),
);

function host(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

onMounted(() => {
  // Opened directly (e.g. after a refresh or a login): fetch the roadmap if a profile is known.
  if (state.value.roadmap.status === 'idle') loadRoadmap(state.value);
});
</script>

<template>
  <SideNav active="resources">
    <div class="page">
      <p class="eyebrow">Skill resources</p>
      <div v-if="!roadmap" class="state">
        <Bubble :size="64">{{ state.roadmap.status === 'error' ? state.roadmap.error : 'Loading your resources…' }}</Bubble>
        <RouterLink v-if="state.roadmap.status === 'error'" :to="go('roles')" class="btn btn-secondary">Back to my roles</RouterLink>
      </div>
      <template v-else>
        <h1>Everything you need for {{ roadmap.title }}</h1>
        <p class="sub">Links for each skill on your roadmap, in the order you’ll learn them.</p>
        <section v-for="(g, gi) in groups" :key="g.node.roadmap_detail_id" class="group">
          <h2><span class="num">{{ gi + 1 }}</span>{{ skillLabel(g.node.skill_name) }}</h2>
          <div v-if="g.items.length" class="list">
            <article v-for="r in g.items" :key="r.url" class="card item">
              <span class="ic"><Icon :name="kinds[r.source_type].icon" :size="20" /></span>
              <div class="txt"><strong>{{ r.title }}</strong><small>{{ host(r.url) }} · {{ kinds[r.source_type].label }}</small></div>
              <a :href="r.url" target="_blank" rel="noopener noreferrer" class="btn btn-secondary go">Open ↗</a>
            </article>
          </div>
          <p v-else class="none">We don’t have a recommended resource for this one yet.</p>
        </section>
      </template>
    </div>
  </SideNav>
</template>

<style scoped>
.page { max-width: 760px; }
.eyebrow { font-size: 12px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
h1 { font-size: 30px; font-weight: 900; margin: 6px 0 8px; line-height: 1.15; }
.sub { color: var(--muted); font-weight: 600; margin-bottom: 28px; }
.group { margin-bottom: 26px; }
h2 { display: flex; align-items: center; gap: 10px; font-size: 18px; font-weight: 900; margin-bottom: 12px; }
.num { width: 28px; height: 28px; border-radius: 50%; background: var(--yellow); box-shadow: 0 3px 0 var(--orange); display: grid; place-items: center; font-size: 13px; }
.list { display: flex; flex-direction: column; gap: 10px; }
.item { display: flex; align-items: center; gap: 14px; padding: 14px 16px; }
.ic { width: 42px; height: 42px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; flex: none; }
.txt { display: flex; flex-direction: column; gap: 2px; flex: 1; min-width: 0; } .txt strong { font-weight: 800; font-size: 15px; } .txt small { font-size: 12px; color: var(--muted); font-weight: 600; }
.go { padding: 10px 18px; font-size: 12px; }
.none { font-size: 13px; font-weight: 600; color: var(--muted); }
.state { margin: 24px 0; display: flex; flex-direction: column; align-items: flex-start; gap: 16px; }
</style>
