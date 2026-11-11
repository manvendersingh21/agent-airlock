import { chromium } from '@playwright/test';
import { mkdirSync, existsSync } from 'fs';
import { join } from 'path';

async function main() {
  const recordingsDir = join(process.cwd(), 'recordings');
  if (!existsSync(recordingsDir)) {
    mkdirSync(recordingsDir, { recursive: true });
  }

  console.log('Launching browser to record video...');
  const browser = await chromium.launch({
    headless: true,
  });

  const context = await browser.newContext({
    recordVideo: {
      dir: recordingsDir,
      size: { width: 1280, height: 720 },
    },
    viewport: { width: 1280, height: 720 },
    deviceScaleFactor: 2,
  });

  // Inject visual cursor for recording
  await context.addInitScript(() => {
    window.addEventListener('DOMContentLoaded', () => {
      const cursor = document.createElement('div');
      cursor.id = 'playwright-mouse-pointer';
      cursor.style.width = '18px';
      cursor.style.height = '18px';
      cursor.style.border = '2px solid #0f172a';
      cursor.style.borderRadius = '50%';
      cursor.style.background = 'rgba(15, 23, 42, 0.45)';
      cursor.style.position = 'fixed';
      cursor.style.pointerEvents = 'none';
      cursor.style.zIndex = '999999';
      cursor.style.transition = 'transform 0.08s ease-out, background 0.15s ease';
      cursor.style.transform = 'translate(-50%, -50%)';
      document.body.appendChild(cursor);

      window.addEventListener('mousemove', (e) => {
        cursor.style.left = e.clientX + 'px';
        cursor.style.top = e.clientY + 'px';
      });
      window.addEventListener('mousedown', () => {
        cursor.style.background = 'rgba(5, 150, 105, 0.85)';
        cursor.style.transform = 'translate(-50%, -50%) scale(0.85)';
      });
      window.addEventListener('mouseup', () => {
        cursor.style.background = 'rgba(15, 23, 42, 0.45)';
        cursor.style.transform = 'translate(-50%, -50%) scale(1)';
      });
    });
  });

  const page = await context.newPage();

  page.on('console', (msg) => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', (err) => console.log('PAGE ERR:', err.message));

  async function moveAndClick(selector, delayAfter = 1000) {
    const el = page.locator(selector).first();
    await el.waitFor({ state: 'visible', timeout: 10000 });
    await el.scrollIntoViewIfNeeded();
    await page.waitForTimeout(200);
    const box = await el.boundingBox();
    if (box) {
      const targetX = box.x + box.width / 2;
      const targetY = box.y + box.height / 2;
      await page.mouse.move(targetX, targetY, { steps: 15 });
      await page.waitForTimeout(200);
      await page.mouse.down();
      await page.waitForTimeout(120);
      await page.mouse.up();
    } else {
      await el.click();
    }
    await page.waitForTimeout(delayAfter);
  }

  async function smoothScroll(targetY, duration = 800) {
    await page.evaluate(async ({ targetY, duration }) => {
      const startY = window.scrollY;
      const diff = targetY - startY;
      const startTime = performance.now();
      return new Promise((resolve) => {
        function step(now) {
          const elapsed = now - startTime;
          const progress = Math.min(elapsed / duration, 1);
          const ease = progress < 0.5 ? 2 * progress * progress : -1 + (4 - 2 * progress) * progress;
          window.scrollTo(0, startY + diff * ease);
          if (progress < 1) requestAnimationFrame(step);
          else resolve();
        }
        requestAnimationFrame(step);
      });
    }, { targetY, duration });
    await page.waitForTimeout(300);
  }

  console.log('Navigating to http://127.0.0.1:8000...');
  await page.goto('http://127.0.0.1:8000/');
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(2500);

  // 1. Scenario 1: Poisoned Document
  console.log('Demonstrating Scenario 1: Poisoned Document...');
  await moveAndClick('.scenario-card.category-injection');
  await page.waitForTimeout(1000);
  await moveAndClick('button:has-text("Run comparison")');
  console.log('Waiting for Clocked Guard to screen...');
  await page.waitForSelector('.protected-card.result-block, .protected-card.result-allow, .protected-card.result-hold', { timeout: 15000 });
  await page.waitForTimeout(3000);

  // Scroll down to show Live Outbox
  console.log('Scrolling to Live Environment State...');
  await smoothScroll(650, 700);
  await page.waitForTimeout(3000);
  await smoothScroll(0, 600);
  await page.waitForTimeout(1000);

  // 2. Scenario 2: Privacy Leak
  console.log('Demonstrating Scenario 2: Privacy Leak...');
  await moveAndClick('.scenario-card.category-privacy');
  await page.waitForTimeout(1000);
  await moveAndClick('button:has-text("Run comparison")');
  console.log('Waiting for Clocked Protect to screen...');
  await page.waitForSelector('.protected-card.result-redact', { timeout: 15000 });
  await page.waitForTimeout(2000);
  // Click Agent received tab to show redaction tokens
  await moveAndClick('button:has-text("Agent received")');
  await page.waitForTimeout(3000);

  // 3. Scenario 3: Legitimate Diagnostic
  console.log('Demonstrating Scenario 3: Legitimate Diagnostic...');
  await moveAndClick('.scenario-card.category-benign');
  await page.waitForTimeout(1000);
  await moveAndClick('button:has-text("Run comparison")');
  await page.waitForSelector('.protected-card.result-allow', { timeout: 15000 });
  await page.waitForTimeout(3000);

  // 4. Interactive Attack Sandbox
  console.log('Demonstrating Interactive Attack Sandbox...');
  await page.locator('.interactive-sandbox-section').scrollIntoViewIfNeeded();
  await page.waitForTimeout(1500);

  // Click DAN Jailbreak preset
  console.log('Testing DAN Jailbreak preset...');
  await moveAndClick('.preset-chip:has-text("DAN / Developer Mode Jailbreak")');
  await page.waitForTimeout(800);
  await moveAndClick('.sandbox-actions button:has-text("Screen & Enforce")');
  await page.waitForSelector('.sandbox-verdict-body', { timeout: 15000 });
  await page.waitForTimeout(3500);

  // Click Support Ticket PII Exposure preset
  console.log('Testing Support Ticket PII Exposure preset...');
  await moveAndClick('.preset-chip:has-text("Support Ticket PII Exposure")');
  await page.waitForTimeout(800);
  await moveAndClick('.sandbox-actions button:has-text("Screen & Enforce")');
  await page.waitForSelector('.redaction-diff-box', { timeout: 15000 });
  await page.waitForTimeout(3500);

  // Scroll down to Drop-in Proxy Quickstart
  console.log('Showing Drop-in OpenAI Proxy Quickstart...');
  await page.locator('.proxy-quickstart-panel').scrollIntoViewIfNeeded();
  await page.waitForTimeout(2000);
  await moveAndClick('.proxy-quickstart-panel button:has-text("cURL")');
  await page.waitForTimeout(1500);
  await moveAndClick('.proxy-quickstart-panel button:has-text("Python SDK")');
  await page.waitForTimeout(1500);
  await moveAndClick('.proxy-quickstart-panel button:has-text("Copy code")');
  await page.waitForTimeout(1500);

  // 5. Sidebar Navigation
  console.log('Showing Policies view...');
  await smoothScroll(0, 600);
  await moveAndClick('nav a:has-text("Policies")');
  await page.waitForTimeout(2500);

  console.log('Showing Event Stream view...');
  await moveAndClick('nav a:has-text("Event Stream")');
  await page.waitForTimeout(2500);

  console.log('Showing Investigations view...');
  await moveAndClick('nav a:has-text("Investigations")');
  await page.waitForTimeout(2500);

  console.log('Returning to Attack Lab...');
  await moveAndClick('nav a:has-text("Attack Lab")');
  await page.waitForTimeout(2500);

  // Close context to save video
  console.log('Finalizing video recording...');
  const videoPath = await page.video()?.path();
  await context.close();
  await browser.close();

  console.log('Video saved to:', videoPath);
}

main().catch((err) => {
  console.error('Recording failed:', err);
  process.exit(1);
});
