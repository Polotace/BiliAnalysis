import { describe, it, expect } from 'vitest'

describe('useApi', () => {
  it('exports useStats, useClusters, usePredictions', async () => {
    const mod = await import('@/composables/useApi')
    expect(mod.useStats).toBeDefined()
    expect(mod.useClusters).toBeDefined()
    expect(mod.usePredictions).toBeDefined()
  })

  it('fetch functions return method instances', async () => {
    const { fetchStats, fetchClusters, fetchPredictions } = await import('@/composables/useApi')
    expect(fetchStats()).toBeDefined()
    expect(fetchClusters()).toBeDefined()
    expect(fetchPredictions()).toBeDefined()
  })
})
