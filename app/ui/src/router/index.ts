import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/pages/LoginPage.vue'),
    },
    {
      path: '/change-password',
      name: 'change-password',
      component: () => import('@/pages/ChangePasswordPage.vue'),
    },
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

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.loading) await auth.fetchMe()

  // Redirect authenticated users away from login page
  if (to.path === '/login' && auth.isLoggedIn) {
    return auth.mustChangePassword ? '/change-password' : '/'
  }

  // Allow anonymous access to all pages except admin
  if (to.path === '/admin' && !auth.isAdmin) return '/'
  if (to.path === '/change-password' && !auth.mustChangePassword) return '/'
})

export default router
