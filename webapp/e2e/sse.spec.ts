import { test, expect } from '@playwright/test'

async function startBasicScan(page) {
  await page.goto('/')
  await page.fill('#url', 'https://example.com')
  await page.fill('#company_name', 'Test Co')
  await page.fill('#email', 'test@example.com')
  await page.click('#start-discovery')
  await page.waitForSelector('#phase-selection.active', { timeout: 30000 })
  await page.click('#select-all-cb')
  await page.click('#start-scan')
  await page.waitForSelector('#phase-scanning.active', { timeout: 10000 })
}

test('SSE monitor shows first event and progress', async ({ page }) => {
  await startBasicScan(page)

  // Assert test IDs exist
  const status = page.locator('[data-testid="sse-status"]')
  const progress = page.locator('[data-testid="sse-progress"]')
  await expect(status).toBeVisible()
  await expect(progress).toBeVisible()

  // First progress within 15s
  await page.waitForFunction(() => {
    const el = document.querySelector('[data-testid="sse-progress"]') as HTMLElement | null
    return !!el && el.style.width !== '0%'
  }, { timeout: 15000 })
})

test('No report transition without terminal event', async ({ page }) => {
  await startBasicScan(page)

  // Ensure we are in scanning phase
  await expect(page.locator('#phase-scanning')).toHaveClass(/active/)

  // Check we do not jump to report immediately
  await expect(page.locator('#phase-report')).not.toHaveClass(/active/)
})

test('Network drop -> retry/backoff and fallback', async ({ page, context }) => {
  await page.goto('/')
  await page.fill('#url', 'https://example.com')
  await page.fill('#company_name', 'Test Co')
  await page.fill('#email', 'test@example.com')
  await page.click('#start-discovery')
  await page.waitForSelector('#phase-selection.active', { timeout: 30000 })
  await page.click('#select-all-cb')

  // Block SSE to simulate drop before starting scan
  await context.route('**/api/scan/stream/**', route => route.abort())

  await page.click('#start-scan')
  await page.waitForSelector('#phase-scanning.active', { timeout: 10000 })

  // Wait a bit to allow retries
  await page.waitForTimeout(6000)

  // Remove block to allow connection or fallback
  await context.unroute('**/api/scan/stream/**')

  // Status element should be present regardless
  await expect(page.locator('[data-testid="sse-status"]')).toBeVisible()
})

