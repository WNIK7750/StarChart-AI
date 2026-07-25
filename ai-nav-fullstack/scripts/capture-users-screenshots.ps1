$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$baseUrl = if ($env:AI_NAV_BASE_URL) { $env:AI_NAV_BASE_URL } else { "http://127.0.0.1:8000" }
$outputDir = Join-Path $root "docs/06-evidence/users/screenshots"
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

$tempDir = Join-Path $env:TEMP ("users-settings-qa-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $tempDir | Out-Null

$spec = @'
const { test, expect, request } = require('@playwright/test');
const fs = require('fs');
const path = require('path');
const baseUrl = process.env.AI_NAV_BASE_URL || '__BASE_URL__';
const outputDir = path.resolve('__OUTPUT_DIR__');

async function createQaUser() {
  const api = await request.newContext({ baseURL: baseUrl });
  const suffix = Date.now().toString(36);
  const response = await api.post('/api/v1/auth/register', {
    data: {
      username: 'qa_settings_' + suffix,
      password: 'QaSettings123',
      email: 'qa_settings_' + suffix + '@example.test',
      displayName: 'QA Settings',
      privacyAccepted: true
    }
  });
  if (!response.ok()) throw new Error(`register failed ${response.status()} ${await response.text()}`);
  const data = await response.json();
  await api.dispose();
  return data;
}

test.describe('settings screenshots', () => {
  let auth;
  const results = [];

  test.beforeAll(async () => {
    fs.mkdirSync(outputDir, { recursive: true });
    auth = await createQaUser();
  });

  test.afterAll(async () => {
    const manifest = {
      baseUrl,
      flow: 'settings load -> desktop avatar/session recovery -> preference consent save -> privacy consent/export/deletion cancellation -> workflow unavailable/archive -> responsive screenshots',
      browserAvailability: 'Opera Browser Connector is available for manual browser QA; this repeatable settings matrix uses Playwright.',
      captures: results,
      passed: results.every((item) => !item.layout.overflowX && item.messages.length === 0 && item.layout.activeSection === 'preferences' && item.layout.saveMessage.length > 0 && item.interactions.savingStateVerified && item.interactions.labelsVerified && item.interactions.ariaCurrentVerified && item.interactions.privacyVerified !== false && item.interactions.workflowVerified !== false && item.interactions.confirmationVerified !== false && item.interactions.retryVerified !== false && item.interactions.avatarUploadVerified !== false && item.interactions.oldAvatarCleanupVerified !== false)
    };
    fs.writeFileSync(path.join(outputDir, 'settings-screenshots-manifest.json'), JSON.stringify(manifest, null, 2));
  });

  for (const item of [
    { name: 'desktop-1440', width: 1440, height: 900 },
    { name: 'tablet-768', width: 768, height: 900 },
    { name: 'mobile-390', width: 390, height: 844 },
    { name: 'mobile-360', width: 360, height: 800 },
  ]) {
    test(item.name, async ({ browser }) => {
      const page = await browser.newPage({ viewport: { width: item.width, height: item.height } });
      const messages = [];
      const expectedMessages = [];
      let failSessions = item.name === 'desktop-1440';
      let retryVerified = item.name === 'desktop-1440' ? false : 'not-run';
      let avatarUploadVerified = item.name === 'desktop-1440' ? false : 'not-run';
      let oldAvatarCleanupVerified = item.name === 'desktop-1440' ? false : 'not-run';
      let confirmationVerified = item.name === 'desktop-1440' ? false : 'not-run';
      let privacyVerified = item.name === 'desktop-1440' ? false : 'not-run';
      let workflowVerified = item.name === 'desktop-1440' ? false : 'not-run';
      page.on('console', (msg) => {
        if (!['error', 'warning'].includes(msg.type())) return;
        const entry = { type: msg.type(), text: msg.text() };
        if (failSessions && msg.text().includes('503')) expectedMessages.push(entry);
        else messages.push(entry);
      });
      page.on('pageerror', (err) => messages.push({ type: 'pageerror', text: err.message }));
      await page.route('**/api/v1/users/me/sessions**', async (route) => {
        if (failSessions) {
          await route.fulfill({ status: 503, contentType: 'application/json', body: JSON.stringify({ detail: { code: 'QA_RETRY', message: 'temporary failure' } }) });
          return;
        }
        await route.continue();
      });
      await page.addInitScript((tokens) => {
        localStorage.setItem('ai_nav_access_token', tokens.accessToken);
        localStorage.setItem('ai_nav_refresh_token', tokens.refreshToken);
      }, auth);
      await page.goto(`${baseUrl}/settings.html#profile`, { waitUntil: 'networkidle' });
      await page.locator('.section.active').waitFor({ state: 'visible', timeout: 10000 });
      if (!await page.locator("[data-section='profile']").evaluate((node) => node.classList.contains('active'))) {
        await page.locator("[data-section-link][href='#profile']").click();
      }
      await page.locator("[data-section='profile'].active [data-profile-form]").waitFor({ state: 'visible', timeout: 10000 });
      if (item.name === 'desktop-1440') {
        const avatarPng = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAIAAAD8GO2jAAAALUlEQVR4nGOUq7jEQEvARFPTRy0YtWDUglELRi0YtWDUglELRi0YtWDUAioCAJqqAaiUJQzQAAAAAElFTkSuQmCC', 'base64');
        await page.locator('[data-avatar-input]').setInputFiles({ name: 'qa-avatar.png', mimeType: 'image/png', buffer: avatarPng });
        await page.locator('[data-crop-panel].open').waitFor({ state: 'visible' });
        await page.locator('[data-crop-confirm]').click();
        await expect(page.locator('[data-avatar-message]')).not.toHaveText('');
        await expect(page.locator('[data-avatar-preview]')).toHaveAttribute('src', /\/uploads\/avatars\/.*\.webp/);
        const firstAvatarUrl = await page.locator('[data-avatar-preview]').getAttribute('src');
        await page.locator('[data-avatar-input]').setInputFiles({ name: 'qa-avatar.png', mimeType: 'image/png', buffer: avatarPng });
        await page.locator('[data-crop-panel].open').waitFor({ state: 'visible' });
        await page.locator('[data-crop-confirm]').click();
        await expect.poll(() => page.locator('[data-avatar-preview]').getAttribute('src')).not.toBe(firstAvatarUrl);
        const oldAvatarResponse = await page.request.get(new URL(firstAvatarUrl, baseUrl).href);
        expect(oldAvatarResponse.status()).toBe(404);
        avatarUploadVerified = true;
        oldAvatarCleanupVerified = true;
        await page.locator("[data-section-link][href='#sessions']").click();
        const retryButton = page.locator("[data-session-list] [data-retry-area='sessions']");
        await retryButton.waitFor({ state: 'visible' });
        failSessions = false;
        await retryButton.click();
        await page.locator('[data-session-list] .session-item').first().waitFor({ state: 'visible' });
        retryVerified = true;
        const revokeOthers = page.locator('[data-revoke-other-sessions]');
        await revokeOthers.click();
        await expect(page.locator('[data-confirm-dialog]')).toBeVisible();
        await expect(page.locator('[data-confirm-accept]')).toBeFocused();
        await page.keyboard.press('Escape');
        await expect(page.locator('[data-confirm-dialog]')).not.toBeVisible();
        await expect(revokeOthers).toBeFocused();
        confirmationVerified = true;
      }
      await page.locator("[data-section-link][href='#preferences']").click();
      await page.locator("[data-section='preferences'].active").waitFor({ state: 'visible', timeout: 5000 });
      const freeFirst = page.locator("[data-preferences-form] [name='freeFirst']");
      await freeFirst.setChecked(!await freeFirst.isChecked());
      let releaseSave;
      let saveRequested = false;
      await page.route('**/api/v1/users/me/preferences', async (route) => {
        if (route.request().method() === 'PATCH') {
          saveRequested = true;
          await new Promise((resolve) => { releaseSave = resolve; });
        }
        await route.continue();
      });
      await page.locator("[data-preferences-form] button[type='submit']").click();
      await expect.poll(() => saveRequested).toBe(true);
      await expect(page.locator('[data-preferences-form]')).toHaveAttribute('aria-busy', 'true');
      await expect(page.locator("[data-preferences-form] button[type='submit']")).toBeDisabled();
      releaseSave();
      await expect(page.locator('[data-preferences-message]')).not.toHaveText('');
      await expect(page.locator('[data-preferences-form]')).toHaveAttribute('aria-busy', 'false');
      await page.unroute('**/api/v1/users/me/preferences');
      if (item.name === 'desktop-1440') {
        await page.locator("[data-section-link][href='#privacy']").click();
        const privacyPolicy = page.locator("[data-privacy-consent-form] [name='privacyPolicy']");
        await privacyPolicy.setChecked(!await privacyPolicy.isChecked());
        await expect(page.locator('[data-privacy-consent-message]')).toContainText('\u5df2\u4fdd\u5b58');

        const privacyLifecycle = await page.evaluate(async () => {
          const token = localStorage.getItem('ai_nav_access_token');
          const headers = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' };
          const exported = await fetch('/api/v1/users/me/privacy/export', {
            method: 'POST', headers, body: JSON.stringify({ currentPassword: 'QaSettings123' }),
          });
          const exportBody = await exported.json();
          const deletion = await fetch('/api/v1/users/me/privacy/deletion-requests', {
            method: 'POST', headers, body: JSON.stringify({ currentPassword: 'QaSettings123', reasonCode: 'other' }),
          });
          const deletionBody = await deletion.json();
          const cancelled = await fetch(`/api/v1/users/me/privacy/deletion-requests/${deletionBody.request?.requestUid}`, {
            method: 'DELETE', headers,
          });
          return {
            exportStatus: exported.status,
            exportBody,
            deletionStatus: deletion.status,
            cancelStatus: cancelled.status,
          };
        });
        expect(privacyLifecycle.exportStatus).toBe(200);
        expect(privacyLifecycle.deletionStatus).toBe(201);
        expect(privacyLifecycle.cancelStatus).toBe(200);
        const exportText = JSON.stringify(privacyLifecycle.exportBody);
        expect(exportText).toContain('"formatVersion":1');
        expect(exportText).not.toContain('password_hash');
        expect(exportText).not.toContain('refresh_token_hash');
        expect(exportText).not.toContain('answer_hash');
        privacyVerified = true;

        const workflowResult = await page.evaluate(async (payload) => {
          const response = await fetch('/api/v1/users/me/assets/workflows', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${localStorage.getItem('ai_nav_access_token')}`,
              'Content-Type': 'application/json',
              'Idempotency-Key': `settings-workflow-${Date.now()}`,
            },
            body: JSON.stringify(payload),
          });
          return { ok: response.ok, status: response.status, body: await response.json() };
        }, {
            confirmed: true,
            sourceType: 'manual',
            title: 'QA Saved Workflow',
            description: 'Verify retired target retention and archive interaction',
            steps: [{ order: 1, name: 'Retired QA Tool', objective: 'Verify unavailable state', toolSlug: 'retired-qa-tool' }],
        });
        expect(workflowResult.ok, JSON.stringify(workflowResult)).toBeTruthy();
        await page.reload({ waitUntil: 'networkidle' });
        await page.locator('.section.active').waitFor({ state: 'visible', timeout: 10000 });
        await page.locator("[data-section-link][href='#workflows']").click();
        const workflowBox = page.locator('[data-workflows-box]');
        await expect(workflowBox).toContainText('QA Saved Workflow');
        await expect(workflowBox).toContainText('\u90e8\u5206\u5de5\u5177\u4e0d\u53ef\u7528');
        await workflowBox.locator('[data-archive-workflow]').click();
        await expect(page.locator('[data-confirm-dialog]')).toBeVisible();
        await page.locator('[data-confirm-accept]').click();
        await expect(workflowBox).toContainText('\u6682\u65e0\u5df2\u4fdd\u5b58\u5de5\u4f5c\u6d41');
        workflowVerified = true;
        await page.locator("[data-section-link][href='#preferences']").click();
        await page.locator("[data-section='preferences'].active").waitFor({ state: 'visible' });
        const refreshedFreeFirst = page.locator("[data-preferences-form] [name='freeFirst']");
        await refreshedFreeFirst.setChecked(!await refreshedFreeFirst.isChecked());
        await page.locator("[data-preferences-form] button[type='submit']").click();
        await expect(page.locator('[data-preferences-message]')).not.toHaveText('');
      }
      const labelsVerified = await page.evaluate(() => Array.from(document.querySelectorAll('.field > label')).every((label) => {
        const id = label.getAttribute('for');
        return Boolean(id && document.getElementById(id));
      }));
      const ariaCurrentVerified = await page.locator("[data-section-link][href='#preferences']").getAttribute('aria-current') === 'page';
      const layout = await page.evaluate(() => ({
        bodyScrollWidth: document.body.scrollWidth,
        bodyClientWidth: document.documentElement.clientWidth,
        documentScrollWidth: document.documentElement.scrollWidth,
        overflowX: Math.max(document.body.scrollWidth, document.documentElement.scrollWidth) > document.documentElement.clientWidth + 1,
        activeSection: document.querySelector('.section.active')?.getAttribute('data-section'),
        visibleText: document.body.innerText.slice(0, 500),
        saveMessage: document.querySelector('[data-preferences-message]')?.textContent || ''
      }));
      const identity = { url: page.url(), title: await page.title() };
      const screenshotPath = path.join(outputDir, `settings-${item.name}.png`);
      await page.screenshot({ path: screenshotPath, fullPage: false });
      const result = {
        name: item.name,
        viewport: { width: item.width, height: item.height },
        identity,
        layout,
        interactions: { retryVerified, avatarUploadVerified, oldAvatarCleanupVerified, confirmationVerified, privacyVerified, workflowVerified, labelsVerified, ariaCurrentVerified, savingStateVerified: true, expectedNetworkErrors: expectedMessages.length },
        messages,
        screenshotPath
      };
      results.push(result);
      fs.writeFileSync(path.join(outputDir, `settings-${item.name}.json`), JSON.stringify(result, null, 2));
      expect(identity.title).toContain('AI');
      expect(layout.activeSection).toBe('preferences');
      expect(layout.overflowX).toBeFalsy();
      expect(layout.saveMessage.length).toBeGreaterThan(0);
      expect(labelsVerified).toBeTruthy();
      expect(ariaCurrentVerified).toBeTruthy();
      expect(messages).toEqual([]);
      await page.close();
    });
  }
});
'@
$spec = $spec.Replace("__BASE_URL__", $baseUrl).Replace("__OUTPUT_DIR__", $outputDir.Replace("\", "/"))
$spec | Set-Content -Encoding UTF8 -Path (Join-Path $tempDir "settings.spec.js")

Push-Location $tempDir
try {
  npm init -y | Out-Null
  npm install @playwright/test --no-audit --no-fund | Out-Null
  npx playwright test settings.spec.js --browser=chromium --reporter=line
  if ($LASTEXITCODE -ne 0) { throw "Settings screenshot capture failed." }
} finally {
  Pop-Location
}
