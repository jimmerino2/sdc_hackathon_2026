<script setup lang="ts">
import type { SdgFocus } from '../api/interests';

/** The UN goals the learner's interests point at, biggest first: the SDG view of their matches. */
defineProps<{ focus: SdgFocus[] }>();
</script>

<template>
  <section v-if="focus.length" class="sdg" aria-label="Your SDG focus">
    <p class="head">Matched to the goals you care about</p>
    <ul>
      <li v-for="f in focus.slice(0, 5)" :key="f.sdg" :title="`${Math.round(f.value * 100)}% of your interests`">
        <b class="num">{{ f.sdg }}</b>
        <span class="name">{{ f.name }}</span>
        <i class="bar" aria-hidden="true"><s :style="{ width: Math.round(f.value * 100) + '%' }" /></i>
      </li>
    </ul>
  </section>
</template>

<style scoped>
.sdg { margin-bottom: 20px; padding: 14px 16px; border: 2px solid var(--line-strong); border-radius: 16px; background: #fff; }
.head { margin-bottom: 10px; font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--orange); }
ul { list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }
li { position: relative; overflow: hidden; display: inline-flex; align-items: center; gap: 8px; padding: 6px 12px 8px 6px; border-radius: 999px; background: var(--cream); font-size: 12px; font-weight: 800; color: var(--ink); }
.num { flex: none; display: grid; place-items: center; width: 22px; height: 22px; border-radius: 50%; background: var(--yellow); font-size: 12px; font-weight: 900; }
.name { white-space: nowrap; }
.bar { position: absolute; left: 0; right: 0; bottom: 0; height: 3px; background: rgba(30, 30, 30, .08); }
.bar s { display: block; height: 100%; background: var(--orange); text-decoration: none; }
</style>
