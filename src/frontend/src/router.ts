import { createRouter, createWebHistory } from 'vue-router';

export const steps = [
  'landing',
  'login',
  'bee',
  'name',
  'who',
  'mind',
  'outcome',
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
  login: '01a Log in',
  bee: '01b Pick your bee',
  name: '01c What do we call you',
  who: '02 Who are you',
  mind: '03 What’s on your mind',
  outcome: '03a What you’ll get',
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
    { path: '/mascot', name: 'mascot', component: () => import('./views/MascotView.vue') },
    // The landing page lives at the site root; every other step keeps its own path.
    ...steps.map((s) => ({ path: s === 'landing' ? '/' : `/${s}`, name: s, component: viewFor(s) })),
    { path: '/landing', redirect: '/' },
    // Old links from when the address started with the persona (/a/landing).
    { path: '/:persona(a|b|c)/:step', redirect: (to) => (to.params.step === 'landing' ? '/' : `/${to.params.step}`) },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

export function go(step: Step) {
  return { name: step };
}
