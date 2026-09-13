import { test, expect } from '@playwright/test';

test('renders only the selected run and keeps unavailable surfaces honest', async ({ page }) => {
  const project = { id: 'lab', name: 'Laboratory examples', site_key: 'laboratory-examples', synthetic: true, verified_bounds_wgs84: null };
  const run = {
    id: 'run-a', state: 'SUCCEEDED',
    input: { request: { engine: 'dflowfm', case_kind: 'OFFICIAL_EXAMPLE' } },
    result: { normalization: { frames: 2, cells: 2, duration_seconds: 10 } },
  };
  await page.route('**/api/projects', async (route) => route.fulfill({ json: [project] }));
  await page.route('**/api/health', async (route) => route.fulfill({ json: { database: 'sqlite', preview: true, engines: [{ engine: 'dflowfm', available: true }] } }));
  await page.route('**/api/projects/lab/datasets', async (route) => route.fulfill({ json: [] }));
  await page.route('**/api/projects/lab/scenarios', async (route) => route.fulfill({ json: [] }));
  await page.route('**/api/projects/lab/readiness', async (route) => route.fulfill({ json: { missing: [], warnings: [] } }));
  await page.route('**/api/projects/lab/jobs', async (route) => route.fulfill({ json: [] }));
  await page.route('**/api/projects/lab/runs', async (route) => route.fulfill({ json: [run] }));
  await page.route('**/api/projects/lab/runs/run-a/results/metadata', async (route) => route.fulfill({
    json: { run_id: 'run-a', source_run_id: 'run-a', cached: false, engine: 'dflowfm', model_version: 'fixture',
      case_kind: 'OFFICIAL_EXAMPLE', input_mode: 'SYNTHETIC', execution_origin: 'LOCAL', units: { h: 'm', u: 'm/s' },
      crs: 'EPSG:32643', vertical_datum: null, nodata_value: { floating: 'NaN', wet: -1, valid: 0 },
      source_time_units: null, source_local_time: null, start_time: null, simulation_elapsed_seconds: [0, 10],
      output_frame_count: 2, cell_count: 2, wet_threshold_m: 0.01, arrival_precision: 'saved frame', cell_semantics: 'fixture' },
  }));
  await page.route('**/api/projects/lab/runs/run-a/results/window**', async (route) => route.fulfill({
    json: { state: 'AVAILABLE', cells: [{ cell: 0, x: 0, y: 0, area_m2: 1 }, { cell: 1, x: 1, y: 1, area_m2: 1 }],
      frames: [{ frame: 0, elapsed_s: 0, values: [0.2, null], states: ['WET', 'NODATA'] }] },
  }));
  await page.route('**/api/projects/lab/runs/run-a/products/area**', async (route) => route.fulfill({
    json: { baseline_water: 'none defined', threshold_m: 0.1, area_semantics: 'known flooded area', frames: [{ frame: 0, elapsed_s: 0, flooded_area_m2: 1, unknown_area_m2: 1 }] },
  }));
  await page.route('**/api/projects/lab/runs/run-a/products/location**', async (route) => route.fulfill({
    json: { state: 'AVAILABLE', name: 'Nearest saved cell', arrival_elapsed_s: 0, series: [] },
  }));

  await page.goto('/');
  await page.getByRole('button', { name: 'Numerical runs' }).click();
  await page.getByRole('button', { name: 'Explore results' }).click();
  await expect(page.getByText('SYNTHETIC · OFFICIAL_EXAMPLE')).toBeVisible();
  await expect(page.getByText('0.200 m')).toBeVisible();
  await page.getByRole('button', { name: 'Exposure' }).click();
  await expect(page.getByText('Exposure overlays unavailable')).toBeVisible();
  await page.getByRole('button', { name: 'Exports' }).click();
  await expect(page.getByText('Exports available after processing')).toBeVisible();
});
