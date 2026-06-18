import { describe, it, expect } from 'vitest'

describe('useChart', () => {
  it('exports useChart function', async () => {
    const mod = await import('@/composables/useChart')
    expect(mod.useChart).toBeDefined()
    expect(typeof mod.useChart).toBe('function')
  })

  it('echarts modules registered without error', async () => {
    await import('@/composables/useChart')
    expect(true).toBe(true)
  })
})
