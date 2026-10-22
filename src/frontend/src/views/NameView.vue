<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import { useFlow } from '../state';
import { go } from '../router';

const router = useRouter();
const { state } = useFlow();
const empty = computed(() => !state.value.name.trim());

function submit() {
  if (empty.value) return;
  state.value.name = state.value.name.trim();
  router.push(go('who'));
}
</script>

<template>
  <FlowShell :progress="0" next="who" back="bee" :next-disabled="empty" @next="state.name = state.name.trim()">
    <h1>What do we call you?</h1>
    <Bubble class="b">Hi, I’m Jobee! Before we start, what should I call you?</Bubble>
    <form @submit.prevent="submit">
      <input v-model="state.name" class="field" type="text" placeholder="Your first name or nickname" maxlength="40" autocomplete="given-name" autofocus />
    </form>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.field {
  width: 100%; padding: 16px 18px; border: 2px solid var(--line-strong); border-radius: 16px; background: #fff;
  font: 800 17px 'Nunito', sans-serif; color: var(--ink); outline: none;
}
.field:focus { border-color: var(--orange); }
</style>
