import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/',
      name: 'home',
      component: () => import('@/pages/HomePage.vue'),
    },
    {
      path: '/analysis/stats',
      name: 'stats',
      component: () => import('@/pages/analysis/StatsPage.vue'),
    },
    {
      path: '/analysis/clusters',
      name: 'clusters',
      component: () => import('@/pages/analysis/ClusterPage.vue'),
    },
    {
      path: '/analysis/predictions',
      name: 'predict',
      component: () => import('@/pages/analysis/PredictPage.vue'),
    },
  ],
  scrollBehavior() {
    return { top: 0 }
  },
})

export default router
