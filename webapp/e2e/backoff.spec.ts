import { test, expect } from '@playwright/test'

test('Exponential backoff calculation', async ({ page }) => {
  await page.goto('/')
  const delays = await page.evaluate(() => {
    // @ts-ignore
    const M = (window as any).ScanMonitor
    // construct with dummy scan id and container id
    // @ts-ignore
    const inst = new M('TEST', 'scan-monitor')
    return [1, 2, 3, 4, 5, 6, 7].map(a => inst.calculateBackoffDelay(a))
  })
  expect(delays).toEqual([1000, 2000, 4000, 8000, 16000, 30000, 30000])
})

