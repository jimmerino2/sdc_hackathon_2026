<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Icon from '../Icon.vue';
import type { RoadmapChallenge } from '../../api/roadmap';
import { skillLabel } from '../../data/skills';

/** A challenge's current stage in full: the brief, the stack, the rubric or scorecard, and the repo form. */
const props = defineProps<{ challenge: RoadmapChallenge; busy?: boolean; error?: string | null }>();
const emit = defineEmits<{ submit: [repoUrl: string] }>();

const base = import.meta.env.BASE_URL;
/** The challenge's repo, kept across both stages; the learner may point it at another. */
const url = ref(props.challenge.repo_url ?? props.challenge.history.at(-1)?.repo_url ?? '');
watch(() => props.challenge.repo_url, (u) => { if (u) url.value = u; });

const c = computed(() => props.challenge);
/** The brief's sentences, and its "- " feature lines. */
const lines = computed(() => c.value.description.split('\n').map((l) => l.trim()).filter(Boolean));
const intro = computed(() => lines.value.filter((l) => !l.startsWith('- ')));
const features = computed(() => lines.value.filter((l) => l.startsWith('- ')).map((l) => l.slice(2)));
const results = computed(() => new Map((c.value.result ?? []).map((r) => [r.key, r])));
/** The criterion whose detail is showing; none until the learner picks one. */
const active = ref<string | null>(null);
const activeRubric = computed(() => c.value.rubric.find((r) => r.key === active.value) ?? null);
const activeResult = computed(() => (active.value ? results.value.get(active.value) ?? null : null));
const score = computed(() => (c.value.score == null ? null : Math.round(c.value.score)));
/** Stage 1 passed: no more submissions, Robbee's rewrite is next. A completed stage 2 can still be resubmitted. */
const passed = computed(() => c.value.stage === 1 && (c.value.status === 'passed' || c.value.status === 'advancing'));
const complete = computed(() => c.value.stage === 2 && !!c.value.completed_at);
const repoName = computed(() => c.value.repo_url?.replace('https://github.com/', '') ?? '');
/** Stage 2 opened with the stage 1 repo already filled in. */
const carried = computed(() => c.value.stage === 2 && !c.value.result && !!c.value.repo_url);
const validUrl = computed(() => /^(https?:\/\/)?(www\.)?github\.com\/[\w.-]+\/[\w.-]+/i.test(url.value.trim()));

function submit() {
  if (!validUrl.value || props.busy) return;
  const u = url.value.trim();
  emit('submit', /^https?:\/\//i.test(u) ? u : `https://${u}`);
}
</script>

<template>
  <div class="jb-quest__body">
    <details class="jb-quest__fold" :open="!c.result">
      <summary>Project brief · stage {{ c.stage }} of 2</summary>
      <div class="jb-quest__foldbody">
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
      </div>
    </details>

    <h4 class="jb-quest__h">{{ c.result ? 'Your scorecard' : `How it’s scored · ${c.pass_score}+ to pass` }}</h4>
    <div v-if="c.result && score != null" class="jb-quest__total">
      <span class="jb-quest__big">{{ score }}<small>/100</small></span>
      <p>{{ c.summary }}</p>
    </div>
    <div class="jb-quest__tiles" role="group" aria-label="Scoring criteria">
      <button
        v-for="r in c.rubric"
        :key="r.key"
        type="button"
        class="jb-quest__tile"
        :aria-pressed="active === r.key"
        @click="active = active === r.key ? null : r.key"
      >
        <span class="jb-quest__tname">{{ r.criterion }}</span>
        <span class="jb-quest__tmeta">
          <span v-if="results.get(r.key)" class="jb-quest__pts">{{ results.get(r.key)!.score }}</span>
          <span class="jb-quest__w">{{ r.weight }}%</span>
        </span>
        <span v-if="results.get(r.key)" class="jb-bar" role="img" :aria-label="`${results.get(r.key)!.score} out of 100`">
          <span class="jb-bar__fill" :style="{ width: Math.max(results.get(r.key)!.score, 3) + '%' }" />
        </span>
      </button>
    </div>
    <div v-if="activeRubric" class="jb-quest__detail">
      <p class="jb-quest__desc">{{ activeRubric.description }}</p>
      <template v-if="activeResult">
        <p class="jb-quest__why"><b>Why</b>{{ activeResult.why }}</p>
        <p class="jb-quest__fix"><b>To improve</b>{{ activeResult.improve }}</p>
      </template>
    </div>
    <details v-if="c.files_read.length" class="jb-quest__files">
      <summary>Judged on {{ c.files_read.length }} files from {{ repoName }}</summary>
      <ul><li v-for="f in c.files_read" :key="f"><code>{{ f }}</code></li></ul>
    </details>

    <p v-if="passed" class="jb-next__note"><Icon name="check" :size="18" /> Passed with {{ score }}. Robbee has something to say about that…</p>
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
          {{ busy ? 'Judging…' : c.result ? 'Resubmit' : `Submit stage ${c.stage}` }}
        </button>
      </div>
      <p v-if="busy" class="jb-next__hint">Your bee is reading the repo and scoring it. This can take up to a minute.</p>
      <p v-else-if="carried" class="jb-next__hint">Same repo as stage 1: build Robbee’s changes on top, push, then submit.</p>
      <p v-else-if="complete" class="jb-next__hint">Hive patched. Resubmit to improve your score; this challenge has paid out its stingers.</p>
      <p v-else-if="c.attempts" class="jb-next__hint">Score {{ c.pass_score }}+ to pass. Push your changes and resubmit; only your latest score is kept.</p>
      <p v-else class="jb-next__hint">Score {{ c.pass_score }}+ to pass the stage and land a stinger.</p>
      <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>
    </form>
  </div>
</template>
