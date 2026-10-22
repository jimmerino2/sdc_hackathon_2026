<script setup lang="ts">
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { personas, type PersonaKey } from '../data/flows';
import { stepLabels, steps, type Step } from '../router';

const route = useRoute();
const router = useRouter();
const persona = computed(() => (route.params.persona as PersonaKey) ?? 'a');
const step = computed(() => (route.name as Step) ?? 'landing');

function setPersona(k: PersonaKey) {
  router.push({ name: step.value, params: { persona: k } });
}
function setStep(e: Event) {
  router.push({ name: (e.target as HTMLSelectElement).value as Step, params: { persona: persona.value } });
}
</script>

<template>
  <div class="switcher" role="toolbar" aria-label="Prototype navigation">
    <div class="tabs">
      <button v-for="(p, k) in personas" :key="k" :class="{ on: persona === k }" :title="p.label" @click="setPersona(k as PersonaKey)">
        {{ k.toUpperCase() }}
      </button>
    </div>
    <select :value="step" @change="setStep">
      <option v-for="s in steps" :key="s" :value="s">{{ stepLabels[s] }}</option>
    </select>
  </div>
</template>

<style scoped>
.switcher {
  position: fixed; left: 12px; bottom: 12px; z-index: 50; display: flex; gap: 8px; align-items: center;
  background: var(--ink); color: #fff; padding: 6px; border-radius: 14px; box-shadow: 0 6px 20px rgba(0,0,0,.25);
}
.tabs { display: flex; gap: 4px; }
.tabs button { width: 30px; height: 30px; border-radius: 9px; font-weight: 900; font-size: 13px; color: #fff; }
.tabs button.on { background: var(--yellow); color: var(--ink); }
select { background: #333; color: #fff; border: 0; border-radius: 9px; padding: 7px 8px; font: 700 12px 'Nunito', sans-serif; }
</style>
