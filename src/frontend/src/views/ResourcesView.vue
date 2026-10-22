<script setup lang="ts">
import { computed } from 'vue';
import SideNav from '../components/SideNav.vue';
import Icon from '../components/Icon.vue';
import { resourceCatalog, pathwayFor } from '../data/flows';
import { useFlow } from '../state';
import { go } from '../router';

const { chosenRole } = useFlow();
const groups = computed(() =>
  pathwayFor(chosenRole.value).map((skill) => ({ skill, items: resourceCatalog[skill] ?? resourceCatalog.default! })),
);
</script>

<template>
  <SideNav active="resources">
    <div class="page">
      <p class="eyebrow">Skill resources</p>
      <h1>Everything you need for {{ chosenRole.title }}</h1>
      <p class="sub">Hand-picked, free where possible. Ordered to match your pathway.</p>
      <section v-for="(g, gi) in groups" :key="g.skill" class="group">
        <h2><span class="num">{{ gi + 1 }}</span>{{ g.skill }}</h2>
        <div class="list">
          <article v-for="r in g.items" :key="r.title" class="card item">
            <span class="ic"><Icon :name="r.kind === 'Project' ? 'code' : r.kind === 'Reading' ? 'book' : 'play'" :size="20" /></span>
            <div class="txt"><strong>{{ r.title }}</strong><small>{{ r.provider }} · {{ r.kind }} · {{ r.duration }}</small></div>
            <RouterLink :to="go('pathway')" class="btn btn-secondary go">Open</RouterLink>
          </article>
        </div>
      </section>
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
</style>
