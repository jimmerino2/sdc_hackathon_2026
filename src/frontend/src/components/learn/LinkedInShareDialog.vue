<script setup lang="ts">
import { computed, ref, watch } from 'vue';
import Icon from '../Icon.vue';
import JbButton from './JbButton.vue';
import { linkedinEnabled, startLinkedInShare } from '../../api/linkedin';
import { draftText, drawCertificate, IMAGE_H, IMAGE_W, type ShareFacts } from '../../learn/sharePost';

const props = defineProps<{ role: string; skills: number; sections: number; minutes?: number | null; name?: string }>();

const MAX_TEXT = 3000;
const dlg = ref<HTMLDialogElement>();
const text = ref('');
const showName = ref(true);
const image = ref('');
const enabled = ref(false);
const busy = ref(false);
const error = ref<string | null>(null);
const copied = ref(false);

const cleanName = computed(() => props.name?.trim() ?? '');
const facts = computed<ShareFacts>(() => ({ role: props.role, skills: props.skills, sections: props.sections, minutes: props.minutes, name: showName.value && cleanName.value ? cleanName.value : null }));
const left = computed(() => MAX_TEXT - text.value.length);
const canPost = computed(() => !busy.value && !!text.value.trim() && left.value >= 0 && !!image.value);

/** Draws the card in the browser, once the fonts are ready, and keeps it as a PNG for the preview, the download and the post. */
async function render() {
  try {
    await document.fonts?.ready;
  } catch {
    // the card still draws, in a fallback font
  }
  const canvas = document.createElement('canvas');
  canvas.width = IMAGE_W;
  canvas.height = IMAGE_H;
  const ctx = canvas.getContext('2d');
  if (!ctx) return;
  drawCertificate(ctx, facts.value);
  image.value = canvas.toDataURL('image/png');
}
watch(showName, render);

function open() {
  text.value = draftText(facts.value);
  error.value = null;
  copied.value = false;
  busy.value = false;
  dlg.value?.showModal();
  void render();
  void linkedinEnabled().then((on) => (enabled.value = on));
}
const close = () => dlg.value?.close();
defineExpose({ open });

async function post() {
  if (!canPost.value) return;
  busy.value = true;
  error.value = null;
  try {
    window.location.assign(await startLinkedInShare(text.value, image.value)); // LinkedIn asks for their OK; busy stays on while the page leaves
  } catch (e) {
    error.value = e instanceof Error ? e.message : 'Couldn’t start the LinkedIn post. Try again in a moment.';
    busy.value = false;
  }
}

async function copy() {
  try {
    await navigator.clipboard.writeText(text.value);
    copied.value = true;
    setTimeout(() => (copied.value = false), 2000);
  } catch {
    error.value = 'Couldn’t copy. Select the text and copy it yourself.';
  }
}
</script>

<template>
  <Teleport to="body">
    <dialog ref="dlg" class="jb jb-sharedlg" aria-labelledby="share-title" @click.self="close">
      <div class="jb-sharedlg__inner">
        <div class="jb-sharedlg__top">
          <h2 id="share-title">Share your Jobee roadmap</h2>
          <button type="button" class="jb-sharedlg__close" aria-label="Close" @click="close"><Icon name="x" :size="20" /></button>
        </div>

        <div class="jb-sharedlg__grid">
          <div class="jb-sharedlg__imgwrap">
            <img v-if="image" :src="image" alt="Jobee roadmap completed card" class="jb-sharedlg__img" />
            <div v-else class="jb-sharedlg__img jb-sharedlg__img--wait" aria-hidden="true" />
            <label v-if="cleanName" class="jb-sharedlg__check"><input v-model="showName" type="checkbox" /> Put my name on the image</label>
          </div>

          <div class="jb-sharedlg__form">
            <label for="share-text" class="jb-sharedlg__label">Your post <span>Edit it as you like</span></label>
            <textarea id="share-text" v-model="text" rows="7" class="jb-sharedlg__text" :aria-invalid="left < 0" />
            <p class="jb-sharedlg__count" :class="{ 'jb-sharedlg__count--over': left < 0 }">{{ left.toLocaleString() }} characters left</p>
          </div>
        </div>

        <p v-if="error" class="jb-next__err" role="alert">{{ error }}</p>

        <div class="jb-sharedlg__actions">
          <JbButton v-if="enabled" :disabled="!canPost" @click="post">{{ busy ? 'Opening LinkedIn…' : 'Post to LinkedIn' }}</JbButton>
          <JbButton variant="quiet" @click="copy">{{ copied ? 'Copied!' : 'Copy text' }}</JbButton>
          <a v-if="image" class="jb jb-btn jb-btn--quiet" :href="image" download="jobee-roadmap-completed.png">Download image</a>
          <a class="jb jb-btn jb-btn--quiet" href="https://www.linkedin.com/feed/" target="_blank" rel="noopener noreferrer">Open LinkedIn</a>
        </div>

        <p v-if="enabled" class="jb-sharedlg__consent">
          When you press Post, LinkedIn asks you to sign in and allow Jobee to post <b>once</b> on your behalf. We post only the text and image shown here.
          We don’t keep your LinkedIn sign-in, and nothing is posted unless you press Post and agree on LinkedIn.
        </p>
        <p v-else class="jb-sharedlg__consent">Posting straight from Jobee isn’t switched on yet. Copy the text, download the image, and post them on LinkedIn yourself.</p>
        <p class="jb-sharedlg__consent">The card is Jobee’s own record of what you completed. It isn’t an accredited qualification, and we don’t describe it as one.</p>
      </div>
    </dialog>
  </Teleport>
</template>
