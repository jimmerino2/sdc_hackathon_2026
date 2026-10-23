<script setup lang="ts">
import { computed } from 'vue';
import Icon from './Icon.vue';
import { MAX_INTERESTS, type Interest } from '../api/interests';

/** The interest tiles, up to MAX_INTERESTS picked. Used in onboarding and on the profile. */
const props = defineProps<{ interests: Interest[]; hintId: string }>();
const picked = defineModel<number[]>({ required: true });

const full = computed(() => picked.value.length >= MAX_INTERESTS);

function toggle(id: number) {
  if (picked.value.includes(id)) picked.value = picked.value.filter((i) => i !== id);
  else if (!full.value) picked.value = [...picked.value, id];
}
</script>

<template>
  <p :id="props.hintId" class="hint">Pick up to {{ MAX_INTERESTS }} · {{ picked.length }} of {{ MAX_INTERESTS }} picked</p>
  <div class="grid" role="group" :aria-describedby="props.hintId">
    <button
      v-for="i in props.interests"
      :key="i.id"
      type="button"
      class="option tile"
      :class="{ selected: picked.includes(i.id) }"
      :aria-pressed="picked.includes(i.id)"
      :disabled="full && !picked.includes(i.id)"
      @click="toggle(i.id)"
    >
      <span class="ic" aria-hidden="true"><Icon :name="i.icon" :size="22" /></span>
      <span class="txt">
        <h3>{{ i.interest }}</h3>
      </span>
      <span v-if="picked.includes(i.id)" class="tick" aria-hidden="true"><Icon name="check" :size="14" :stroke="3" /></span>
    </button>
  </div>
</template>

<style scoped>
.hint { font-size: 13px; font-weight: 800; color: var(--muted); margin-bottom: 12px; }
.grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.tile { position: relative; flex-direction: column; justify-content: center; min-height: 112px; padding: 14px 10px; gap: 10px; text-align: center; }
.tile:disabled { opacity: .45; cursor: not-allowed; }
.ic { flex: none; width: 44px; height: 44px; border-radius: 12px; background: var(--cream); display: grid; place-items: center; }
.selected .ic { background: var(--yellow); }
.txt { min-width: 0; }
.tile h3 { font-size: 14px; line-height: 1.25; }
.tick { position: absolute; top: 8px; right: 8px; }
@media (max-width: 420px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
