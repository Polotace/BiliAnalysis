import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import { createRouter, createWebHistory } from 'vue-router'
import TopNav from '@/components/layout/TopNav.vue'

function makeRouter() {
  return createRouter({
    history: createWebHistory(),
    routes: [
      { path: '/', component: { template: '<div>Home</div>' } },
      { path: '/analysis/stats', component: { template: '<div>Stats</div>' } },
    ],
  })
}

describe('TopNav', () => {
  it('renders logo text', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(TopNav, { global: { plugins: [router] } })
    expect(wrapper.text()).toContain('BiliInsight')
  })

  it('renders two nav links', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(TopNav, { global: { plugins: [router] } })
    const links = wrapper.findAll('a')
    expect(links.length).toBeGreaterThanOrEqual(2)
  })

  it('highlights active route', async () => {
    const router = makeRouter()
    router.push('/')
    await router.isReady()
    const wrapper = mount(TopNav, { global: { plugins: [router] } })
    const activeLink = wrapper.find('.\\!text-text')
    expect(activeLink.exists()).toBe(true)
  })
})
