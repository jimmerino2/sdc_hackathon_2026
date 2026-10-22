<script setup lang="ts">
import { ref } from 'vue';
import FlowShell from '../components/FlowShell.vue';
import Bubble from '../components/Bubble.vue';
import Icon from '../components/Icon.vue';
import { useFlow } from '../state';

const { persona } = useFlow();
const uploaded = ref(true);
</script>

<template>
  <FlowShell :progress="4" next="loading" next-label="Analyze my profile" skip-label="No resume? Skip">
    <h1>Got a resume? Let Jobee read it.</h1>
    <Bubble class="b" :size="60">Upload your resume, or even a list of class projects. I’ll pull out the skills.</Bubble>
    <button class="drop" @click="uploaded = true">
      <span class="up"><Icon name="upload" :size="22" /></span>
      <strong>Drop your resume or LinkedIn PDF</strong>
      <small>PDF or DOCX · up to 5 MB · stays private</small>
    </button>
    <template v-if="uploaded">
      <div class="file card">
        <span class="fic"><Icon name="file" :size="20" /></span>
        <span class="meta"><strong>{{ persona.resume.file }}</strong><small>{{ persona.resume.size }} · {{ persona.resume.pages }} pages · read just now</small></span>
        <span class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> Read</span>
      </div>
      <h3>Jobee found these skills</h3>
      <div class="chips">
        <span v-for="s in persona.resume.found" :key="s" class="chip chip-have"><Icon name="check" :size="14" :stroke="3" /> {{ s }}</span>
        <span class="chip chip-neutral">+ {{ persona.resume.more }} more</span>
      </div>
    </template>
  </FlowShell>
</template>

<style scoped>
h1 { font-size: 30px; font-weight: 900; margin-bottom: 24px; }
.b { margin-bottom: 24px; }
.drop { width: 100%; display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 36px 16px; border: 3px dashed var(--yellow); border-radius: 20px; }
.drop:hover { background: rgba(255, 193, 7, .08); }
.up { width: 46px; height: 46px; border-radius: 50%; background: var(--yellow); box-shadow: 0 3px 0 var(--orange); display: grid; place-items: center; margin-bottom: 6px; }
.drop strong { font-weight: 800; font-size: 16px; } small { font-size: 12px; color: var(--muted); font-weight: 600; }
.file { margin-top: 18px; display: flex; align-items: center; gap: 14px; padding: 14px 16px; border-radius: 16px; }
.fic { width: 40px; height: 40px; border-radius: 10px; background: var(--cream); display: grid; place-items: center; }
.meta { display: flex; flex-direction: column; flex: 1; gap: 2px; } .meta strong { font-weight: 800; font-size: 14px; }
h3 { margin: 22px 0 12px; font-weight: 900; font-size: 15px; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { font-size: 12px; padding: 6px 12px 6px 10px; }
</style>
