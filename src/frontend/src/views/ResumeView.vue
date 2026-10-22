<script setup lang="ts">
import { computed, ref } from 'vue';
import { useRouter } from 'vue-router';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { checkResumeFile, extractResume, ResumeUploadError } from '../api/resume';
import { skillLabel } from '../data/skills';
import { useFlow } from '../state';
import { go } from '../router';

const SHOWN_SKILLS = 8;

const router = useRouter();
const { state } = useFlow();
const input = ref<HTMLInputElement>();
const reading = ref(false);
const dragging = ref(false);
const error = ref<string | null>(null);
let attempt = 0; // a newer upload wins over one still in flight

const shown = computed(() => state.value.resume?.skills.slice(0, SHOWN_SKILLS) ?? []);
const more = computed(() => Math.max((state.value.resume?.skills.length ?? 0) - SHOWN_SKILLS, 0));

function kb(bytes: number) {
  return bytes >= 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`;
}

async function upload(file: File | undefined) {
  if (!file || reading.value) return;
  error.value = checkResumeFile(file);
  if (error.value) return;

  const mine = ++attempt;
  reading.value = true;
  try {
    const result = await extractResume(file);
    if (mine !== attempt) return;
    if (result.error || !result.skills) {
      error.value = result.char_count === 0
        ? 'I couldn’t find any text in that PDF. It may be a scan. Try a PDF exported from Word or Google Docs.'
        : 'I read the file but couldn’t pull out the skills. Try again in a moment.';
      return;
    }
    state.value.resume = {
      filename: result.filename ?? file.name,
      size: file.size,
      pages: result.page_count,
      skills: result.skills,
    };
  } catch (e) {
    if (mine !== attempt) return;
    error.value = e instanceof ResumeUploadError ? e.message : 'Something went wrong reading your resume. Try again in a moment.';
  } finally {
    if (mine === attempt) reading.value = false;
    if (input.value) input.value.value = ''; // let the same file be picked again
  }
}

function onDrop(e: DragEvent) {
  dragging.value = false;
  upload(e.dataTransfer?.files[0]);
}

function skip() {
  attempt++;
  state.value.resume = null;
  router.push(go('skills'));
}
</script>

<template>
  <FlowShell :progress="3" next="skills" back="mind" :next-disabled="!state.resume || reading">
    <h1>Got a resume? Let Jobee read it.</h1>
    <Bubble class="b" :size="60">Upload your resume, or even a list of class projects. I’ll pull out the skills.</Bubble>
    <button
      type="button"
      class="drop"
      :class="{ dragging, busy: reading }"
      :disabled="reading"
      @click="input?.click()"
      @dragover.prevent="dragging = true"
      @dragleave="dragging = false"
      @drop.prevent="onDrop"
    >
      <span class="up"><Icon :name="reading ? 'sparkles' : 'upload'" :size="22" /></span>
      <template v-if="reading">
        <strong>Jobee is reading your resume…</strong>
        <small>This takes a few seconds</small>
      </template>
      <template v-else>
        <strong>{{ state.resume ? 'Drop a different PDF' : 'Drop your resume or LinkedIn PDF' }}</strong>
        <small>PDF · up to 10 MB · stays private</small>
      </template>
    </button>
    <input ref="input" type="file" accept="application/pdf,.pdf" hidden @change="upload(($event.target as HTMLInputElement).files?.[0])" />
    <p v-if="error" class="error" role="alert">{{ error }}</p>

    <template v-if="state.resume && !reading">
      <div class="file card">
        <span class="fic"><Icon name="file" :size="20" /></span>
        <span class="meta">
          <strong>{{ state.resume.filename }}</strong>
          <small>{{ kb(state.resume.size) }} · {{ state.resume.pages }} {{ state.resume.pages === 1 ? 'page' : 'pages' }} · read just now</small>
        </span>
        <span class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> Read</span>
      </div>
      <h3>Jobee found these skills</h3>
      <div v-if="shown.length" class="chips">
        <span v-for="s in shown" :key="s.name" class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ skillLabel(s.name) }}</span>
        <span v-if="more" class="chip chip-neutral">+ {{ more }} more</span>
      </div>
      <p v-else class="none">I couldn’t spot specific skills in this one. That’s okay, the skill check is next.</p>
    </template>

    <button type="button" class="skip" @click="skip">No resume? Skip</button>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.drop { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 36px 16px; border: 3px dashed var(--yellow); border-radius: 20px; }
.drop:hover, .drop.dragging { background: rgba(255, 193, 7, .08); }
.drop.busy { cursor: progress; }
.drop.busy .up { animation: pulse 1.2s ease-in-out infinite; }
@keyframes pulse { 50% { transform: scale(1.12); } }
.up { width: 46px; height: 46px; border-radius: 50%; background: var(--yellow); box-shadow: 0 3px 0 var(--orange); display: grid; place-items: center; margin-bottom: 6px; }
.drop strong { font-weight: 800; font-size: 16px; } small { font-size: 12px; color: var(--muted); font-weight: 600; }
.error { margin-top: 14px; padding: 12px 16px; border-radius: 14px; background: #fdecea; color: #b3261e; font-weight: 800; font-size: 14px; line-height: 1.4; }
.file { margin-top: 18px; display: flex; align-items: center; gap: 14px; padding: 14px 16px; border-radius: 16px; }
.fic { width: 40px; height: 40px; border-radius: 10px; background: var(--cream); display: grid; place-items: center; }
.meta { display: flex; flex-direction: column; flex: 1; gap: 2px; min-width: 0; } .meta strong { font-weight: 800; font-size: 14px; overflow-wrap: anywhere; }
h3 { margin: 22px 0 12px; font-weight: 900; font-size: 15px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 12px; padding: 6px 12px 6px 10px; }
.none { color: var(--muted); font-weight: 700; font-size: 14px; }
.skip { display: block; margin: 24px auto 0; font-size: 12px; font-weight: 900; letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }
.skip:hover { color: var(--ink); }
</style>
