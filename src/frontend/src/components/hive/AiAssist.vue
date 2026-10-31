<script setup lang="ts">
import { computed, ref } from 'vue';
import Icon from '../Icon.vue';
import CopyPrompt from '../learn/CopyPrompt.vue';
import type { RoadmapChallenge } from '../../api/roadmap';
import { ASSIST_CHECKLIST, guidanceFor, REFLECTION_QUESTIONS, tipsFor } from '../../data/aiAssist';
import { lessonById } from '../../data/aiFluency';
import { reflectionFor, saveReflection } from '../../learn/aiProgress';

/** Optional help for working with AI on a challenge. Closed until asked for, and it has no effect on scoring or stingers. */
const props = defineProps<{ challenge: RoadmapChallenge }>();

const tips = computed(() => tipsFor(props.challenge));
const guidance = computed(() => guidanceFor(props.challenge.onet_code));
const complete = computed(() => props.challenge.stage === 2 && !!props.challenge.completed_at);
const openTip = ref<string | null>(null);

const lessonLink = (id: string) => ({ name: 'pathway', query: { section: 'ai-fluency', lesson: id } });
const lessonTitle = (id: string) => lessonById(id)?.title ?? 'AI Fluency';
const answer = (key: (typeof REFLECTION_QUESTIONS)[number]['key']) => reflectionFor(props.challenge.challenge_id)[key] ?? '';
function save(key: (typeof REFLECTION_QUESTIONS)[number]['key'], e: Event) {
  saveReflection(props.challenge.challenge_id, { [key]: (e.target as HTMLTextAreaElement).value });
}
</script>

<template>
  <details class="jb-quest__fold aiast">
    <summary><Icon name="sparkles" :size="16" />AI Assist · optional</summary>
    <div class="jb-quest__foldbody">
      <p class="aiast__intro">Tips and prompts for using AI tools on this project. Whether you use them is up to you: it isn’t scored, and you lose nothing by skipping this.</p>
      <p v-if="guidance" class="aiast__role"><b>Useful for {{ guidance.title }}:</b> {{ guidance.skills.join(', ') }}.</p>

      <ul class="aiast__tips">
        <li v-for="t in tips" :key="t.id" class="aiast__tip">
          <button type="button" class="aiast__tiphead" :aria-expanded="openTip === t.id" @click="openTip = openTip === t.id ? null : t.id">
            <span class="aiast__icon"><Icon :name="t.icon" :size="18" /></span>
            <span class="aiast__tiptext"><small>{{ t.kind }}</small>{{ t.title }}</span>
            <Icon name="chevron" :size="20" class="aiast__caret" :class="{ open: openTip === t.id }" />
          </button>
          <div v-if="openTip === t.id" class="aiast__tipbody">
            <p>{{ t.advice }}</p>
            <CopyPrompt :text="t.prompt" :label="`${t.kind} prompt`" />
            <p class="aiast__why"><b>Why this prompt works:</b> {{ t.why }}</p>
            <RouterLink :to="lessonLink(t.lessonId)" class="aiast__link">Learn more: {{ lessonTitle(t.lessonId) }}</RouterLink>
          </div>
        </li>
      </ul>

      <h4 class="jb-quest__h">Before you trust the result</h4>
      <ul class="aiast__checks">
        <li v-for="item in ASSIST_CHECKLIST" :key="item"><Icon name="check" :size="16" />{{ item }}</li>
      </ul>

      <template v-if="complete">
        <h4 class="jb-quest__h">Reflect on how you worked · optional</h4>
        <p class="aiast__intro">Only for you. This stays in this browser, and it isn’t judged or scored.</p>
        <label v-for="q in REFLECTION_QUESTIONS" :key="q.key" class="aiast__q">
          <span>{{ q.label }}</span>
          <textarea rows="2" :value="answer(q.key)" @input="save(q.key, $event)" />
        </label>
      </template>
    </div>
  </details>
</template>

<style scoped>
.aiast { padding-top: 12px; border-top: 2px solid var(--line); }
.aiast > summary svg { flex: none; }
.aiast p { margin: 0; }
.aiast__intro { font-size: 15px; line-height: 22px; font-weight: 600; color: var(--text-muted); }
.aiast__role { font-size: 15px; line-height: 22px; font-weight: 600; }
.aiast__tips, .aiast__checks { display: flex; flex-direction: column; margin: 0; padding: 0; list-style: none; }
.aiast__tips { gap: 8px; }
.aiast__tip { border: 2px solid var(--line); border-radius: var(--radius-md); background: var(--surface-raised); overflow: hidden; }
.aiast__tiphead { display: flex; align-items: center; gap: 12px; width: 100%; min-height: 44px; padding: 10px 14px; border: 0; background: none; color: var(--text); text-align: left; cursor: pointer; }
.aiast__tiphead:hover { background: var(--surface); }
.jb .aiast__tiphead:focus-visible { outline-offset: -3px; }
.aiast__icon { flex: none; display: grid; place-items: center; width: 32px; height: 32px; border-radius: 50%; background: var(--honey-tint); color: var(--accent-text); }
.aiast__tiptext { flex: 1; min-width: 0; display: flex; flex-direction: column; font-size: 16px; line-height: 22px; font-weight: 800; }
.aiast__tiptext small { font-size: 13px; line-height: 17px; font-weight: 800; color: var(--text-muted); }
.aiast__caret { flex: none; color: var(--text-muted); transition: transform var(--dur-base) var(--ease-out); }
.aiast__caret.open { transform: rotate(180deg); }
.aiast__tipbody { display: flex; flex-direction: column; gap: 10px; padding: 4px 14px 14px; font-size: 15px; line-height: 22px; font-weight: 600; }
.aiast__why { color: var(--text-muted); }
.aiast__why b { color: var(--text); }
.aiast__link { align-self: flex-start; font-weight: 800; color: var(--accent-text); text-decoration: underline; }
.aiast__checks { gap: 4px; }
.aiast__checks li { display: flex; align-items: flex-start; gap: 8px; font-size: 15px; line-height: 22px; font-weight: 600; }
.aiast__checks svg { flex: none; margin-top: 3px; color: #2e7d4f; }
.aiast__q { display: flex; flex-direction: column; gap: 4px; font-size: 15px; line-height: 21px; font-weight: 800; }
.aiast__q textarea { width: 100%; padding: 8px 12px; border: 2px solid var(--line-strong); border-radius: var(--radius-sm); background: var(--surface-raised); color: var(--text); font: inherit; font-size: 16px; font-weight: 600; resize: vertical; }
.aiast__q textarea:focus-visible { outline: 3px solid var(--focus); outline-offset: 1px; }
</style>
