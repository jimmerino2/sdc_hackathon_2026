<script setup lang="ts">
import { computed } from 'vue';
import Icon from '../Icon.vue';
import CopyPrompt from './CopyPrompt.vue';
import { nextLesson, type AiLesson } from '../../data/aiFluency';

/** One AI Fluency lesson in full, in the order concept, why, demonstration, application, verification, further reading. */
const props = defineProps<{ lesson: AiLesson; position: number; total: number; done: boolean }>();
const emit = defineEmits<{ toggle: [] }>();

const next = computed(() => nextLesson(props.lesson.id));
const linkTo = (lesson: string) => ({ name: 'pathway', query: { section: 'ai-fluency', lesson } });
</script>

<template>
  <article class="ailes">
    <RouterLink :to="{ name: 'pathway', query: { section: 'ai-fluency' } }" class="ailes__back">
      <Icon name="chevron" :size="18" /> All lessons
    </RouterLink>

    <header class="ailes__head">
      <p class="jb-eyebrow">Lesson {{ position }} of {{ total }} · {{ lesson.category }}</p>
      <h1>{{ lesson.title }}</h1>
      <p class="ailes__summary">{{ lesson.summary }}</p>
      <p class="ailes__meta">{{ lesson.difficulty }} · about {{ lesson.minutes }} min</p>
    </header>

    <section class="ailes__card">
      <h2>What you’ll be able to do</h2>
      <ul><li v-for="o in lesson.objectives" :key="o">{{ o }}</li></ul>
    </section>

    <section class="ailes__sec">
      <h2>Why it matters</h2>
      <p v-for="p in lesson.why" :key="p">{{ p }}</p>
    </section>

    <section v-for="s in lesson.sections" :key="s.heading" class="ailes__sec">
      <h2>{{ s.heading }}</h2>
      <p v-for="p in s.body ?? []" :key="p">{{ p }}</p>
      <ul v-if="s.bullets"><li v-for="b in s.bullets" :key="b">{{ b }}</li></ul>
      <ol v-if="s.steps" class="ailes__steps">
        <li v-for="st in s.steps" :key="st.name"><b>{{ st.name }}</b><span>{{ st.detail }}</span></li>
      </ol>
      <p v-if="s.note" class="ailes__note">{{ s.note }}</p>
    </section>

    <section class="ailes__sec">
      <h2>See it in practice</h2>
      <div v-for="e in lesson.examples" :key="e.title" class="ailes__card ailes__example">
        <h3>{{ e.title }}</h3>
        <p v-if="e.context">{{ e.context }}</p>
        <div class="ailes__compare" :class="{ 'ailes__compare--two': e.before }">
          <CopyPrompt v-if="e.before" :text="e.before" :label="e.beforeLabel ?? 'Weak prompt'" />
          <CopyPrompt :text="e.after" :label="e.afterLabel ?? 'Stronger prompt'" />
        </div>
        <p class="ailes__why"><b>What to notice</b>{{ e.why }}</p>
      </div>
    </section>

    <section class="ailes__sec">
      <h2>Prompt templates</h2>
      <div v-for="t in lesson.templates" :key="t.title" class="ailes__template">
        <CopyPrompt :text="t.prompt" :label="t.title" />
        <p class="ailes__why"><b>Why it works</b>{{ t.why }}</p>
      </div>
    </section>

    <section class="ailes__card ailes__try">
      <h2>Try it yourself</h2>
      <p>{{ lesson.exercise.task }}</p>
      <ol><li v-for="st in lesson.exercise.steps" :key="st">{{ st }}</li></ol>
      <p><b>You’re done when:</b> {{ lesson.exercise.doneWhen }}</p>
    </section>

    <section class="ailes__sec">
      <h2>Check your result</h2>
      <ul class="ailes__checks">
        <li v-for="c in lesson.checklist" :key="c"><Icon name="check" :size="18" />{{ c }}</li>
      </ul>
    </section>

    <section class="ailes__sec">
      <h2>Further reading</h2>
      <ul class="ailes__links">
        <li v-for="r in lesson.reading" :key="r.url">
          <a :href="r.url" target="_blank" rel="noopener noreferrer">{{ r.label }} <Icon name="external" :size="14" /></a>
          <span>{{ r.licence ? `${r.note} ${r.licence}` : r.note }}</span>
        </li>
      </ul>
      <p class="ailes__note">Tools and documentation change. Treat these as references, and check what still applies to the tools you use.</p>
    </section>

    <footer class="ailes__foot">
      <button type="button" class="jb-btn" :class="done ? 'jb-btn--quiet' : 'jb-btn--primary'" :aria-pressed="done" @click="emit('toggle')">
        <Icon v-if="done" name="check" :size="18" />{{ done ? 'Completed' : 'Mark as complete' }}
      </button>
      <RouterLink v-if="next" :to="linkTo(next.id)" class="jb-btn jb-btn--quiet">Next: {{ next.title }}</RouterLink>
      <RouterLink v-else :to="{ name: 'pathway', query: { section: 'ai-fluency' } }" class="jb-btn jb-btn--quiet">All lessons</RouterLink>
    </footer>
  </article>
</template>

<style scoped>
.ailes { display: flex; flex-direction: column; gap: 24px; max-width: 820px; }
.ailes__back { display: inline-flex; align-items: center; gap: 4px; align-self: flex-start; font-size: 15px; font-weight: 800; color: var(--accent-text); }
.ailes__back svg { transform: rotate(90deg); }
.ailes__head { display: flex; flex-direction: column; gap: 6px; }
.ailes__head .jb-eyebrow { color: var(--accent-text); }
h1 { margin: 0; font-size: 34px; line-height: 41px; font-weight: 900; overflow-wrap: anywhere; }
h2 { margin: 0; font-size: 23px; line-height: 30px; font-weight: 900; }
h3 { margin: 0; font-size: 18px; line-height: 25px; font-weight: 900; }
p, li { margin: 0; font-size: 16px; line-height: 24px; font-weight: 600; }
ul, ol { margin: 0; padding-left: 22px; display: flex; flex-direction: column; gap: 6px; }
.ailes__summary { font-size: 18px; line-height: 26px; color: var(--text-muted); }
.ailes__meta { font-size: 15px; font-weight: 800; color: var(--text-muted); }
.ailes__sec { display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.ailes__card { display: flex; flex-direction: column; gap: 10px; min-width: 0; padding: 18px 22px; border: 2px solid var(--line); border-radius: var(--radius-lg); background: var(--surface-raised); }
.ailes__try { border-color: var(--honey); background: var(--honey-tint); }
.ailes__steps { list-style: none; padding: 0; counter-reset: step; gap: 8px; }
.ailes__steps li { counter-increment: step; position: relative; display: flex; flex-direction: column; padding-left: 40px; min-height: 30px; }
.ailes__steps li::before { content: counter(step); position: absolute; left: 0; top: 0; display: grid; place-items: center; width: 30px; height: 30px; border-radius: 50%; background: var(--honey); color: var(--on-honey); font-size: 15px; font-weight: 900; }
.ailes__steps b { font-weight: 900; }
.ailes__steps span { color: var(--text-muted); }
.ailes__note { padding: 10px 14px; border-left: 4px solid var(--honey); border-radius: 0 var(--radius-sm) var(--radius-sm) 0; background: var(--surface); font-size: 15px; line-height: 22px; color: var(--text-muted); }
.ailes__compare { display: grid; grid-template-columns: minmax(0, 1fr); gap: 12px; }
.ailes__compare--two { grid-template-columns: minmax(0, 2fr) minmax(0, 3fr); align-items: start; }
.ailes__why { font-size: 15px; line-height: 22px; color: var(--text-muted); }
.ailes__why b { display: block; color: var(--text); font-weight: 900; }
.ailes__template { display: flex; flex-direction: column; gap: 8px; }
.ailes__template + .ailes__template { margin-top: 8px; }
.ailes__checks { list-style: none; padding: 0; }
.ailes__checks li { display: flex; align-items: flex-start; gap: 8px; }
.ailes__checks svg { flex: none; margin-top: 3px; color: #2e7d4f; }
.ailes__links { list-style: none; padding: 0; gap: 10px; }
.ailes__links li { display: flex; flex-direction: column; }
.ailes__links a { display: inline-flex; align-items: center; gap: 5px; align-self: flex-start; font-weight: 800; color: var(--accent-text); text-decoration: underline; }
.ailes__links span { font-size: 15px; line-height: 22px; color: var(--text-muted); }
.ailes__foot { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; padding-top: 8px; }
.ailes__foot .jb-btn { max-width: 100%; text-transform: none; letter-spacing: 0; }
@media (max-width: 760px) {
  h1 { font-size: 28px; line-height: 35px; }
  .ailes__card { padding: 14px 16px; }
  .ailes__compare--two { grid-template-columns: minmax(0, 1fr); }
}
</style>
