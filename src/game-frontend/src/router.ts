import { createRouter, createWebHistory } from 'vue-router'
import { useProgress } from '@/stores/progress'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'entry', component: () => import('@/views/EntryView.vue'), meta: { bare: true } },
    { path: '/start', name: 'onboarding', component: () => import('@/views/OnboardingView.vue'), meta: { bare: true } },
    { path: '/academy', name: 'academy', component: () => import('@/views/AcademyView.vue'), meta: { needsProfile: true } },
    {
      path: '/academy/:missionId',
      name: 'lesson',
      component: () => import('@/views/LessonView.vue'),
      props: true,
      meta: { needsProfile: true },
    },
    { path: '/frontier', name: 'frontier', component: () => import('@/views/FrontierView.vue'), meta: { needsProfile: true } },
    { path: '/workshop', name: 'workshop', component: () => import('@/views/WorkshopView.vue'), meta: { needsProfile: true } },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach((to) => {
  if (to.meta.needsProfile && !useProgress().profile) return { name: 'onboarding' }
})
