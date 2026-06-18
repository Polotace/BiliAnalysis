import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatCard from '@/components/shared/StatCard.vue'

describe('StatCard', () => {
  it('renders label and value', () => {
    const wrapper = mount(StatCard, {
      props: { label: '测试指标', value: 12345 },
    })
    expect(wrapper.text()).toContain('测试指标')
    expect(wrapper.text()).toContain('1.2万')
  })

  it('renders subLabel when provided', () => {
    const wrapper = mount(StatCard, {
      props: { label: '播放量', value: 999, subLabel: '近7天均值' },
    })
    expect(wrapper.text()).toContain('近7天均值')
  })

  it('does not render subLabel when omitted', () => {
    const wrapper = mount(StatCard, {
      props: { label: '播放量', value: 999 },
    })
    expect(wrapper.text()).not.toContain('近7天均值')
  })

  it('displays raw string values directly', () => {
    const wrapper = mount(StatCard, {
      props: { label: 'R²', value: '0.856' },
    })
    expect(wrapper.text()).toContain('0.856')
  })
})
