<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import { useRoute } from 'vue-router';
import Bubble from '../Bubble.vue';
import Icon from '../Icon.vue';
import AiLesson from './AiLesson.vue';
import { AI_LESSONS, AI_ROLE_CODES, isAiRole, lessonById, ROLE_AI_GUIDANCE, type AiRoleCode } from '../../data/aiFluency';
import { completedLessons, toggleLesson } from '../../learn/aiProgress';

/** The Learn page's optional AI Fluency section: lesson cards, or one lesson when the address names it. */
const props = defineProps<{ profileId: string | null; roleCode?: string | null }>();
const route = useRoute();

const lesson = computed(() => lessonById(typeof route.query.lesson === 'string' ? route.query.lesson : null));
const position = computed(() => (lesson.value ? AI_LESSONS.indexOf(lesson.value) + 1 : 0));

const done = computed(() => completedLessons(props.profileId));
const doneCount = computed(() => AI_LESSONS.filter((l) => done.value.includes(l.id)).length);
const pct = computed(() => Math.round((doneCount.value / AI_LESSONS.length) * 100));
/** The first lesson not finished yet, which the cards point the learner to. */
const upNext = computed(() => AI_LESSONS.find((l) => !done.value.includes(l.id))?.id ?? null);

/** The role whose guidance shows: the roadmap's, until the learner picks another. */
const role = ref<AiRoleCode | null>(null);
watch(() => props.roleCode, (code) => { role.value = isAiRole(code) ? code : role.value; }, { immediate: true });
const guidance = computed(() => (role.value ? ROLE_AI_GUIDANCE[role.value] : null));
const linkTo = (id: string) => ({ name: 'pathway', query: { section: 'ai-fluency', lesson: id } });
</script>

<template>
  <div class="jb aifl">
    <AiLesson
      v-if="lesson"
      :key="lesson.id"
      :lesson="lesson"
      :position="position"
      :total="AI_LESSONS.length"
      :done="done.includes(lesson.id)"
      @toggle="toggleLesson(profileId, lesson!.id)"
    />

    <template v-else>
      <header class="aifl__head">
        <div>
          <p class="jb-eyebrow">Optional · alongside your roadmap</p>
          <h1>AI Fluency</h1>
          <p class="aifl__sub">Five short lessons on using AI tools well at work. They build on your technical skills and don’t change your roadmap.</p>
        </div>
        <Bubble :size="64" mood="happy">
          {{ doneCount === AI_LESSONS.length ? 'All five done. Nice work!' : doneCount ? `${doneCount} done, ${AI_LESSONS.length - doneCount} to go.` : 'Pick any lesson. The order is only a suggestion!' }}
        </Bubble>
      </header>

      <div class="aifl__progress">
        <div class="progress" role="progressbar" aria-label="AI Fluency lessons completed" aria-valuemin="0" :aria-valuemax="AI_LESSONS.length" :aria-valuenow="doneCount">
          <i :style="{ width: pct + '%' }" />
        </div>
        <span>{{ doneCount }} of {{ AI_LESSONS.length }} lessons</span>
      </div>

      <ol class="aifl__list">
        <li v-for="(l, i) in AI_LESSONS" :key="l.id">
          <RouterLink :to="linkTo(l.id)" class="aifl__card" :class="{ 'is-next': l.id === upNext }">
            <span class="aifl__num" :class="{ 'is-done': done.includes(l.id) }">
              <Icon v-if="done.includes(l.id)" name="check" :size="18" /><template v-else>{{ i + 1 }}</template>
              <span class="sr-only">{{ done.includes(l.id) ? 'Completed' : '' }}</span>
            </span>
            <span class="aifl__body">
              <span class="aifl__title">{{ l.title }}</span>
              <span class="aifl__desc">{{ l.summary }}</span>
              <span class="aifl__meta">
                <span>{{ l.difficulty }}</span><span>{{ l.minutes }} min</span>
                <span v-if="guidance?.lessons.includes(l.id)" class="aifl__tag">Suggested for {{ guidance.title }}</span>
                <span v-if="l.id === upNext" class="aifl__tag aifl__tag--next">Up next</span>
              </span>
            </span>
          </RouterLink>
        </li>
      </ol>

      <section class="aifl__roles" aria-labelledby="aifl-roles">
        <h2 id="aifl-roles">AI skills by role</h2>
        <div class="aifl__chips" role="group" aria-label="Choose a role">
          <button v-for="code in AI_ROLE_CODES" :key="code" type="button" class="aifl__chip" :class="{ on: role === code }" :aria-pressed="role === code" @click="role = code">
            {{ ROLE_AI_GUIDANCE[code].title }}
          </button>
        </div>
        <div v-if="guidance" class="aifl__guide">
          <ul><li v-for="s in guidance.skills" :key="s">{{ s }}</li></ul>
          <p><b>Try this:</b> {{ guidance.useCase }}</p>
          <p class="aifl__fine">Static suggestions to help you learn. They have no effect on your role match scores.</p>
        </div>
        <p v-else class="aifl__fine">Pick a role to see which AI skills matter most for it.</p>
      </section>
    </template>
  </div>
</template>

<style scoped>
.aifl { display: flex; flex-direction: column; gap: 22px; max-width: 980px; }
.aifl__head { display: flex; flex-wrap: wrap; align-items: flex-end; justify-content: space-between; gap: 16px; }
.aifl__head > div:first-child { flex: 1 1 380px; min-width: 0; }
.aifl__head .jb-eyebrow { color: var(--accent-text); }
h1 { margin: 2px 0 4px; font-size: 34px; line-height: 41px; font-weight: 900; }
h2 { margin: 0; font-size: 23px; line-height: 30px; font-weight: 900; }
.aifl__sub { margin: 0; font-size: 16px; line-height: 23px; font-weight: 600; color: var(--text-muted); }
.aifl__progress { display: flex; align-items: center; gap: 14px; }
.aifl__progress .progress { flex: 1; max-width: 420px; }
.aifl__progress > span { font-size: 15px; font-weight: 800; color: var(--text-muted); white-space: nowrap; }
.aifl__list { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 14px; margin: 0; padding: 0; list-style: none; }
.aifl__list li { display: flex; min-width: 0; }
.aifl__card { display: flex; flex: 1; min-width: 0; gap: 14px; padding: 16px 18px; border: 2px solid var(--line); border-radius: var(--radius-lg); background: var(--surface-raised); color: var(--text); transition: transform var(--dur-fast) var(--ease-bounce), border-color var(--dur-fast); }
.aifl__card:hover { transform: translateY(-2px); border-color: var(--line-strong); }
.aifl__card.is-next { border-color: var(--honey); }
.aifl__num { flex: none; display: grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; background: var(--honey-tint); color: var(--text); font-size: 16px; font-weight: 900; }
.aifl__num.is-done { background: #2e7d4f; color: #fff; }
.aifl__body { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.aifl__title { font-size: 19px; line-height: 25px; font-weight: 900; }
.aifl__desc { font-size: 15px; line-height: 21px; font-weight: 600; color: var(--text-muted); }
.aifl__meta { display: flex; flex-wrap: wrap; align-items: center; gap: 4px 10px; margin-top: 4px; font-size: 14px; line-height: 20px; font-weight: 800; color: var(--text-muted); }
.aifl__tag { padding: 1px 9px; border-radius: var(--radius-pill); background: var(--honey-tint); color: var(--accent-text); }
.aifl__tag--next { background: var(--honey); color: var(--on-honey); }
.aifl__roles { display: flex; flex-direction: column; gap: 12px; padding: 18px 22px; border: 2px solid var(--line); border-radius: var(--radius-lg); background: var(--surface-raised); }
.aifl__chips { display: flex; flex-wrap: wrap; gap: 8px; }
.aifl__chip { min-height: 38px; padding: 6px 14px; border: 2px solid var(--line-strong); border-radius: var(--radius-pill); background: var(--surface-raised); color: var(--text-muted); font-size: 15px; font-weight: 800; cursor: pointer; transition: background var(--dur-fast); }
.aifl__chip:hover { background: var(--surface); }
.aifl__chip.on { border-color: var(--honey); background: var(--honey-tint); color: var(--text); }
.aifl__guide { display: flex; flex-direction: column; gap: 8px; }
.aifl__guide ul { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 4px 24px; margin: 0; padding-left: 20px; }
.aifl__guide li, .aifl__guide p { margin: 0; font-size: 16px; line-height: 23px; font-weight: 600; }
.aifl__guide .aifl__fine, .aifl__fine { margin: 0; font-size: 14px; line-height: 20px; font-weight: 600; color: var(--text-muted); }
@media (max-width: 760px) {
  h1 { font-size: 28px; line-height: 35px; }
  .aifl__list, .aifl__guide ul { grid-template-columns: minmax(0, 1fr); }
  .aifl__roles { padding: 14px 16px; }
}
</style>
