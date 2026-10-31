<script setup lang="ts">
import { computed, onMounted, ref } from 'vue';
import SdgTip from '../SdgTip.vue';
import { fetchSkillSdgs, type SkillSdg } from '../../api/sdg';
import { SDG_GOALS } from '../../data/interestSdgs';
import Icon from '../Icon.vue';
import JbButton from './JbButton.vue';
import HrdCard from './HrdCard.vue';
import { splitByCost } from '../../learn/cost';
import type { Programme } from '../../api/hrd';

export interface NextUpSkill {
  id: string;
  name: string;
  /** The O*NET skill name, which the HRD Corp courses are matched by. */
  skillName: string;
  state: 'ready' | 'done' | 'locked';
  kind: string;
  blurb: string | null;
  blockers: string[];
  links: { title: string; url: string; kind: string }[];
  /** How long it takes, and where that figure comes from. */
  time?: { text: string; note: string } | null;
  /** A section's AI study guide: its blurb is what the AI wrote, with these steps under it, and there are no courses to offer. */
  ai?: boolean;
  steps?: string[];
}

const props = defineProps<{
  skill: NextUpSkill | null;
  selected: boolean;
  /** The skill's HRD Corp courses; null while loading. */
  programmes?: Programme[] | null;
  busy?: boolean;
  error?: string | null;
  eyebrow?: string;
  closable?: boolean;
}>();

defineEmits<{
  complete: [];
  close: [];
}>();

/** The goals the selected skill serves (main first), each with its targets, for the hoverable SDG chips. */
const skillSdgs = ref<Map<string, SkillSdg>>(new Map());
onMounted(async () => (skillSdgs.value = await fetchSkillSdgs()));
const goals = computed(() => {
  const s = skillSdgs.value.get(props.skill?.skillName ?? '');
  if (!s) return [];
  return [s.main, ...s.relevant].map((g) => ({
    sdg: g.sdg,
    title: `SDG ${g.sdg} · ${SDG_GOALS[g.sdg]?.title ?? g.name}`,
    color: SDG_GOALS[g.sdg]?.color ?? 'var(--ink)',
    targets: s.targets.filter((t) => t.sdg === g.sdg),
  }));
});

/** The links split into those that are free and those on sites that sell courses, so "Free" is never claimed for a paid course. */
const groups = computed(() => splitByCost(props.skill?.links ?? []));
const blockerText = computed(() => props.skill?.blockers.join(' and ') || 'the earlier skills');
const collapsed = ref(false);
/** Each group of links folds away on its own; both start open. */
const freeOpen = ref(true);
const costOpen = ref(true);

const eyebrowText = computed(() => {
  if (props.eyebrow) return props.eyebrow;
  if (props.skill?.state === 'done') return 'Skill materials';
  return 'Next up';
});
</script>

<template>
  <section class="jb jb-card jb-next">
    <div class="jb-card__head">
      <p class="jb-eyebrow">{{ eyebrowText }}</p>
      <div class="jb-card__head-actions">
        <button v-if="closable" type="button" class="jb-collapse" aria-label="Close skill materials" @click="$emit('close')">
          <Icon name="x" :size="16" />
        </button>
        <button v-if="skill" type="button" class="jb-collapse" :aria-expanded="!collapsed" aria-label="Toggle sources" @click="collapsed = !collapsed">
          <Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': !collapsed }" />
        </button>
      </div>
    </div>
    <div v-if="!skill" key="none" class="jb-next__body">
      <h3 class="jb-card__title">All done!</h3>
      <p class="jb-next__hint">Every skill on your roadmap is complete.</p>
    </div>
    <template v-else>
      <h3 class="jb-card__title">{{ skill.name }}</h3>
      <div v-show="!collapsed">
        <div v-if="!selected" :key="`hint-${skill.id}`" class="jb-next__body">
          <p class="jb-next__hint">Tap a skill to see how to learn it, then mark it done.</p>
        </div>
        <div v-else :key="`sel-${skill.id}-${skill.state}`" class="jb-next__body">
          <span class="jb-next__kind" :class="{ 'jb-next__ai': skill.ai }">{{ skill.kind }}</span>
          <p v-if="skill.time" class="jb-next__hint"><b>About {{ skill.time.text }}</b> · {{ skill.time.note }}</p>
          <p v-if="goals.length" class="jb-next__sdgs" aria-label="Sustainable Development Goals this skill serves">
            <SdgTip v-for="g in goals" :key="g.sdg" :title="g.title" :targets="g.targets" :pill="g.color">SDG {{ g.sdg }}</SdgTip>
          </p>
          <p v-else-if="skill.blurb" class="jb-next__hint">{{ skill.blurb }}</p>
          <ol v-if="skill.steps?.length" class="jb-next__steps"><li v-for="step in skill.steps" :key="step">{{ step }}</li></ol>
          <template v-if="skill.links.length">
            <section v-if="groups.free.length" class="jb-res jb-res--free" aria-label="Free resources">
              <button type="button" class="jb-res__head" :aria-expanded="freeOpen" aria-controls="res-free" @click="freeOpen = !freeOpen">
                <span class="jb-res__seal" aria-hidden="true"><Icon name="gift" :size="16" :stroke="2.6" /></span>
                <span class="jb-res__titles">
                  <span class="jb-res__eyebrow">Free</span>
                  <span class="jb-res__title">Free resources</span>
                </span>
                <span class="jb-res__count">{{ groups.free.length }}</span>
                <span class="jb-res__chev" aria-hidden="true"><Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': freeOpen }" /></span>
              </button>
              <div v-show="freeOpen" id="res-free" class="jb-res__body">
                <ul class="jb-next__res">
                  <li v-for="(l, i) in groups.free" :key="l.url" :style="{ '--i': i }">
                    <a :href="l.url" target="_blank" rel="noopener noreferrer"><span>{{ l.title }}</span><small>{{ l.kind }}</small></a>
                  </li>
                </ul>
              </div>
            </section>
            <section v-if="groups.mayCost.length" class="jb-res jb-res--cost" aria-label="Courses that may cost">
              <button type="button" class="jb-res__head" :aria-expanded="costOpen" aria-controls="res-cost" @click="costOpen = !costOpen">
                <span class="jb-res__seal" aria-hidden="true"><Icon name="coins" :size="16" :stroke="2.6" /></span>
                <span class="jb-res__titles">
                  <span class="jb-res__eyebrow">May cost</span>
                  <span class="jb-res__title">Courses and credentials</span>
                </span>
                <span class="jb-res__count">{{ groups.mayCost.length }}</span>
                <span class="jb-res__chev" aria-hidden="true"><Icon name="chevron" :size="16" :class="{ 'jb-collapse__icon--up': costOpen }" /></span>
              </button>
              <div v-show="costOpen" id="res-cost" class="jb-res__body">
                <p class="jb-res__note">Some are free to preview. The full course or the certificate can cost.</p>
                <ul class="jb-next__res">
                  <li v-for="(l, i) in groups.mayCost" :key="l.url" :style="{ '--i': i }">
                    <a :href="l.url" target="_blank" rel="noopener noreferrer"><span>{{ l.title }}</span><small>{{ l.kind }}</small></a>
                  </li>
                </ul>
              </div>
            </section>
          </template>
          <p v-else-if="!skill.ai" class="jb-next__hint">We don’t have a recommended resource for this one yet.</p>
          <HrdCard v-if="programmes && !skill.ai" :programmes="programmes" />
          <div class="jb-next__cta">
            <JbButton v-if="skill.state === 'ready'" :disabled="busy" @click="$emit('complete')">{{ busy ? 'Saving…' : 'Mark as done' }}</JbButton>
            <p v-else-if="skill.state === 'done'" class="jb-next__note"><Icon name="check" :size="18" /> Marked as done</p>
            <p v-else class="jb-next__note"><Icon name="lock" :size="18" /> Finish {{ blockerText }} first.</p>
          </div>
          <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>
        </div>
      </div>
    </template>
  </section>
</template>
