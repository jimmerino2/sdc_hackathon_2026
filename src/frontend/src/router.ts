import { createRouter, createWebHistory } from 'vue-router';
import type { PersonaKey } from './data/flows';

export const steps = [
  'landing',
  'name',
  'who',
  'mind',
  'resume',
  'skills',
  'loading',
  'roles',
  'signal',
  'sync',
  'building',
  'pathway',
  'resources',
] as const;
export type Step = (typeof steps)[number];

export const stepLabels: Record<Step, string> = {
  landing: '01 Landing',
  name: '01b What do we call you',
  who: '02 Who are you',
  mind: '03 What’s on your mind',
  resume: '04 Resume upload',
  skills: '05 Skill check',
  loading: '06 Loading',
  roles: '07 Future roles',
  signal: '08 Forecast & skill gap',
  sync: '09 Sync your email',
  building: '10 Building roadmap',
  pathway: '11 Reskill pathway',
  resources: '12 Skill resources',
};

const views = import.meta.glob('./views/*.vue');
const viewFor = (s: Step) => {
  const name = s.charAt(0).toUpperCase() + s.slice(1);
  return views[`./views/${name}View.vue`] as () => Promise<unknown>;
};

export const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    { path: '/', redirect: '/a/landing' },
    ...steps.map((s) => ({
      path: `/:persona(a|b|c)/${s}`,
      name: s,
      component: viewFor(s),
    })),
    { path: '/:pathMatch(.*)*', redirect: '/a/landing' },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

export function go(persona: PersonaKey, step: Step) {
  return { name: step, params: { persona } };
}
