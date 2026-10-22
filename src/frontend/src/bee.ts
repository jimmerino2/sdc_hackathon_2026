import { ref, watch } from 'vue';

export const BEES = ['Libbee', 'Tobee', 'Barnabee', 'Phoebee'] as const;
export type BeeName = (typeof BEES)[number];

const KEY = 'jobee_bee';
const saved = typeof localStorage !== 'undefined' ? localStorage.getItem(KEY) : null;

/** The learner's chosen companion. Every Mascot on screen follows this unless given its own `bee`. */
export const bee = ref<BeeName>(BEES.includes(saved as BeeName) ? (saved as BeeName) : 'Libbee');

watch(bee, (b) => localStorage.setItem(KEY, b));

export const beeInfo: Record<BeeName, { tagline: string; vibe: string }> = {
  Libbee: { tagline: 'Bright and bubbly', vibe: 'Cheers you on every step' },
  Tobee: { tagline: 'Bold and bouncy', vibe: 'Extra stripes, extra energy' },
  Barnabee: { tagline: 'Seen it all', vibe: 'A tired manager. Honest feedback, no fluff' },
  Phoebee: { tagline: 'Running on coffee', vibe: 'A petite, overworked manager. Gets it done' },
};
