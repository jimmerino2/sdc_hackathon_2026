<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Icon from '../Icon.vue';
import type { RoadmapChallenge } from '../../api/roadmap';
import { skillLabel } from '../../data/skills';

const props = defineProps<{ challenge: RoadmapChallenge; busy?: boolean; error?: string | null }>();
const emit = defineEmits<{ submit: [repoUrl: string] }>();

const base = import.meta.env.BASE_URL;
const open = ref(false);
const url = ref(props.challenge.repo_url ?? '');
watch(() => props.challenge.repo_url, (u) => { if (u) url.value = u; });

const c = computed(() => props.challenge);
const range = computed(() => {
  const s = c.value.sections;
  return s.length === 1 ? `section ${s[0]}` : `sections ${s[0]}–${s[s.length - 1]}`;
});
/** The brief's sentences, and its "- " feature lines. */
const lines = computed(() => c.value.description.split('\n').map((l) => l.trim()).filter(Boolean));
const intro = computed(() => lines.value.filter((l) => !l.startsWith('- ')));
const features = computed(() => lines.value.filter((l) => l.startsWith('- ')).map((l) => l.slice(2)));
const results = computed(() => new Map((c.value.result ?? []).map((r) => [r.key, r])));
const score = computed(() => (c.value.score == null ? null : Math.round(c.value.score)));
const state = computed(() => (c.value.locked ? 'locked' : score.value != null ? 'scored' : 'open'));
const meta = computed(() => {
  if (c.value.locked) return `Finish ${range.value} to unlock`;
  if (score.value != null) return `Your last score: ${score.value} / 100. Tap to see why.`;
  return 'Build it, push it to GitHub, get scored with tips';
});
const repoName = computed(() => c.value.repo_url?.replace('https://github.com/', '') ?? '');
const validUrl = computed(() => /^(https?:\/\/)?(www\.)?github\.com\/[\w.-]+\/[\w.-]+/i.test(url.value.trim()));

function submit() {
  if (!validUrl.value || props.busy) return;
  const u = url.value.trim();
  emit('submit', /^https?:\/\//i.test(u) ? u : `https://${u}`);
}
</script>

<template>
  <section class="jb jb-quest" :data-state="state">
    <button type="button" class="jb-quest__head" :aria-expanded="open" @click="open = !open">
      <span class="jb-quest__disc"><Icon :name="c.locked ? 'lock' : 'trophy'" :size="24" /></span>
      <span class="jb-quest__label">
        <span class="jb-eyebrow">Bonus quest · optional</span>
        <span class="jb-quest__title">{{ c.title }}</span>
        <span class="jb-quest__meta">{{ meta }}</span>
      </span>
      <span v-if="score != null" class="jb-quest__score" :aria-label="`Score ${score} out of 100`">{{ score }}</span>
      <Icon class="jb-quest__chev" name="arrow" :size="20" />
    </button>

    <div v-if="open" class="jb-quest__body">
      <p v-for="(l, i) in intro" :key="i" class="jb-quest__intro">{{ l }}</p>
      <ul v-if="features.length" class="jb-quest__features">
        <li v-for="(f, i) in features" :key="i">{{ f }}</li>
      </ul>

      <div class="jb-quest__sdg">
        <img :src="`${base}sdg/goal-${String(c.sdg).padStart(2, '0')}.jpg`" :alt="`UN Sustainable Development Goal ${c.sdg}: ${c.sdg_name}`" width="56" height="56" loading="lazy" />
        <p>
          <b>Goal {{ c.sdg }}: {{ c.sdg_name }}</b>
          <span v-if="c.interests.length">Picked for your interest in {{ c.interests.join(' and ') }}.</span>
        </p>
      </div>

      <h4 class="jb-quest__h">Build it with</h4>
      <dl class="jb-quest__stack">
        <div v-for="a in c.tech_stack" :key="a.area">
          <dt>{{ a.area }}</dt>
          <dd><span v-for="s in a.skills" :key="s" class="jb-quest__chip">{{ skillLabel(s) }}</span></dd>
        </div>
      </dl>

      <h4 class="jb-quest__h">{{ c.result ? 'Your scorecard' : 'How it’s scored' }}</h4>
      <div v-if="c.result && score != null" class="jb-quest__total">
        <span class="jb-quest__big">{{ score }}<small>/100</small></span>
        <p>{{ c.summary }}</p>
      </div>
      <ol class="jb-quest__rubric">
        <li v-for="r in c.rubric" :key="r.key">
          <div class="jb-quest__crit">
            <b>{{ r.criterion }}</b>
            <span class="jb-quest__w">{{ r.weight }}% of score</span>
            <span v-if="results.get(r.key)" class="jb-quest__pts">{{ results.get(r.key)!.score }}/100</span>
          </div>
          <div v-if="results.get(r.key)" class="jb-bar" role="img" :aria-label="`${results.get(r.key)!.score} out of 100`">
            <div class="jb-bar__fill" :style="{ width: Math.max(results.get(r.key)!.score, 3) + '%' }" />
          </div>
          <p class="jb-quest__desc">{{ r.description }}</p>
          <template v-if="results.get(r.key)">
            <p class="jb-quest__why"><b>Why</b>{{ results.get(r.key)!.why }}</p>
            <p class="jb-quest__fix"><b>To improve</b>{{ results.get(r.key)!.improve }}</p>
          </template>
        </li>
      </ol>
      <details v-if="c.files_read.length" class="jb-quest__files">
        <summary>Judged on {{ c.files_read.length }} files from {{ repoName }}</summary>
        <ul><li v-for="f in c.files_read" :key="f"><code>{{ f }}</code></li></ul>
      </details>

      <p v-if="c.locked" class="jb-next__note"><Icon name="lock" :size="18" /> Finish every skill in {{ range }} to submit your project.</p>
      <form v-else class="jb-quest__form" @submit.prevent="submit">
        <label class="jb-quest__lbl" :for="`quest-${c.challenge_id}`">Your public GitHub repo</label>
        <div class="jb-quest__row">
          <input
            :id="`quest-${c.challenge_id}`"
            v-model="url"
            type="url"
            inputmode="url"
            autocomplete="url"
            spellcheck="false"
            placeholder="https://github.com/you/your-project"
            :disabled="busy"
          />
          <button type="submit" class="jb-btn jb-btn--primary" :disabled="!validUrl || busy">
            {{ busy ? 'Judging…' : c.result ? 'Resubmit' : 'Submit' }}
          </button>
        </div>
        <p v-if="busy" class="jb-next__hint">Your bee is reading the repo and scoring it. This can take up to a minute.</p>
        <p v-else-if="c.attempts" class="jb-next__hint">Improved it? Push your changes and resubmit. Only your latest score is kept.</p>
        <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>
      </form>
    </div>
  </section>
</template>
