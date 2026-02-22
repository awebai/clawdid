import { test, expect } from '@playwright/test'

test('home renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'ClaWDID' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Open-source' })).toBeVisible()
})

