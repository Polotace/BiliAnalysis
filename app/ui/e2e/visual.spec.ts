import { test, expect } from '@playwright/test'

test.describe('visual regression', () => {
  test('homepage layout matches design mockup', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('homepage.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('stats page layout', async ({ page }) => {
    await page.goto('/analysis/stats')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('stats.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('clusters page layout', async ({ page }) => {
    await page.goto('/analysis/clusters')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('clusters.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('predictions page layout', async ({ page }) => {
    await page.goto('/analysis/predictions')
    await page.waitForTimeout(2000)
    await expect(page).toHaveScreenshot('predictions.png', {
      maxDiffPixelRatio: 0.1,
      fullPage: true,
    })
  })

  test('navigation between pages works', async ({ page }) => {
    await page.goto('/')
    await page.waitForTimeout(1000)
    await page.click('text=分析')
    await expect(page).toHaveURL(/\/analysis\/stats/)
  })
})
