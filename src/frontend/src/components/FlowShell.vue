<script setup lang="ts">
import { computed } from 'vue';
import { useRouter } from 'vue-router';
import Icon from './Icon.vue';
import { useFlow } from '../state';
import { go, type Step } from '../router';

const props = defineProps<{
  progress: number;
  next: Step;
  skipTo?: Step;
  nextLabel?: string;
  skipLabel?: string;
  nextDisabled?: boolean;
}>();
const emit = defineEmits<{ next: [] }>();
const router = useRouter();
const { key } = useFlow();
const pct = computed(() => (props.progress / 5) * 100);

function onNext() {
  emit('next');
  router.push(go(key.value, props.next));
}
</script>

<template>
  <div class="shell">
    <header>
      <RouterLink :to="go(key, 'landing')" class="x" aria-label="Close"><Icon name="x" :size="22" /></RouterLink>
      <div class="progress"><i :style="{ width: pct + '%' }" /></div>
      <div class="streak"><Icon name="flame" :size="18" /> {{ progress }}/5</div>
    </header>
    <main><slot /></main>
    <footer>
      <RouterLink :to="go(key, skipTo ?? next)" class="btn btn-secondary">{{ skipLabel ?? 'Skip' }}</RouterLink>
      <button class="btn btn-primary" :disabled="nextDisabled" @click="onNext">{{ nextLabel ?? 'Continue' }}</button>
    </footer>
  </div>
</template>

<style scoped>
.shell { min-height: 100vh; display: flex; flex-direction: column; }
header { display: flex; align-items: center; gap: 20px; padding: 28px 24px 0; width: 100%; max-width: 820px; margin: 0 auto; }
header .progress { flex: 1; }
.x { color: #b9b6b0; display: grid; place-items: center; }
.streak { display: flex; align-items: center; gap: 4px; color: var(--orange); font-weight: 900; font-size: 14px; }
main { flex: 1; width: 100%; max-width: 580px; margin: 0 auto; padding: 48px 20px 40px; }
footer { border-top: 2px solid var(--line); padding: 20px 24px; display: flex; justify-content: space-between; }
@media (max-width: 640px) { main { padding-top: 32px; } .btn { padding: 14px 20px; } }
</style>
