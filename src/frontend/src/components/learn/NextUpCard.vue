<script setup lang="ts">
import { computed } from 'vue';
import Icon from '../Icon.vue';
import JbButton from './JbButton.vue';

export interface NextUpSkill {
  id: string;
  name: string;
  state: 'ready' | 'done' | 'locked';
  kind: string;
  blurb: string | null;
  blockers: string[];
  links: { title: string; url: string; kind: string }[];
}

const props = defineProps<{ skill: NextUpSkill | null; selected: boolean; busy?: boolean; error?: string | null }>();
defineEmits<{ complete: [] }>();
const blockerText = computed(() => props.skill?.blockers.join(' and ') || 'the earlier skills');
</script>

<template>
  <section class="jb jb-card jb-next">
    <p class="jb-eyebrow">Next up</p>
    <div v-if="!skill" key="none" class="jb-next__body">
      <h3 class="jb-card__title">All done!</h3>
      <p class="jb-next__hint">Every skill on your roadmap is complete.</p>
    </div>
    <div v-else-if="!selected" :key="`hint-${skill.id}`" class="jb-next__body">
      <h3 class="jb-card__title">{{ skill.name }}</h3>
      <p class="jb-next__hint">Tap a skill to see how to learn it, then mark it done.</p>
    </div>
    <div v-else :key="`sel-${skill.id}-${skill.state}`" class="jb-next__body">
      <h3 class="jb-card__title">{{ skill.name }}</h3>
      <span class="jb-next__kind">{{ skill.kind }}</span>
      <p v-if="skill.blurb" class="jb-next__hint">{{ skill.blurb }}</p>
      <ul v-if="skill.links.length" class="jb-next__res">
        <li v-for="(l, i) in skill.links" :key="l.url" :style="{ '--i': i }">
          <a :href="l.url" target="_blank" rel="noopener noreferrer"><span>{{ l.title }}</span><small>{{ l.kind }}</small></a>
        </li>
      </ul>
      <p v-else class="jb-next__hint">We don’t have a recommended resource for this one yet.</p>
      <div class="jb-next__cta">
        <JbButton v-if="skill.state === 'ready'" :disabled="busy" @click="$emit('complete')">{{ busy ? 'Saving…' : 'Mark as done' }}</JbButton>
        <p v-else-if="skill.state === 'done'" class="jb-next__note"><Icon name="check" :size="18" /> Marked as done</p>
        <p v-else class="jb-next__note"><Icon name="lock" :size="18" /> Finish {{ blockerText }} first.</p>
      </div>
      <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>
    </div>
  </section>
</template>
