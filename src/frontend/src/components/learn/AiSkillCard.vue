<script setup lang="ts">
import { ref } from 'vue';
import Icon from '../Icon.vue';

/** Shown in place of the demand forecast when a section's AI study guide is selected: why the step is there and why it comes first. */
defineProps<{ name: string }>();
const collapsed = ref(false);
</script>

<template>
  <section class="jb jb-card jb-aiskill">
    <div class="jb-card__head">
      <p class="jb-eyebrow">AI skill (high priority)</p>
      <button type="button" class="jb-collapse" :aria-expanded="!collapsed" aria-label="Toggle AI skill" @click="collapsed = !collapsed">
        <Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': !collapsed }" />
      </button>
    </div>
    <h3 class="jb-card__title">{{ name }}</h3>
    <span class="jb-aiskill__badge"><Icon name="sparkles" :size="14" :stroke="2.6" /> Do this first</span>
    <div v-show="!collapsed" class="jb-next__body">
      <p class="jb-aiskill__text">This skill was recommended by Jobee, as it teaches you how to properly use AI to simplify the learning process for the skills in this section.</p>
    </div>
  </section>
</template>
