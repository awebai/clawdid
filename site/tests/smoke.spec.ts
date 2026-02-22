import { test, expect } from '@playwright/test'

test('home renders', async ({ page }) => {
  await page.goto('/')
  await expect(page.getByRole('heading', { name: 'ClawDID' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'GitHub' })).toBeVisible()
})

test('docs landing renders with navigation table', async ({ page }) => {
  await page.goto('/docs/')
  await expect(page.getByRole('heading', { name: 'Docs', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: 'What is ClawDID?' })).toBeVisible()
  await expect(page.getByRole('link', { name: 'Identity Architecture' })).toBeVisible()
  await expect(page.getByRole('table').getByRole('link', { name: 'Trust Model' })).toBeVisible()
})

const docPages = [
  { path: '/docs/overview/', title: 'What is ClawDID?' },
  { path: '/docs/architecture/', title: 'Identity Architecture' },
  { path: '/docs/message-signing/', title: 'Message Signing and Verification' },
  { path: '/docs/clawdid-service/', title: 'ClawDID Service' },
  { path: '/docs/identity-lifecycle/', title: 'Identity Lifecycle' },
  { path: '/docs/trust-model/', title: 'Trust Model' },
  { path: '/docs/open-questions/', title: 'Open Questions' },
]

for (const { path, title } of docPages) {
  test(`docs page renders: ${title}`, async ({ page }) => {
    await page.goto(path)
    await expect(page.getByRole('heading', { name: title })).toBeVisible()
    // Sidebar navigation present
    await expect(page.locator('.docs-sidebar')).toBeVisible()
  })
}

test('docs sidebar highlights active page', async ({ page }) => {
  await page.goto('/docs/architecture/')
  await expect(page.locator('.docs-sidebar li.active a')).toHaveText('Identity Architecture')
})

test('docs prev/next navigation works', async ({ page }) => {
  await page.goto('/docs/architecture/')
  await expect(page.locator('.docs-prev')).toBeVisible()
  await expect(page.locator('.docs-next')).toBeVisible()
})
