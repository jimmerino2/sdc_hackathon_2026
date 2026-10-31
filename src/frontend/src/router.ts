import { createRouter, createWebHistory } from 'vue-router';
import { isOnboarded } from './api/profile';

export const steps = [
  'landing',
  'login',
  'bee',
  'name',
  'who',
  'interests',
  'resume',
  'skills',
  'loading',
  'roles',
  'signal',
  'gap',
  'sync',
  'building',
  'pathway',
  'challenges',
  'hive',
  'social',
  'suggested',
  'role',
  'generating',
  'profile',
  'outlook',
  'occupations',
  'benchmark',
] as const;
export type Step = (typeof steps)[number];

export const stepLabels: Record<Step, string> = {
  landing: '01 Landing',
  login: '01a Log in',
  bee: '01b Pick your bee',
  name: '01c What do we call you',
  who: '02 Who are you',
  interests: '03 What you’re into',
  resume: '04 Resume upload',
  skills: '05 Skill check',
  loading: '06 Loading',
  roles: '07 Future roles',
  signal: '08 Forecast',
  gap: '08a Skill gap',
  sync: '09 Sync your email',
  building: '10 Building roadmap',
  pathway: '11 Reskill pathway',
  challenges: '11a Challenges',
  hive: '11b Protect the Hive',
  social: '11c Social',
  suggested: '12 My roles',
  role: '13 Role details',
  generating: '14 Generating a roadmap',
  profile: '15 Profile',
  outlook: '16 AI outlook',
  occupations: '17 Occupational forecasting',
  benchmark: '18 LLM forecast benchmark',
};

/** Pages that live inside the sidebar layout. */
const tabSteps: readonly Step[] = ['pathway', 'challenges', 'hive', 'social', 'suggested', 'role', 'outlook', 'occupations', 'benchmark', 'profile'];

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
    ...steps.map((s) => ({ path: s === 'landing' ? '/' : `/${s}`, name: s, component: viewFor(s), meta: { tabs: tabSteps.includes(s) } })),
    { path: '/landing', redirect: '/' },
    // Old links from when the address started with the persona (/a/landing).
    { path: '/:persona(a|b|c)/:step', redirect: (to) => (to.params.step === 'landing' ? '/' : `/${to.params.step}`) },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
  scrollBehavior: () => ({ top: 0 }),
});

/** The question pages and everything up to building the roadmap. Once a browser has a roadmap these are closed to it. */
const onboardingSteps: readonly string[] = steps.slice(0, steps.indexOf('pathway'));

router.beforeEach((to) => {
  if (isOnboarded() && onboardingSteps.includes(to.name as string)) return { name: 'pathway', replace: true };
});

export function go(step: Step) {
  return { name: step };
}
