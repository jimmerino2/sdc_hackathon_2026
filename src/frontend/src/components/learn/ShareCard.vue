<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import Icon from '../Icon.vue';
import JbButton from './JbButton.vue';
import LinkedInShareDialog from './LinkedInShareDialog.vue';

defineProps<{ role: string; skills: number; sections: number; minutes?: number | null; name?: string }>();

const dialog = ref<InstanceType<typeof LinkedInShareDialog>>();
const route = useRoute();
const router = useRouter();

/** What LinkedIn's sign-in sent the browser back with, kept here so the address can be tidied. */
type Result = { kind: 'posted'; url: string | null } | { kind: 'cancelled' } | { kind: 'error'; reason: string };
const result = ref<Result | null>(null);

onMounted(() => {
  const { linkedin, post, reason, ...rest } = route.query;
  if (typeof linkedin !== 'string') return;
  result.value =
    linkedin === 'posted' ? { kind: 'posted', url: typeof post === 'string' && post.startsWith('https://www.linkedin.com/') ? post : null }
    : linkedin === 'cancelled' ? { kind: 'cancelled' }
    : { kind: 'error', reason: typeof reason === 'string' ? reason : 'Something went wrong. Try again.' };
  void router.replace({ query: rest }); // a refresh must not show it again
});
</script>

<template>
  <section class="jb jb-card jb-share">
    <p class="jb-eyebrow">Role-ready!</p>
    <h3 class="jb-card__title">Show it off</h3>
    <p class="jb-next__hint">Share that you completed a Jobee learning roadmap for {{ role }}. You see and edit the post first, and nothing is sent until you say so.</p>
    <div class="jb-next__cta">
      <JbButton @click="dialog?.open()">Larp on LinkedIn</JbButton>
    </div>

    <p v-if="result?.kind === 'posted'" class="jb-share__note jb-share__note--ok" role="status">
      <Icon name="check" :size="18" /> Posted to LinkedIn.
      <a v-if="result.url" :href="result.url" target="_blank" rel="noopener noreferrer">See your post</a>
    </p>
    <p v-else-if="result?.kind === 'cancelled'" class="jb-share__note" role="status">No problem. Nothing was posted.</p>
    <p v-else-if="result?.kind === 'error'" class="jb-next__err" role="alert">{{ result.reason }}</p>

    <LinkedInShareDialog ref="dialog" :role="role" :skills="skills" :sections="sections" :minutes="minutes" :name="name" />
  </section>
</template>
