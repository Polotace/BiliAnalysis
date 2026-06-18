import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import SectionHeader from '@/components/shared/SectionHeader.vue'

describe('SectionHeader', () => {
  it('renders title', () => {
    const wrapper = mount(SectionHeader, {
      props: { title: '平台概览' },
    })
    expect(wrapper.text()).toContain('平台概览')
  })

  it('renders description when provided', () => {
    const wrapper = mount(SectionHeader, {
      props: { title: '平台概览', description: '数据全景' },
    })
    expect(wrapper.text()).toContain('数据全景')
  })

  it('does not render description paragraph when omitted', () => {
    const wrapper = mount(SectionHeader, {
      props: { title: '平台概览' },
    })
    const p = wrapper.findAll('p')
    expect(p.length).toBe(0)
  })
})
