<script lang="ts">
import { shallowRef } from 'vue';
import type { ResumePreview } from '../api/readResumePdf';

/** The resume's preview. Kept outside the component so it survives a trip to the skill check and back. */
const doc = shallowRef<ResumePreview | null>(null);
</script>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Icon from '../components/Icon.vue';
import PollenGame from '../components/PollenGame.vue';
import ResumeDoc from '../components/ResumeDoc.vue';
import ResumeProgress from '../components/ResumeProgress.vue';
import ResumeResults, { type SkillRow } from '../components/ResumeResults.vue';
import { checkResumeFile, extractResume, ResumeUploadError, type ResumeEvent } from '../api/resume';
import { readResumePdf } from '../api/readResumePdf';
import { EXPECTED_MS, SCAN_END, useAnalysisClock } from '../composables/useAnalysisClock';
import { displayName, limitInferred } from '../data/resumeKeywords';
import { useFlow } from '../state';
import { personaCopy } from '../data/personaCopy';
import { go } from '../router';

const STAGE_LINES = ['Give me a sec, I’m reading it…', 'Picking out the skills worth checking…', 'Matching them against your resume…', 'Last step: ranking your strongest.'];
/** After the response arrives, a beat for the bar to fill and Jobee to cheer before the results show. */
const FINISH_MS = 750;
const MIN_SPIN_MS = 1400; // a very fast upload would otherwise flash the spinner for a blink
const wait = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));
const UNDO_MS = 4000;

const router = useRouter();
const { state, key } = useFlow();
const input = ref<HTMLInputElement>();
const reading = ref(false);
const finished = ref(false);
const dragging = ref(false);
const error = ref<string | null>(null);
let attempt = 0; // a newer upload wins over one still in flight

const expectedMs = ref(EXPECTED_MS);
const clock = useAnalysisClock(expectedMs);
if (!state.value.resume) doc.value = null;
const previewFailed = ref(false);
const picked = ref<{ name: string; size: number } | null>(null);
/** A result just arrived, so Jobee can celebrate it; coming back to the page later doesn't count. */
const justRead = ref(false);
const focusKey = ref<string | null>(null);

/** What the server has reported so far (empty when it can't stream, and the page falls back to the clock). */
const live = reactive({ read: false, candidates: null as number | null, engine: null as string | null, thinkingWords: null as number | null, found: [] as string[] });
function resetLive() {
  Object.assign(live, { read: false, candidates: null, engine: null, thinkingWords: null, found: [] });
  expectedMs.value = EXPECTED_MS;
}
function onEvent(e: ResumeEvent) {
  if (e.type === 'read') {
    live.read = true;
    expectedMs.value = e.expected_seconds * 1000;
  } else if (e.type === 'candidates') live.candidates = e.count;
  else if (e.type === 'engine') live.engine = e.source;
  else if (e.type === 'thinking') live.thinkingWords = e.words;
  else if (e.type === 'skill') live.found.push(e.name);
}

const resume = computed(() => state.value.resume);
const showResults = computed(() => !!resume.value && !reading.value);
const split = computed(() => reading.value || (showResults.value && !!doc.value));

/** Jobee reads along while the resume is processed, cheers when it's done, and is startled by an error. */
const mood = computed(() => (finished.value ? 'celebrate' : reading.value ? 'busy' : error.value ? 'surprised' : resume.value ? 'happy' : 'wave'));

function kb(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

// The scan line, highlights and "keywords spotted" tray all follow the clock. They come from a keyword scan in the browser, not from the API's result.
const scanned = computed(() => (doc.value ? Math.min(1, clock.f.value / SCAN_END) * doc.value.height : 0));
const reveal = computed(() => (showResults.value || finished.value ? Infinity : scanned.value));
const scan = computed(() => (reading.value && !finished.value && clock.f.value <= SCAN_END ? scanned.value : null));
const spotted = computed(() => {
  const d = doc.value;
  if (!d) return [];
  if (reveal.value === Infinity) return d.order;
  return [...new Set(d.marks.filter((m) => m.y <= scanned.value).map((m) => m.key))];
});
const countsByName = computed(() => new Map(Object.entries(doc.value?.counts ?? {}).map(([k, n]) => [k.toLowerCase(), n])));
const rows = computed<SkillRow[]>(() =>
  (resume.value?.skills ?? []).map((s) => {
    const label = displayName(s.name);
    // A scanned PDF has no text to count in, so nothing can be called "inferred".
    const n = doc.value?.chars ? (countsByName.value.get(label.toLowerCase()) ?? 0) : null;
    return { name: s.name, label, score: s.score, n };
  }),
);
/** Mentions are counted only for the skills in the result, since those are the ones highlighted. */
const stats = computed(() => {
  const d = doc.value;
  return d ? { pages: d.pageCount, chars: d.chars, mentions: rows.value.reduce((a, r) => a + (r.n ?? 0), 0) } : null;
});

// While the AI works, only skills it has confirmed are highlighted; once it is done, the skills in the result. Without
// live skills the browser's keyword scan stands in until the result arrives.
const liveSkills = computed(() => live.engine === 'llm');
const foundLabels = computed(() => live.found.map(displayName));
const shownKeys = computed(() => {
  if (showResults.value) return new Set(rows.value.map((r) => r.label.toLowerCase()));
  return liveSkills.value ? new Set(foundLabels.value.map((l) => l.toLowerCase())) : null;
});
const tray = computed(() =>
  liveSkills.value
    ? { title: 'Skills found', items: foundLabels.value, allConfirmed: true }
    : { title: 'Keywords spotted', items: spotted.value, allConfirmed: false },
);
// The stage follows the server's events; if it sent none, the clock.
const stage = computed(() => (finished.value ? 3 : !live.read ? clock.stage.value : live.candidates === null ? 1 : 2));

const bubble = computed(() => {
  if (finished.value) return 'Got it!';
  if (reading.value) return clock.slow.value && stage.value >= 2 ? 'Still on it. Good resumes take a moment.' : STAGE_LINES[stage.value];
  if (resume.value) return 'Nice! Here’s what I found.';
  return personaCopy[key.value].resume;
});

async function upload(file: File | undefined) {
  if (input.value) input.value.value = ''; // let the same file be picked again
  if (!file || reading.value) return;
  error.value = checkResumeFile(file);
  if (error.value) return;

  const mine = ++attempt;
  reading.value = true;
  finished.value = false;
  doc.value = null;
  previewFailed.value = false;
  justRead.value = false;
  undo.value = null;
  state.value.resume = null;
  resetLive();
  docOpen.value = false;
  picked.value = { name: file.name, size: file.size };
  clock.start();

  // The preview is built in the browser while the API works; neither waits for the other.
  const preview = readResumePdf(file).then(
    (d) => { if (mine === attempt) doc.value = d; },
    () => { if (mine === attempt) previewFailed.value = true; },
  );
  try {
    const result = await extractResume(file, (e) => { if (mine === attempt) onEvent(e); });
    if (mine !== attempt) return;
    if (result.error || !result.skills) {
      error.value = result.char_count === 0
        ? 'I couldn’t find any text in that PDF. It may be a scan. Try a PDF exported from Word or Google Docs.'
        : 'I read the file but couldn’t pull out the skills. Try again in a moment.';
      doc.value = null;
      return;
    }
    clock.stop();
    finished.value = true;
    await Promise.all([preview, new Promise((r) => setTimeout(r, FINISH_MS))]);
    if (mine !== attempt) return;
    justRead.value = true;
    // A scanned PDF has no text to check against, so its skills can't be told apart and all stay.
    const read = doc.value as ResumePreview | null;
    const skills = read?.chars ? limitInferred(result.skills, read) : result.skills;
    state.value.resume = { filename: result.filename ?? file.name, size: file.size, pages: result.page_count, skills };
  } catch (e) {
    if (mine !== attempt) return;
    error.value = e instanceof ResumeUploadError ? e.message : 'Something went wrong reading your resume. Try again in a moment.';
    doc.value = null;
  } finally {
    if (mine === attempt) {
      clock.stop();
      reading.value = false;
      finished.value = false;
    }
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false;
  upload(e.dataTransfer?.files[0]);
}

/** Pick a file again. The current results stay until one is chosen, so cancelling the file picker loses nothing. */
function chooseAnother() {
  if (reading.value) {
    attempt++;
    clock.stop();
    reading.value = false;
    finished.value = false;
    doc.value = null;
    previewFailed.value = false;
  }
  input.value?.click();
}

function skip() {
  attempt++;
  clock.stop();
  reading.value = false;
  state.value.resume = null;
  router.push(go('skills'));
}

// Screen size: the flower game only has room in the side margins on wide screens, and on narrow ones the resume preview
// collapses so the progress and the results stay in view.
const wideMedia = window.matchMedia('(min-width: 1180px)');
const narrowMedia = window.matchMedia('(max-width: 900px)');
const canPlay = ref(wideMedia.matches);
const narrow = ref(narrowMedia.matches);
const docOpen = ref(false);
const onWide = () => (canPlay.value = wideMedia.matches);
const onNarrow = () => (narrow.value = narrowMedia.matches);
wideMedia.addEventListener('change', onWide);
narrowMedia.addEventListener('change', onNarrow);
onBeforeUnmount(() => {
  wideMedia.removeEventListener('change', onWide);
  narrowMedia.removeEventListener('change', onNarrow);
});

// Fixing the result: a removed skill can be brought back for a few seconds.
const undo = ref<{ skill: { name: string; score: number }; index: number } | null>(null);
let undoTimer: number | undefined;
onBeforeUnmount(() => window.clearTimeout(undoTimer));

function removeSkill(row: SkillRow) {
  const r = state.value.resume;
  const i = r?.skills.findIndex((s) => s.name === row.name) ?? -1;
  if (!r || i < 0) return;
  undo.value = { skill: r.skills[i], index: i };
  r.skills = r.skills.filter((_, j) => j !== i);
  window.clearTimeout(undoTimer);
  undoTimer = window.setTimeout(() => (undo.value = null), UNDO_MS);
}
function undoRemove() {
  const r = state.value.resume;
  if (!r || !undo.value) return;
  r.skills = r.skills.toSpliced(undo.value.index, 0, undo.value.skill);
  undo.value = null;
}
</script>

<template>
  <!-- With a resume the skill check is optional, so Continue goes straight on to the analysis. -->
  <FlowShell :progress="3" :next="resume ? 'loading' : 'skills'" :next-label="resume ? 'Analyze my profile' : undefined" back="outcome" :mood="mood" gear="glasses" :wide="split" :next-disabled="!resume || reading">
    <template #bubble>{{ bubble }}</template>

    <!-- The flower game stays out of the header, footer and content, so it only has the side margins (wide screens only). -->
    <PollenGame v-if="reading && canPlay" :avoid="['.skip', '.stage', 'header', 'footer']" :bottom-reserve="90" />

    <div class="stage" :class="{ split }">
      <template v-if="split">
        <div class="left">
          <button v-if="narrow && doc" type="button" class="docbtn" :aria-expanded="docOpen" @click="docOpen = !docOpen">
            {{ docOpen ? 'Hide your resume' : showResults ? `Show your resume · ${stats?.mentions ?? 0} highlights` : 'Show your resume' }}
          </button>
          <ResumeDoc v-if="doc" v-show="!narrow || docOpen" :doc="doc" :reveal="reveal" :scan="scan" :shown-keys="shownKeys" :focus-key="focusKey" />
          <div v-else-if="previewFailed" class="card nopreview" role="status">
            <b>We couldn’t preview that file.</b>
            <p>Check that it’s a text-based PDF, not a scan. I’ll keep going in case Jobee can still read it.</p>
            <button type="button" class="link" @click="chooseAnother">Choose another file</button>
          </div>
          <p v-if="doc && showResults && (!narrow || docOpen)" class="doclabel"><span>Your resume</span><span>{{ stats?.mentions ?? 0 }} highlights</span></p>
        </div>
        <div class="right">
          <ResumeProgress
            v-if="reading && picked"
            :filename="picked.name"
            :size-label="kb(picked.size)"
            :stats="doc ? { chars: doc.chars, pages: doc.pageCount } : null"
            :stage="stage"
            :elapsed="clock.elapsed.value"
            :progress="clock.progress.value"
            :slow="clock.slow.value"
            :tray="tray"
            :thinking-words="live.thinkingWords"
            :candidates="live.candidates"
            :expected-seconds="Math.round(expectedMs / 1000)"
            :finished="finished"
          />
          <ResumeResults
            v-else-if="resume"
            :filename="resume.filename"
            :size-label="kb(resume.size)"
            :pages="resume.pages"
            :rows="rows"
            :celebrate="justRead"
            @focus="focusKey = $event"
            @remove="removeSkill"
          />
        </div>
      </template>

      <template v-else-if="resume">
        <ResumeResults
          :filename="resume.filename"
          :size-label="kb(resume.size)"
          :pages="resume.pages"
          :rows="rows"
          :celebrate="justRead"
          @remove="removeSkill"
        />
      </template>

      <button
        v-else
        type="button"
        class="drop"
        :class="{ dragging }"
        @click="input?.click()"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="onDrop"
      >
        <svg class="dash" aria-hidden="true"><rect width="100%" height="100%" rx="20" /></svg>
        <span class="up" aria-hidden="true"><Icon name="upload" :size="22" :stroke="2.6" /></span>
        <strong>{{ personaCopy[key].resumeDrop }}</strong>
        <small>PDF, up to 10 MB</small>
      </button>

      <p v-if="error" class="error" role="alert">{{ error }}</p>
      <button v-if="resume && !reading" type="button" class="link again" @click="chooseAnother">Upload a different PDF</button>
    </div>

    <input ref="input" type="file" accept="application/pdf,.pdf" hidden aria-label="Resume PDF" @change="upload(($event.target as HTMLInputElement).files?.[0])" />

    <div v-if="undo" class="toast" role="status">
      <span>Removed {{ displayName(undo.skill.name) }}</span>
      <button type="button" @click="undoRemove">Undo</button>
    </div>

    <template #skip>
      <RouterLink v-if="resume" :to="go('skills')" class="skip">Rate my skills too</RouterLink>
      <button v-else type="button" class="skip" @click="skip">No resume? Skip</button>
    </template>
  </FlowShell>
</template>

<style scoped>
.stage { max-width: 960px; margin: 0 auto; }
.stage.split { display: grid; grid-template-columns: 420px minmax(0, 1fr); gap: 24px; align-items: start; }
.left { position: sticky; top: 0; }
.right > :first-child { margin-top: 0; }
@media (max-width: 900px) { .stage.split { grid-template-columns: 1fr; } .left { position: static; order: 2; } }

.docbtn {
  width: 100%; margin-bottom: 10px; padding: 12px 16px; border: 2px solid var(--line-strong); border-radius: 14px; background: #fff;
  font: inherit; font-size: 16px; font-weight: 800; color: var(--ink); cursor: pointer;
}
@media (min-width: 901px) { .docbtn { display: none; } }

.drop {
  position: relative; width: 100%; max-width: 600px; margin: 0 auto; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 40px 24px; border: 0; border-radius: 20px; background: transparent; color: var(--ink);
  transition: background .26s, transform .26s cubic-bezier(.34, 1.56, .64, 1);
}
.drop:hover, .drop.dragging { background: var(--cream); transform: scale(1.01); }
.dash { position: absolute; inset: 0; width: 100%; height: 100%; pointer-events: none; overflow: visible; }
.dash rect { fill: none; stroke: var(--yellow); stroke-width: 3; stroke-dasharray: 8 7; }
.drop:hover .dash rect, .drop.dragging .dash rect { animation: march 1s linear infinite; }
@keyframes march { to { stroke-dashoffset: -30; } }
.up { width: 48px; height: 48px; border-radius: 50%; background: var(--yellow); box-shadow: 0 4px 0 var(--orange); display: grid; place-items: center; margin-bottom: 8px; }
.drop:hover .up, .drop.dragging .up { animation: bob .9s ease-in-out infinite; }
@keyframes bob { 50% { transform: translateY(-4px); } }
.drop strong { font-weight: 800; font-size: 18px; }
small { font-size: 15px; color: var(--muted); font-weight: 700; }

.error { margin: 14px auto 0; max-width: 600px; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 16px; line-height: 1.4; }
.card.nopreview { padding: 16px 20px; }
.nopreview p { margin: 6px 0 10px; font-size: 15px; font-weight: 700; color: var(--muted); }
.link { border: 0; background: none; padding: 6px 4px; font: inherit; font-size: 15px; font-weight: 800; color: var(--amber-ink); text-decoration: underline; text-underline-offset: 4px; cursor: pointer; }
.again { display: block; margin: 14px auto 0; }
.doclabel { display: flex; justify-content: space-between; margin: 8px 2px 0; font-size: 14px; font-weight: 700; color: var(--muted); }

.toast {
  position: fixed; left: 50%; bottom: 96px; z-index: 8; transform: translateX(-50%); display: flex; align-items: center; gap: 14px;
  padding: 10px 14px 10px 18px; border-radius: 16px; background: var(--ink); color: #fff; font-size: 15px; font-weight: 700;
  animation: pop .4s cubic-bezier(.34, 1.56, .64, 1) both;
}
.toast button { border: 0; background: none; color: var(--yellow); font: inherit; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; cursor: pointer; }
@keyframes pop { 0% { opacity: 0; transform: translateX(-50%) scale(.4); } 60% { opacity: 1; transform: translateX(-50%) scale(1.08); } }
@media (prefers-reduced-motion: reduce) { .drop:hover .dash rect, .drop:hover .up, .toast { animation: none; } }
</style>
