<script setup lang="ts">
import Logo from '../components/Logo.vue';
import Mascot from '../components/Mascot.vue';
import Icon from '../components/Icon.vue';
import { useFlow } from '../state';
import { go } from '../router';

const { key } = useFlow();
const built = ['IT undergrads', 'Fresh grads', 'Working engineers'];
</script>

<template>
  <div class="page">
    <header><Logo /><span class="lang">Site language: English</span></header>
    <section class="hero">
      <div class="art">
        <div class="disc" />
        <p class="say">Psst, I read 2,431 job posts this week so you don’t have to.</p>
        <span class="tag t1">Python</span>
        <span class="tag t2"><Icon name="sparkles" :size="16" /> LLM apps</span>
        <span class="tag t3">Cloud</span>
        <span class="tag t4"><Icon name="check" :size="16" /> System design</span>
        <Mascot :size="150" class="mas" />
      </div>
      <div class="copy">
        <h1>AI is changing tech. Your future in it can be certain.</h1>
        <p>See where software jobs are heading, which ones fit you, and exactly what to learn next.</p>
        <RouterLink :to="go(key, 'name')" class="btn btn-primary">Get started</RouterLink>
        <button type="button" class="btn btn-secondary">I already have an account</button>
      </div>
    </section>
    <footer>
      <span>Built for</span>
      <span v-for="b in built" :key="b" class="built">{{ b }}</span>
    </footer>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; display: flex; flex-direction: column; }
header { display: flex; justify-content: space-between; align-items: center; padding: 32px 80px; }
.lang { font-size: 12px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.hero { flex: 1; display: grid; grid-template-columns: 1fr 1fr; align-items: center; gap: 40px; padding: 20px 80px 60px; max-width: 1280px; margin: 0 auto; width: 100%; }
.art { position: relative; height: 380px; }
.disc { position: absolute; left: 12%; top: 18%; width: 330px; height: 330px; border-radius: 50%; background: var(--cream); }
.mas { position: absolute; left: 24%; top: 30%; width: 150px; }
.mas :deep(i) { }
.say { position: absolute; left: 14%; top: 0; width: 240px; background: #fff; border: 2px solid var(--line); border-radius: 16px; padding: 12px 16px; font-weight: 800; font-size: 14px; line-height: 1.35; }
.tag { position: absolute; display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 999px; background: #fff; border: 2px solid var(--line-strong); font-weight: 800; font-size: 14px; }
.t1 { left: 0; top: 46%; } .t3 { left: 4%; top: 84%; }
.t2 { right: 8%; top: 49%; background: var(--cream); border-color: var(--orange); }
.t2 svg { color: var(--orange); }
.t4 { right: 22%; top: 90%; background: var(--ink); color: #fff; border-color: var(--ink); }
.t4 svg { color: var(--yellow); }
.copy { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 14px; max-width: 380px; margin: 0 auto; }
h1 { font-size: 40px; line-height: 1.15; font-weight: 900; margin-bottom: 6px; letter-spacing: -.01em; }
.copy p { color: var(--muted); font-weight: 600; font-size: 15px; line-height: 1.5; margin-bottom: 14px; }
.copy .btn { width: 100%; }
footer { border-top: 2px solid var(--line); padding: 22px; display: flex; gap: 12px; justify-content: center; align-items: center; flex-wrap: wrap; font-size: 11px; font-weight: 900; letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.built { padding: 8px 16px; border-radius: 999px; border: 2px solid var(--line-strong); background: #fff; color: var(--ink); }
@media (max-width: 900px) {
  header { padding: 20px; } .hero { grid-template-columns: 1fr; padding: 10px 20px 40px; } h1 { font-size: 32px; }
  .art { height: 340px; max-width: 420px; margin: 0 auto; width: 100%; }
  .disc { left: 15%; width: 260px; height: 260px; } .mas { left: 28%; top: 34%; }
}
</style>
