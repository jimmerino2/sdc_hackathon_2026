import { createRouter, createWebHistory } from 'vue-router';
import type { PersonaKey } from './data/flows';

export const steps = [
  'landing',
  'who',
  'mind',
  'skills',
  'resume',
  'loading',
  'signal',
  'roles',
  'gap',
  'pathway',
  'resources',
] as const;
export type Step = (typeof steps)[number];

export const stepLabels: Record<Step, string> = {
  landing: '01 Landing',
  who: '02 Who are you',
  mind: '03 What’s on your mind',
  skills: '04 Skill check',
  resume: '05 Resume upload',
  loading: '06 Loading',
  signal: '07 AI signal',
  roles: '08 Future roles',
  gap: '09 Skill gap',
  pathway: '10 Reskill pathway',
  resources: '11 Skill resources',
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
