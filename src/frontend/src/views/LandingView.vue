<script setup lang="ts">
import Logo from '../components/Logo.vue';
import Mascot from '../components/Mascot.vue';
import { go } from '../router';
import { BRAND_BEE } from '../bee';
</script>

<template>
  <div class="page">
    <header><Logo /></header>
    <main class="hero">
      <div class="art">
        <span class="disc" aria-hidden="true" />
        <Mascot :size="190" :bee="BRAND_BEE" class="mas" mood="wave" wings />
      </div>
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
  flex: 1; display: grid; grid-template-columns: 1fr 1fr; align-items: center; gap: 56px;
  width: 100%; max-width: 1080px; margin: 0 auto; padding: 0 40px 72px;
}
.art { position: relative; height: 380px; display: grid; place-items: center; }
.disc { position: absolute; width: 320px; height: 320px; border-radius: 50%; background: var(--cream); animation: breathe 6s ease-in-out infinite; }
.mas { position: relative; animation: hover 5s ease-in-out infinite; }
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
  .art { height: 240px; }
  .disc { width: 220px; height: 220px; }
  .mas { font-size: 140px !important; }
  h1 { font-size: 30px; }
  .copy { gap: 28px; }
}
@media (max-height: 640px) and (max-width: 860px) {
  .art { height: 170px; } .disc { width: 160px; height: 160px; } .mas { font-size: 100px !important; }
}
@media (prefers-reduced-motion: reduce) { .mas, .disc, h1, .ctas { animation: none; } }
</style>
