import { test, expect } from '@playwright/test'

const BASE_URL = process.env.BASE_URL || 'http://localhost:3000'

test.describe('E2E Full Flow (React 3000 + FastAPI 8000)', () => {
  test('configuration → discovery (manual URL) → selection → scanning → report', async ({ page }) => {
    // Configuration
    await page.goto(BASE_URL)
    await page.fill('#url', 'https://example.com')
    await page.fill('#company', 'Test Company')
    await page.fill('#email', 'test@example.com')

    // Avvia discovery
    await page.getByRole('button', { name: /Avvia Discovery URL/i }).click()
    await expect(page).toHaveURL(/\/discovery/)

    // Opzionale: attendi un feedback di progresso/badge
    await page.waitForSelector('.discovery-progress-section .progress-bar', { timeout: 15000 })

    // Aggiungi manualmente un URL per garantire almeno una pagina
    await page.getByPlaceholder('https://esempio.com/pagina').fill('https://example.com')
    await page.getByRole('button', { name: /^Aggiungi$/ }).click()

    // Procedi alla selezione anche se discovery non ha popolato pagine
    await page.getByRole('button', { name: /Procedi alla Selezione/ }).click()
    await expect(page).toHaveURL(/\/selection/)

    // Seleziona la prima pagina nella tabella
    const firstRowCheckbox = page.locator('table.pages-table tbody tr:first-of-type input[type="checkbox"]')
    await firstRowCheckbox.check()

    // Avvia scansione
    await page.getByRole('button', { name: /Avvia Scansione Accessibilit/ }).click()
    await expect(page).toHaveURL(/\/scanning/)

    // Attendi che compaia l'intestazione di scanning
    await expect(page.getByRole('heading', { name: /Scansione Accessibilit/ })).toBeVisible()

    // Attendi la transizione al report (flusso reale)
    await page.waitForURL(/\/report/, { timeout: 120000 })
    await expect(page.getByRole('heading', { name: /Report Accessibilit/ })).toBeVisible()
  })
})
