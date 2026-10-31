<script setup lang="ts">
import { useRouter } from 'vue-router';
import Logo from '../components/Logo.vue';
import { go } from '../router';

const router = useRouter();
/** Back to wherever the reader came from; a page opened in a new tab has nowhere to go back to. */
const back = () => (window.history.state?.back ? router.back() : router.push(go('landing')));
const UPDATED = '31 October 2026';
</script>

<template>
  <div class="page">
    <header><Logo /></header>
    <main>
      <button type="button" class="back" @click="back">Back</button>
      <h1>Privacy Policy</h1>
      <p class="meta">Last updated {{ UPDATED }}. Written to follow Malaysia’s Personal Data Protection Act 2010 (PDPA).</p>

      <section class="card">
        <h2>What we collect</h2>
        <ul>
          <li><strong>Your profile:</strong> the name you choose, your bee, your stage (student, fresh graduate or working), your interests and your skills.</li>
          <li><strong>Your email address:</strong> used only to save your roadmap and send you a one-time login code. There is no password.</li>
          <li><strong>Your roadmap and progress:</strong> the role you chose, the skills you marked as learned and the challenges you completed.</li>
          <li><strong>Your resume, if you upload one:</strong> we read it to suggest skills. The file itself is not saved. Only the skills you confirm are kept.</li>
        </ul>
        <p>We don’t ask for your IC number, address, phone number, gender, race, religion or health information. Please don’t type them into your resume or profile.</p>
      </section>

      <section class="card">
        <h2>Why we use it</h2>
        <p>To match you to roles, build your learning roadmap, and let you come back to it. We don’t sell your data and we don’t use it for advertising.</p>
      </section>

      <section class="card">
        <h2>Who it is shared with</h2>
        <ul>
          <li><strong>Supabase</strong> stores your profile and roadmap, and sends your login code by email.</li>
          <li><strong>An AI model provider</strong> (through our gateway, currently Google Gemini) reads your resume text and profile to extract skills and write your roadmap. Their servers may be outside Malaysia.</li>
          <li><strong>LinkedIn</strong>, only if you choose “Larp on LinkedIn”. You approve the post on LinkedIn’s own screen. Jobee uses the permission once to publish it and doesn’t keep it.</li>
        </ul>
        <p>We don’t share your data with anyone else, unless the law requires us to.</p>
      </section>

      <section class="card">
        <h2>How long we keep it</h2>
        <p>Your profile and roadmap stay until you ask us to remove them. Resume files are not kept at all.</p>
      </section>

      <section class="card">
        <h2>Security</h2>
        <p>Data is sent over HTTPS and stored in a managed database with access rules. No online service is perfectly secure, so keep personal details out of your resume where you can.</p>
      </section>

      <section class="card">
        <h2>Your rights</h2>
        <p>You can ask to see, correct or delete the data we hold about you, and you can withdraw your consent at any time. You can already rename yourself and edit your skills on the Profile page. To see or delete everything else, contact the Jobee team using the email you signed up with.</p>
      </section>

      <section class="card">
        <h2>Children</h2>
        <p>If you are under 18, please use Jobee with a parent’s or guardian’s agreement.</p>
      </section>

      <section class="card">
        <h2>Changes</h2>
        <p>If we change how we use your data, we’ll update this page and the date at the top.</p>
      </section>
    </main>
  </div>
</template>

<style scoped>
.page { min-height: 100vh; display: flex; flex-direction: column; }
header { padding: 32px 80px; }
main { width: 100%; max-width: 720px; margin: 0 auto; padding: 8px 20px 80px; }
h1 { font-size: 34px; font-weight: 900; margin: 14px 0 6px; }
.meta { margin: 0 0 22px; font-size: 15px; font-weight: 600; color: var(--muted); }
.back { font-size: 14px; font-weight: 900; letter-spacing: .06em; text-transform: uppercase; color: var(--muted); }
.back:hover { color: var(--ink); }
.card { padding: 18px 22px; margin-bottom: 12px; }
h2 { margin: 0 0 8px; font-size: 20px; font-weight: 900; }
p, li { font-size: 16px; line-height: 24px; font-weight: 600; }
p { margin: 0 0 8px; }
p:last-child { margin-bottom: 0; }
ul { margin: 0 0 8px; padding-left: 20px; display: grid; gap: 6px; }
@media (max-width: 900px) { header { padding: 20px; } }
</style>
