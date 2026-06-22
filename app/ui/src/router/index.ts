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
    {
      path: '/analysis/keywords',
      name: 'keywords',
      component: () => import('@/pages/analysis/KeywordsPage.vue'),
    },
    {
      path: '/analysis/models',
      name: 'models',
      component: () => import('@/pages/analysis/ModelComparisonPage.vue'),
    },
    {
      path: '/videos',
      name: 'videos',
      component: () => import('@/pages/browse/VideoLibraryPage.vue'),
      meta: { keepAlive: true },
    },
    {
      path: '/videos/:aid',
      name: 'video-detail',
      component: () => import('@/pages/browse/VideoDetailPage.vue'),
    },
    {
      path: '/weeks',
      name: 'weeks',
      component: () => import('@/pages/browse/WeeksPage.vue'),
      meta: { keepAlive: true },
    },
    {
      path: '/weeks/:number',
      name: 'week-detail',
      component: () => import('@/pages/browse/WeekDetailPage.vue'),
    },
    {
      path: '/creators',
      name: 'creators',
      component: () => import('@/pages/browse/CreatorsPage.vue'),
      meta: { keepAlive: true },
    },
    {
      path: '/creators/:mid',
      name: 'creator-detail',
      component: () => import('@/pages/browse/CreatorDetailPage.vue'),
    },
    {
      path: '/categories',
      name: 'categories',
      component: () => import('@/pages/browse/CategoriesPage.vue'),
    },
    {
      path: '/admin',
      name: 'admin',
      component: () => import('@/pages/AdminPage.vue'),
    },
  ],
  scrollBehavior(to, from, savedPosition) {
    if (savedPosition) {
      return savedPosition
    }
    return { top: 0 }
  },
})

export default router
