import { test, expect } from '@playwright/test';

test.describe('Agent Airlock Console', () => {
  test('renders the attack lab with live status and scenarios', async ({ page }) => {
    await page.goto('/');

    // Check title and header
    await expect(page.locator('h1')).toHaveText('Attack Lab');
    await expect(page.locator('.live-checks-tag')).toContainText('LIVE CLOCKED INTEGRATION');

    // Check scenarios are listed
    await expect(page.locator('.scenario-card')).toHaveCount(4);
    await expect(page.locator('.scenario-card').first()).toContainText('Poisoned document');
    await expect(page.locator('.failure-button')).toContainText('Test an outage');
  });

  test('navigates between console views', async ({ page }) => {
    await page.goto('/');

    // Navigate to Policies
    await page.click('nav a:has-text("Policies")');
    await expect(page).toHaveURL(/\/policies/);
    await expect(page.locator('h1')).toHaveText('Enforcement policies');

    // Navigate to Event Stream
    await page.click('nav a:has-text("Event Stream")');
    await expect(page).toHaveURL(/\/events/);
    await expect(page.locator('h1')).toHaveText('Event Stream');

    // Navigate to Investigations
    await page.click('nav a:has-text("Investigations")');
    await expect(page).toHaveURL(/\/investigations/);
    await expect(page.locator('h1')).toHaveText('Investigations');
  });

  test('runs failure drill and observes fail-closed HOLD decision', async ({ page }) => {
    await page.goto('/');

    // Click outage failure drill
    await page.click('.failure-button');
    await expect(page.locator('.workbench-title h2')).toContainText('Security unavailable');

    // Click Run comparison
    await page.click('button:has-text("Run comparison")');

    // Verify baseline and protected results
    await expect(page.locator('.protected-card')).toContainText('Security check unavailable', { timeout: 15000 });
    await expect(page.locator('.protected-card .status-badge')).toContainText('Held');
    await expect(page.locator('.baseline-card .status-badge')).toContainText('Simulation');

    // Verify timeline shows trace events
    await expect(page.locator('.trace-panel')).toBeVisible();
    await expect(page.locator('.timeline-list')).toContainText('Failure drill enabled');
  });
});
