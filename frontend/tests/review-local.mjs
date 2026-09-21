// Real local API/browser smoke review. No API mocks and no solver submissions.
import { chromium, expect } from '@playwright/test';
import { spawn } from 'node:child_process';
import { mkdir } from 'node:fs/promises';
import { resolve } from 'node:path';
const root = resolve('..');
const port = 8019;
const server = spawn(resolve(root, '.venv/Scripts/python.exe'), ['-m', 'uvicorn', 'damsafe.api:create_app', '--factory', '--host', '127.0.0.1', '--port', String(port)], {
  cwd: root, env: { ...process.env, DAMSAFE_DATABASE_URL: `sqlite:///${root.replaceAll('\\', '/')}/.local/damsafe.db`, DAMSAFE_STORAGE_ROOT: resolve(root, '.local/objects') }, stdio: 'ignore',
});
let browser;
try {
  let ready = false;
  for (let i = 0; i < 60; i++) {
    try { if ((await fetch(`http://127.0.0.1:${port}/api/health`)).ok) { ready = true; break; } } catch {}
    await new Promise(r => setTimeout(r, 500));
  }
  if (!ready) throw new Error('Local API did not become ready');
  browser = await chromium.launch({ channel: 'msedge', headless: true });
  const page = await browser.newPage({ viewport: { width: 1366, height: 768 } });
  const errors = [];
  page.on('pageerror', e => { errors.push(String(e)); console.error(String(e)); });
  await page.goto(`http://127.0.0.1:${port}`, { waitUntil: 'domcontentloaded' });
  await page.waitForSelector('#page-dashboard');
  const output = resolve(root, '.local/ui-review');
  await mkdir(output, { recursive: true });
  for (const [id, label] of [['dashboard','Dashboard'],['study-area','Study Area'],['data-setup','Data Setup'],['scenario-builder','Scenario Builder'],['simulation','Simulation'],['results','Results'],['validation','Validation'],['impact','Impact & HADR'],['reports','Reports & Export']]) {
    await page.locator('.sidebar .nav-item').filter({ hasText: label }).click();
    await page.waitForSelector(`#page-${id}`, { timeout: 10000 });
    await page.waitForTimeout(700);
    await page.screenshot({ path: resolve(output, `${id}.png`), fullPage: true });
    console.log(`PASS ${label}`);
  }
  await page.locator('#nav-dashboard').click();
  await expect(page.locator('.stat-grid')).toContainText(/\d+\.\d+ m/);
  await page.locator('#nav-results').click();
  await expect(page.locator('#results-timeline-slider')).toBeVisible();
  await page.locator('#results-timeline-slider').fill('40');
  await expect(page.locator('.timeline-time')).toContainText('Frame 40 /');
  await page.locator('#field-btn-velocity').click();
  await expect(page.locator('.stat-grid')).toContainText('m/s');
  await page.locator('#field-btn-depth').click();
  await expect(page.locator('.timeline-time')).toContainText('Frame 40 /');
  await page.locator('#results-tab-terrain3d').click();
  await expect(page.locator('canvas[aria-label="Native river mesh and saved water surface"]')).toBeVisible();
  await page.screenshot({ path: resolve(output, 'river-3d.png'), fullPage: true });
  await page.locator('#results-tab-sph3d').click();
  await expect(page.locator('canvas[aria-label="Saved DualSPHysics particles"]')).toBeVisible();
  await page.getByRole('slider', { name: 'SPH frame' }).fill('100');
  await expect(page.locator('.sph-viewer .metric-grid')).toContainText('1.000 s');
  await page.screenshot({ path: resolve(output, 'sph-3d.png'), fullPage: true });
  await page.locator('.sph-viewer').getByRole('button', { name: 'Play', exact: true }).click();
  await expect(page.getByRole('slider', { name: 'SPH frame' })).not.toHaveValue('100');
  await page.locator('.sph-viewer').getByRole('button', { name: 'Pause', exact: true }).click();
  console.log('PASS numeric dashboard, frame 40 batch, field switch, native 3D mesh, SPH seek and playback');
  const projects = await (await fetch(`http://127.0.0.1:${port}/api/projects`)).json();
  for (const project of projects) {
    const runs = await (await fetch(`http://127.0.0.1:${port}/api/projects/${project.id}/runs`)).json();
    const run = runs.find(r => r.id === 'a8bacdd4-490c-4961-a8c1-a3a2d4e3874b');
    if (!run) continue;
    const base = `http://127.0.0.1:${port}/api/projects/${project.id}/runs/${run.id}`;
    const result = await (await fetch(`${base}/results/window?bbox=-1000000000,-1000000000,1000000000,1000000000&frame_count=1`)).json();
    if (!result.cells?.every(c => c.polygon?.length >= 4)) throw new Error('Native cell polygons missing');
    console.log(`PASS real Ujjani result: ${result.cells.length} native polygons`);
    for (const format of ['geojson', 'shapefile', 'kml', 'geotiff', 'csv', 'html']) {
      const response = await fetch(`${base}/exports/${format}`, { method: 'POST' });
      if (!response.ok || (await response.arrayBuffer()).byteLength === 0) throw new Error(`Export failed: ${format}`);
      console.log(`PASS real export ${format}`);
    }
  }
  if (errors.length) throw new Error(errors.join('\n'));
  console.log(`Screenshots: ${output}`);
} finally { await browser?.close(); server.kill(); }
