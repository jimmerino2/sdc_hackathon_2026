<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
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
  <FlowShell :progress="0" next="who" back="bee" mood="happy" :next-disabled="empty" @next="state.name = state.name.trim()">
    <template #bubble>What should I call you?</template>
    <form @submit.prevent="submit">
      <label for="name" class="label">First name or nickname</label>
      <input id="name" v-model="state.name" class="field" type="text" placeholder="e.g. Aisyah" maxlength="40" autocomplete="given-name" autofocus />
    </form>
  </FlowShell>
</template>

<style scoped>
.label { display: block; font-weight: 800; font-size: 16px; margin-bottom: 8px; }
.field {
  width: 100%; padding: 16px 18px; border: 2px solid var(--line-strong); border-radius: 16px; background: #fff;
  font: 800 18px 'Nunito', sans-serif; color: var(--ink); outline: none; transition: border-color .15s, box-shadow .15s;
}
.field::placeholder { color: #9a948a; font-weight: 700; }
.field:focus-visible, .field:focus { border-color: var(--orange); box-shadow: 0 0 0 4px rgba(255, 193, 7, .3); outline: none; }
</style>
