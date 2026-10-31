<script setup lang="ts">
import Logo from '../components/Logo.vue';
import HeroScene from '../components/HeroScene.vue';
import { go } from '../router';
</script>

<template>
  <div class="page">
    <header><Logo /></header>
    <main class="hero">
      <div class="art"><HeroScene /></div>
      <div class="copy">
        <h1>Get ready for how AI is changing your next tech role.</h1>
        <div class="ctas">
          <RouterLink :to="go('bee')" class="btn btn-primary">Get started</RouterLink>
          <RouterLink :to="go('login')" class="btn btn-secondary">I already have an account</RouterLink>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; min-height: 100dvh; display: flex; flex-direction: column; }
header { padding: 28px 48px; }
.hero {
  flex: 1; display: grid; grid-template-columns: minmax(0, 1.55fr) minmax(0, 1fr); align-items: center; gap: 40px;
  width: 100%; max-width: 1360px; margin: 0 auto; padding: 0 40px 72px;
}
.art { position: relative; min-width: 0; }
.copy { display: flex; flex-direction: column; align-items: center; text-align: center; gap: 36px; max-width: 420px; margin: 0 auto; width: 100%; }
h1 { text-wrap: balance; font-size: 40px; line-height: 1.18; font-weight: 900; letter-spacing: -.015em; color: var(--ink); animation: rise .5s cubic-bezier(.2, .8, .3, 1) both; }
.ctas { display: flex; flex-direction: column; gap: 14px; width: 100%; animation: rise .5s .08s cubic-bezier(.2, .8, .3, 1) both; }
.ctas .btn { width: 100%; white-space: normal; text-align: center; }
@keyframes hover { 0%, 100% { transform: translate(0, 0) rotate(-2deg); } 50% { transform: translate(6px, -14px) rotate(2deg); } }
@keyframes breathe { 0%, 100% { transform: scale(1); } 50% { transform: scale(1.04); } }
@keyframes rise { from { opacity: 0; transform: translateY(10px); } }
@media (max-width: 860px) {
  header { padding: 18px 20px; }
  .hero { grid-template-columns: 1fr; gap: 20px; padding: 0 20px 40px; align-content: center; }
  h1 { font-size: 34px; }
  .copy { gap: 28px; }
}
@media (prefers-reduced-motion: reduce) { h1, .ctas { animation: none; } }
</style>
