<script setup lang="ts">
import { computed } from 'vue';
import { RouterLink } from 'vue-router';
import Icon from '../Icon.vue';
import { go } from '../../router';

export interface IncompleteRoadmap {
  onet_code: string;
  title: string;
  completed: number;
  total: number;
}

const props = defineProps<{
  otherRoadmap?: IncompleteRoadmap | null;
  hasChallenge?: boolean;
  challengeId?: string | null;
}>();

defineEmits<{
  switchRoadmap: [onetCode: string];
}>();

const action = computed(() => {
  if (props.otherRoadmap) {
    return {
      type: 'roadmap' as const,
      icon: 'route',
      eyebrow: 'Your next move',
      title: 'Keep the momentum going',
      desc: `You’re already making progress on ${props.otherRoadmap.title} (${props.otherRoadmap.completed} of ${props.otherRoadmap.total} skills done). Ready to jump back in?`,
      cta: `Continue ${props.otherRoadmap.title}`,
    };
  }
  if (props.hasChallenge && props.challengeId) {
    return {
      type: 'challenge' as const,
      icon: 'trophy',
      eyebrow: 'Your next move',
      title: 'Put your skills to work',
      desc: 'Ready to prove what you’ve learned? Take on a real-world project to build your portfolio and test your skills.',
      cta: 'Take on the challenge',
      to: { name: 'challenges', query: { open: props.challengeId } },
    };
  }
  return {
    type: 'roles' as const,
    icon: 'sparkles',
    eyebrow: 'Your next move',
    title: 'Choose a direction',
    desc: 'You’ve mastered this pathway. Explore more tech roles that match your profile and start your next journey.',
    cta: 'Explore roles',
    to: go('suggested'),
  };
});
</script>

<template>
  <section class="jb jb-card jb-nextmove">
    <div class="jb-card__head">
      <p class="jb-eyebrow">{{ action.eyebrow }}</p>
    </div>

    <h3 class="jb-card__title jb-nextmove__title">{{ action.title }}</h3>
    <p class="jb-nextmove__desc">{{ action.desc }}</p>

    <div class="jb-nextmove__act">
      <button
        v-if="action.type === 'roadmap' && otherRoadmap"
        type="button"
        class="jb-btn jb-btn--primary jb-nextmove__btn"
        @click="$emit('switchRoadmap', otherRoadmap.onet_code)"
      >
        <span>{{ action.cta }}</span>
        <Icon name="arrow" :size="16" />
      </button>

      <RouterLink
        v-else-if="action.type === 'challenge'"
        :to="action.to as any"
        class="jb-btn jb-btn--primary jb-nextmove__btn"
      >
        <span>{{ action.cta }}</span>
        <Icon name="arrow" :size="16" />
      </RouterLink>

      <RouterLink
        v-else
        :to="action.to as any"
        class="jb-btn jb-btn--primary jb-nextmove__btn"
      >
        <span>{{ action.cta }}</span>
        <Icon name="arrow" :size="16" />
      </RouterLink>
    </div>
  </section>
</template>

<style scoped>
.jb-nextmove {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.jb-nextmove__badge {
  display: grid;
  place-items: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--honey-tint);
  color: var(--accent-text);
  flex: none;
}
.jb-nextmove__title {
  margin: 2px 0 0;
  font-size: 23px;
  line-height: 30px;
  font-weight: 900;
}
.jb-nextmove__desc {
  margin: 4px 0 0;
  font-size: 15px;
  line-height: 22px;
  font-weight: 600;
  color: var(--text-muted);
}
.jb-nextmove__act {
  margin-top: 8px;
}
.jb-nextmove__btn {
  width: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
}
</style>
