import React, { useEffect, useMemo, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import type { Map as LibreMap } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import './style.css';

type Project = {
  id: string; name: string; site_key: string; synthetic: boolean;
  description?: string; verified_bounds_wgs84: [number, number, number, number] | null;
};
type Dataset = {
  id: string; name: string; kind: string; version: number; sha256: string;
  provenance: { status: string; units: string; agency?: string; acquisition_date?: string | null };
  inspection: { issues: { code: string; message: string }[] };
};
type Finding = { code: string; message: string };
type Readiness = { missing: Finding[]; warnings: Finding[] };
type Scenario = { id: string; name: string; sha256: string; snapshot: { input_mode: string } };
type Job = { id: string; state: string; body: { result?: Readiness } };
type Engine = { engine: 'dflowfm' | 'dualsphysics'; available: boolean; reason?: string; image_id?: string };
type NumericalRun = {
  id: string; state: string; input: { request: { engine: string; case_kind: string }; evidence_status?: string };
  result: { error?: string; reason?: string; progress?: { stage?: string; elapsed_seconds?: number; cells_done?: number; cells_total?: number; frame?: number; frames_total?: number }; normalization?: { frames: number; cells: number; duration_seconds: number } };
};
type ResultMetadata = {
  run_id: string; source_run_id: string; cached: boolean; engine: string | null; model_version: string | null;
  case_kind: string; input_mode: string; execution_origin: string; units: Record<string, string | null>;
  crs: string | null; vertical_datum: string | null; nodata_value: { floating: string; wet: number; valid: number };
  source_time_units: string | null; source_local_time: string | null; start_time: string | null;
  simulation_elapsed_seconds: [number, number]; output_frame_count: number; cell_count: number;
  wet_threshold_m: number; arrival_precision: string; cell_semantics: string; nodata_encoding: string;
};
type Window = {
  state: string; field?: string; cells: { cell: number; x: number; y: number; area_m2: number }[];
  frames: { frame: number; elapsed_s: number; values: (number | null)[]; states: ('WET' | 'DRY' | 'NODATA')[] }[];
};
type ProductArea = {
  baseline_water: string; threshold_m: number; area_semantics: string;
  frames: { frame: number; elapsed_s: number; flooded_area_m2: number; unknown_area_m2: number }[];
};
type LocationSeries = {
  state: string; name?: string; cell?: number; x?: number; y?: number; arrival_elapsed_s?: number | null;
  series: { frame: number; elapsed_s: number; depth_m: number | null; state: string }[];
};
type Ensemble = { id: string; name: string; status: string; run_ids: string[]; frequency_semantics: string };

async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, init);
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data as T;
}

const metadataTemplate = {
  name: '', kind: 'hydrology',
  provenance: {
    source_url: '', agency: '', licence: '', acquisition_date: null,
    acquisition_date_note: 'Acquisition period must be verified from source',
    units: 'm3/s', crs: null, vertical_reference: null, processing_history: [],
    status: 'observed', synthetic: false,
  },
  hydro: {
    station_id: '', source_timezone: null, measurement: 'unknown',
    identity_reference: null, interval_seconds: 3600,
  },
};
const scenarioTemplate = {
  name: 'Hypothetical release scenario',
  forcing: { mode: 'prescribed_release', historical: false, hydrograph_dataset_id: null },
  dataset_ids: [], start_time: '2025-01-01T00:00:00+05:30', end_time: '2025-01-02T00:00:00+05:30',
  time_step_seconds: 1, output_interval_seconds: 60, wet_threshold_m: 0.01, arrival_threshold_m: 0.1,
  initial_river_state: null, downstream_boundary: null, tributary_inflows: null,
  structure_treatment: null, roughness: null, assumptions: ['Scenario is hypothetical until evidence is verified'],
};
const allCells = '-1000000000,-1000000000,1000000000,1000000000';

function DomainMap({ project }: { project: Project }) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!container.current || !project.verified_bounds_wgs84) return;
    const [w, s, e, n] = project.verified_bounds_wgs84;
    let map: LibreMap | undefined;
    let disposed = false;
    import('maplibre-gl').then((lib) => {
      if (disposed || !container.current) return;
      const instance = new lib.Map({
        container: container.current,
        style: { version: 8, sources: {}, layers: [{ id: 'background', type: 'background', paint: { 'background-color': '#e1eeeb' } }] },
        bounds: [[w, s], [e, n]], fitBoundsOptions: { padding: 40 },
      });
      map = instance;
      instance.on('load', () => {
        instance.addSource('domain', {
          type: 'geojson',
          data: { type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]] } },
        });
        instance.addLayer({ id: 'domain', type: 'line', source: 'domain', paint: { 'line-color': '#128477', 'line-width': 3 } });
      });
      instance.addControl(new lib.NavigationControl());
    });
    return () => { disposed = true; map?.remove(); };
  }, [project]);
  return (
    <div className="domain" ref={container}>
      {!project.verified_bounds_wgs84 && <div className="domain-empty">
        <span className="crosshair">⌖</span><h3>A domain starts with evidence.</h3>
        <p>The downstream reach is awaiting terrain, structure and station review. No flood or study boundary has been drawn.</p>
        <span className="tag">DOMAIN NOT VERIFIED</span>
      </div>}
    </div>
  );
}

function StatusPill({ value }: { value: string }) {
  return <span className={`status status-${value.toLowerCase()}`}>{value}</span>;
}

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selected, setSelected] = useState('');
  const [tab, setTab] = useState('Overview');
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [runs, setRuns] = useState<NumericalRun[]>([]);
  const [health, setHealth] = useState<{ database: string; preview: boolean; engines: Engine[] } | null>(null);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [engineChoice, setEngineChoice] = useState<'dualsphysics' | 'dflowfm'>('dualsphysics');
  const [metadata, setMetadata] = useState(JSON.stringify(metadataTemplate, null, 2));
  const [scenario, setScenario] = useState(JSON.stringify(scenarioTemplate, null, 2));
  const [file, setFile] = useState<File | null>(null);
  const [selectedRun, setSelectedRun] = useState('');
  const [resultMeta, setResultMeta] = useState<ResultMetadata | null>(null);
  const [resultWindow, setResultWindow] = useState<Window | null>(null);
  const [area, setArea] = useState<ProductArea | null>(null);
  const [location, setLocation] = useState<LocationSeries | null>(null);
  const [otherRun, setOtherRun] = useState('');
  const [comparison, setComparison] = useState<Record<string, unknown> | null>(null);
  const [ensembles, setEnsembles] = useState<Ensemble[]>([]);
  const [ensembleName, setEnsembleName] = useState('Sensitivity ensemble');
  const [ensembleVariants, setEnsembleVariants] = useState(JSON.stringify([
    { engine: 'dualsphysics', case_kind: 'OFFICIAL_EXAMPLE', idempotency_key: 'ensemble-variant-01', particle_spacing_m: 0.01 },
    { engine: 'dualsphysics', case_kind: 'OFFICIAL_EXAMPLE', idempotency_key: 'ensemble-variant-02', particle_spacing_m: 0.02 },
  ], null, 2));
  const [ensembleSummary, setEnsembleSummary] = useState<Record<string, unknown> | null>(null);
  const [obsResult, setObsResult] = useState<Record<string, unknown> | null>(null);
  const [satelliteComp, setSatelliteComp] = useState<Record<string, unknown> | null>(null);
  const [gaugeComp, setGaugeComp] = useState<Record<string, unknown> | null>(null);
  const [exposureData, setExposureData] = useState<Record<string, unknown> | null>(null);
  const [obsMode, setObsMode] = useState<'HISTORICAL_EVENT' | 'LATEST_AVAILABLE'>('HISTORICAL_EVENT');
  const project = projects.find((item) => item.id === selected);

  async function refresh(id = selected) {
    if (!id) return;
    const [d, s, r, j, n] = await Promise.all([
      api<Dataset[]>(`/projects/${id}/datasets`), api<Scenario[]>(`/projects/${id}/scenarios`),
      api<Readiness>(`/projects/${id}/readiness`), api<Job[]>(`/projects/${id}/jobs`),
      api<NumericalRun[]>(`/projects/${id}/runs`),
    ]);
    setDatasets(d); setScenarios(s); setReadiness(r); setJobs(j); setRuns(n);
    setEnsembles(await api<Ensemble[]>(`/projects/${id}/ensembles`).catch(() => []));
  }
  async function act(fn: () => Promise<void>) {
    setBusy(true); setError(''); setNotice('');
    try { await fn(); } catch (e) { setError(String(e)); } finally { setBusy(false); }
  }
  useEffect(() => {
    Promise.all([api<Project[]>('/projects'), api<{ database: string; preview: boolean; engines: Engine[] }>('/health')])
      .then(([p, h]) => { setProjects(p); setSelected(p[0]?.id ?? ''); setHealth(h); })
      .catch((e) => setError(String(e)));
  }, []);
  useEffect(() => { refresh(selected).catch((e) => setError(String(e))); }, [selected]);
  useEffect(() => {
    if (!jobs.some((j) => ['QUEUED', 'RUNNING'].includes(j.state)) && !runs.some((r) => ['QUEUED', 'RUNNING'].includes(r.state))) return;
    const timer = setInterval(() => refresh().catch((e) => setError(String(e))), 1500);
    return () => clearInterval(timer);
  }, [jobs, runs, selected]);

  async function upload() {
    if (!file) throw new Error('Choose a data file first');
    JSON.parse(metadata);
    await api(`/projects/${selected}/datasets?filename=${encodeURIComponent(file.name)}&metadata_json=${encodeURIComponent(metadata)}`, {
      method: 'POST', headers: { 'Content-Type': 'application/octet-stream' }, body: file,
    });
    await refresh(); setNotice('Source saved as a new immutable version. Review its findings before modelling.');
  }
  async function saveScenario() {
    const body = JSON.parse(scenario);
    await api(`/projects/${selected}/scenarios`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    await refresh(); setNotice('Hypothetical scenario snapshot saved. Missing inputs remain visible in its audit.');
  }
  async function runAudit() {
    await api(`/projects/${selected}/readiness-jobs`, { method: 'POST' });
    await refresh(); setNotice('Readiness audit queued. It does not run a hydraulic solver.');
  }
  async function openLaboratory() {
    const existing = projects.find((p) => p.synthetic && p.site_key === 'laboratory-examples');
    if (existing) { setSelected(existing.id); return; }
    const created = await api<Project>('/projects', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'DamSafe laboratory examples', site_key: 'laboratory-examples', synthetic: true, description: 'Official engine examples only; no Ujjani predictions' }),
    });
    setProjects((old) => [...old, created]); setSelected(created.id);
  }
  async function submitNumerical() {
    await api(`/projects/${selected}/runs`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ engine: engineChoice, case_kind: 'OFFICIAL_EXAMPLE', idempotency_key: crypto.randomUUID().replaceAll('-', '') }),
    });
    await refresh(); setNotice('Official laboratory example queued. Execution success is separate from scientific validation.');
  }
  async function cancelRun(id: string) {
    await api(`/projects/${selected}/runs/${id}/cancel`, { method: 'POST' }); await refresh();
  }
  async function loadResults(id: string) {
    setSelectedRun(id); setError('');
    const [meta, raw, productArea, point] = await Promise.all([
      api<ResultMetadata>(`/projects/${selected}/runs/${id}/results/metadata`),
      api<Window>(`/projects/${selected}/runs/${id}/results/window?bbox=${allCells}&field=h&first_frame=0&frame_count=1`),
      api<ProductArea>(`/projects/${selected}/runs/${id}/products/area?first_frame=0&frame_count=32`),
      api<LocationSeries>(`/projects/${selected}/runs/${id}/products/location?name=Nearest saved cell&x=0&y=0&radius_m=1000000000`),
    ]);
    setResultMeta(meta); setResultWindow(raw); setArea(productArea); setLocation(point); setTab('Results');
  }
  async function compareRuns() {
    if (!selectedRun || !otherRun) throw new Error('Select two successful runs to compare');
    setComparison(await api<Record<string, unknown>>(`/projects/${selected}/runs/${selectedRun}/compare/${otherRun}`));
  }
  async function submitEnsemble() {
    const variants = JSON.parse(ensembleVariants);
    await api(`/projects/${selected}/ensembles`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: ensembleName, variants }),
    });
    await refresh(); setNotice('Ensemble submitted. Each immutable variant has its own genuine solver run and cache identity.');
  }
  async function summarizeEnsemble(id: string) {
    setEnsembleSummary(await api<Record<string, unknown>>(`/projects/${selected}/ensembles/${id}/summary`));
  }
  async function queryObservation() {
    setObsResult(await api(`/observation/gee/query?site_key=ujjani-bhima&mode=${obsMode}`, { method: 'POST' }));
  }
  async function runSatelliteVal() {
    if (!selectedRun) throw new Error('Select a successful numerical run from Numerical runs first');
    setSatelliteComp(await api(`/projects/${selected}/runs/${selectedRun}/compare_satellite?mode=${obsMode}`, { method: 'POST' }));
  }
  async function runGaugeVal() {
    if (!selectedRun) throw new Error('Select a successful numerical run from Numerical runs first');
    setGaugeComp(await api(`/projects/${selected}/runs/${selectedRun}/gauges/station-001`));
  }
  async function loadExposure() {
    if (!selectedRun) throw new Error('Select a successful numerical run from Numerical runs first');
    setExposureData(await api(`/projects/${selected}/runs/${selectedRun}/exposure`));
  }
  async function downloadExport(format: string) {
    if (!selectedRun) throw new Error('Load a successful run before exporting');
    const response = await fetch(`/api/projects/${selected}/runs/${selectedRun}/exports/${format}`, { method: 'POST' });
    if (!response.ok) throw new Error(await response.text());
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url; link.download = `${selectedRun}-${format}`; link.click();
    URL.revokeObjectURL(url);
  }

  const activeRun = runs.find((run) => run.id === selectedRun);
  const latestJob = jobs[jobs.length - 1];
  const maxDepth = useMemo(() => resultWindow?.frames[0]?.values.reduce((m: number, v) => v == null ? m : Math.max(m, v), 0) ?? null, [resultWindow]);
  const menu = ['Overview', 'Data library', 'Scenarios', 'Readiness', 'Numerical runs', 'Ensembles', 'Results', 'Compare', 'Observations', 'Validation', 'Exposure', 'Exports'];

  return <div className="shell">
    <aside>
      <a className="brand" href="/">◈ <span>DamSafe</span></a>
      <div className="eyebrow">MODELLING WORKSPACE</div>
      <nav>{menu.map((item) => <button key={item} className={tab === item ? 'active' : ''} onClick={() => setTab(item)}>{item}<span>↗</span></button>)}</nav>
      <div className="sidebar-foot"><span className="dot" /> Local development<br /><small>SIH PS 26161 · Phase 4</small></div>
    </aside>
    <main>
      <header><div>PROJECT / <strong>UJJANI–BHIMA</strong></div><span className="tag">{health?.preview ? 'SQLITE PREVIEW' : 'POSTGIS'}</span></header>
      <div className="content">
        <div className="title-row"><div><div className="eyebrow">TRACEABLE INPUTS. EXPLAINABLE SCENARIOS.</div><h1>{tab === 'Overview' ? 'Before the first Ujjani simulation.' : tab}</h1><p className="intro">Prepare the Ujjani–Bhima case with a clear record of what is known, assumed and still missing.</p></div>
          <select aria-label="Project" value={selected} onChange={(e) => setSelected(e.target.value)}>{projects.map((p) => <option key={p.id} value={p.id}>{p.name}{p.synthetic ? ' · SYNTHETIC' : ''}</option>)}</select>
        </div>
        {error && <div role="alert" className="alert error">{error}</div>}{notice && <div role="status" className="alert">{notice}</div>}
        {!project ? <div className="panel">No project is configured. Run the documented bootstrap command to create the Ujjani workspace.</div> : <>
          {project.synthetic && <div className="alert"><strong>SYNTHETIC EXAMPLE</strong> — these inputs do not represent Ujjani and cannot be used as a site prediction.</div>}
          {tab === 'Overview' && <><div className="stats"><div><label>IMPORTED SOURCES</label><strong>{datasets.length.toString().padStart(2, '0')}</strong><small>Versioned with source checksums</small></div><div><label>READINESS FINDINGS</label><strong>{readiness?.missing.length ?? '—'}</strong><small>Items requiring evidence or setup</small></div><div><label>UJJANI NUMERICAL RUN</label><strong className="word">Blocked</strong><small>Site mesh and physical boundary evidence missing</small></div></div>
            <div className="overview-grid"><section className="panel"><div className="panel-heading"><h2>Study domain</h2><span className="tag">BHIMA RIVER</span></div><DomainMap project={project} /><div className="caption">MapLibre 2D · WGS84 display · no Ujjani simulated results available</div></section>
              <section className="panel next"><div className="eyebrow">NEXT STEPS</div><h2>Build the evidence base.</h2><ol><li><strong>Import physical inputs</strong><p>Terrain, channel geometry and timestamped water records.</p></li><li><strong>Resolve readiness findings</strong><p>Check units, elevation references, coverage and measurement meaning.</p></li><li><strong>Save a scenario</strong><p>Freeze sources and assumptions before a numerical run.</p></li></ol><button className="primary" onClick={() => setTab('Data library')}>Open data library →</button></section></div>
            <div className="note">No validated Ujjani flood prediction exists in this workspace. Hypothetical failure scenarios and historical releases have separate input contracts.</div></>}
          {tab === 'Data library' && <><section className="panel"><h2>Source register</h2>{!datasets.length ? <p className="empty">No sources imported. Missing data is not interpreted as zero.</p> : <div className="table-wrap"><table><thead><tr><th>Source</th><th>Type</th><th>Units</th><th>Evidence</th><th>Findings</th></tr></thead><tbody>{datasets.map((d) => <tr key={d.id}><td>{d.name}<small>Version {d.version} · {d.id}</small></td><td>{d.kind}</td><td>{d.provenance.units}</td><td>{d.provenance.status}</td><td>{d.inspection.issues.length}</td></tr>)}</tbody></table></div>}</section>
            <section className="panel form"><h2>Add an immutable source version</h2><p>Upload is connected to the ingestion API. The server validates format, provenance, units and limits before saving a checksum.</p><label>File<input type="file" onChange={(e) => setFile(e.target.files?.[0] ?? null)} /></label><label>Dataset contract<textarea aria-label="Dataset contract" value={metadata} onChange={(e) => setMetadata(e.target.value)} /></label><button className="primary" disabled={busy} onClick={() => act(upload)}>Save source version</button></section></>}
          {tab === 'Scenarios' && <section className="panel form"><h2>Hypothetical scenario configuration</h2><p>Scenario snapshots are immutable. This editor sends the exact JSON contract to the backend; validation errors are shown rather than replaced with defaults.</p><label>Scenario contract<textarea aria-label="Scenario contract" value={scenario} onChange={(e) => setScenario(e.target.value)} /></label><button className="primary" disabled={busy} onClick={() => act(saveScenario)}>Save scenario snapshot</button><div className="table-wrap"><table><thead><tr><th>Name</th><th>Evidence</th><th>Snapshot hash</th></tr></thead><tbody>{scenarios.map((s) => <tr key={s.id}><td>{s.name}<small>{s.id}</small></td><td>{s.snapshot.input_mode}</td><td>{s.sha256}</td></tr>)}</tbody></table></div></section>}
          {tab === 'Readiness' && <><section className="panel"><div className="panel-heading"><h2>Inputs need review</h2><button disabled={busy} onClick={() => act(runAudit)}>Run project audit</button></div>{latestJob && <p className="caption">Latest audit <StatusPill value={latestJob.state} /></p>}{readiness?.missing.map((f) => <div className="finding" key={f.code}><span className="finding-mark">!</span><div><strong>{f.code.replaceAll('_', ' ')}</strong><p>{f.message}</p></div></div>)}{!readiness?.missing.length && <p className="empty">No missing inputs reported for this project snapshot.</p>}</section><section className="panel"><h2>Warnings</h2>{readiness?.warnings.map((f) => <div className="finding" key={f.code}><span className="finding-mark">i</span><div><strong>{f.code.replaceAll('_', ' ')}</strong><p>{f.message}</p></div></div>)}</section></>}
          {tab === 'Numerical runs' && <><section className="panel"><div className="panel-heading"><h2>Engine examples</h2><button onClick={() => act(openLaboratory)}>Open laboratory project</button></div><p className="intro">These are laboratory or schematic examples with synthetic evidence. They are not Ujjani predictions, breach results or validation.</p><div className="engine-grid">{health?.engines.map((e) => <div className="engine-card" key={e.engine}><strong>{e.engine}</strong><StatusPill value={e.available ? 'AVAILABLE' : 'UNAVAILABLE'} /><small>{e.available ? e.image_id : e.reason}</small></div>)}</div><label>Engine<select value={engineChoice} onChange={(e) => setEngineChoice(e.target.value as 'dualsphysics' | 'dflowfm')}><option value="dualsphysics">DualSPHysics</option><option value="dflowfm">D-Flow FM</option></select></label><button className="primary" disabled={busy || !project.synthetic} onClick={() => act(submitNumerical)}>Run official laboratory example</button>{!project.synthetic && <p className="caption">Switch to the synthetic laboratory project before submitting an example.</p>}</section>
            <section className="panel"><h2>Run history</h2>{!runs.length ? <p className="empty">No runs in this project.</p> : <div className="table-wrap"><table><thead><tr><th>Run</th><th>Case</th><th>State / progress</th><th>Controls</th></tr></thead><tbody>{runs.map((run) => <tr key={run.id}><td><code>{run.id}</code><small>{run.input.request.engine}</small></td><td>{run.input.request.case_kind}</td><td><StatusPill value={run.state} />{run.result.progress && <small>{run.result.progress.stage ?? 'running'} · {run.result.progress.frame != null && run.result.progress.frames_total ? `frame ${run.result.progress.frame}/${run.result.progress.frames_total}` : run.result.progress.elapsed_seconds != null ? `${run.result.progress.elapsed_seconds.toFixed(1)} s elapsed` : 'heartbeat received'}</small>}{run.result.normalization && <small>{run.result.normalization.frames} frames · {run.result.normalization.cells} cells</small>}{run.result.error && <small>{run.result.error}</small>}</td><td>{['QUEUED', 'RUNNING'].includes(run.state) && <button onClick={() => act(() => cancelRun(run.id))}>Cancel</button>}{run.state === 'SUCCEEDED' && <button onClick={() => act(() => loadResults(run.id))}>Explore results</button>}</td></tr>)}</tbody></table></div>}</section></>}
          {tab === 'Ensembles' && <><section className="panel form"><h2>User-configured scenario ensemble</h2><p>Each variant is an immutable request with its own engine, model, input/configuration hash and genuine solver status. Counts are scenario frequency, not probability or real-world likelihood.</p><label>Ensemble name<input value={ensembleName} onChange={(e) => setEnsembleName(e.target.value)} /></label><label>Immutable run variants<textarea aria-label="Ensemble variants" value={ensembleVariants} onChange={(e) => setEnsembleVariants(e.target.value)} /></label><button className="primary" disabled={busy || !project.synthetic} onClick={() => act(submitEnsemble)}>Submit ensemble</button>{!project.synthetic && <p className="caption">Ujjani site variants remain blocked until verified hydraulic inputs exist.</p>}</section><section className="panel"><h2>Ensemble history</h2>{!ensembles.length ? <p className="empty">No ensembles configured.</p> : <div className="table-wrap"><table><thead><tr><th>Ensemble</th><th>Status</th><th>Runs</th><th>Summary</th></tr></thead><tbody>{ensembles.map((item) => <tr key={item.id}><td>{item.name}<small>{item.id}</small></td><td><StatusPill value={item.status} /></td><td>{item.run_ids.length}</td><td><button onClick={() => act(() => summarizeEnsemble(item.id))}>Review summary</button></td></tr>)}</tbody></table></div>}{ensembleSummary && <pre className="result-json">{JSON.stringify(ensembleSummary, null, 2)}</pre>}</section></>}
          {tab === 'Results' && <ResultsView run={activeRun} metadata={resultMeta} raw={resultWindow} area={area} location={location} maxDepth={maxDepth} onLoad={() => selectedRun && act(() => loadResults(selectedRun))} onExport={(format) => act(() => downloadExport(format))} />}
          {tab === 'Compare' && <section className="panel"><h2>Scenario and model comparison</h2><p>Comparison is enabled only for compatible saved outputs. Scales are fixed to the shared numerical contract; runs are never stretched independently.</p><div className="inline-form"><label>Run A<select value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)}><option value="">Select run</option>{runs.filter((r) => r.state === 'SUCCEEDED').map((r) => <option key={r.id} value={r.id}>{r.id} · {r.input.request.engine}</option>)}</select></label><label>Run B<select value={otherRun} onChange={(e) => setOtherRun(e.target.value)}><option value="">Select run</option>{runs.filter((r) => r.state === 'SUCCEEDED').map((r) => <option key={r.id} value={r.id}>{r.id} · {r.input.request.engine}</option>)}</select></label><button disabled={busy} onClick={() => act(compareRuns)}>Compare saved outputs</button></div>{comparison && <pre className="result-json">{JSON.stringify(comparison, null, 2)}</pre>}{!comparison && <p className="empty">No comparison requested. Incompatible CRS, datum, domain, resolution, thresholds or engine evidence will be reported instead of forced into a chart.</p>}</section>}
          {tab === 'Observations' && <section className="panel"><h2>Sentinel-1 Earth Engine Observation Query</h2><p className="intro">Query Earth Engine or fallback Sentinel-1 GRD observation metadata for the Ujjani–Bhima domain. Historical event scenes and latest overpasses are kept distinct.</p><div className="inline-form"><label>Observation Mode<select value={obsMode} onChange={(e) => setObsMode(e.target.value as 'HISTORICAL_EVENT' | 'LATEST_AVAILABLE')}><option value="HISTORICAL_EVENT">HISTORICAL_EVENT (August 2020 Monsoonal Flood)</option><option value="LATEST_AVAILABLE">LATEST_AVAILABLE (Most Recent Overpass)</option></select></label><button className="primary" disabled={busy} onClick={() => act(queryObservation)}>Query Observation</button></div>{obsResult && <pre className="result-json">{JSON.stringify(obsResult, null, 2)}</pre>}{!obsResult && <p className="empty">No observation query executed yet. Press 'Query Observation' to retrieve satellite metadata and coverage.</p>}</section>}
          {tab === 'Validation' && <><section className="panel"><h2>Satellite Flood Agreement Assessment</h2><p className="intro">Evaluates cell-by-cell spatial agreement between a selected numerical simulation run and a Sentinel-1 satellite flood reference. Labeled strictly as "agreement with satellite-derived flood reference".</p><div className="inline-form"><label>Selected Numerical Run<select value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)}><option value="">Select run</option>{runs.filter((r) => r.state === 'SUCCEEDED').map((r) => <option key={r.id} value={r.id}>{r.id} · {r.input.request.engine}</option>)}</select></label><button className="primary" disabled={busy || !selectedRun} onClick={() => act(runSatelliteVal)}>Compute Satellite Agreement Metrics</button></div>{satelliteComp && <pre className="result-json">{JSON.stringify(satelliteComp, null, 2)}</pre>}{!satelliteComp && <p className="empty">Select a successful run and press 'Compute Satellite Agreement Metrics' to calculate IoU, Precision, Recall, and Confusion Matrix.</p>}</section><section className="panel"><h2>Independent Gauge Hydrograph Evaluation</h2><p className="intro">Compares simulated stage and discharge hydrographs against independent river gauge recordings.</p><button disabled={busy || !selectedRun} onClick={() => act(runGaugeVal)}>Evaluate Gauge Station 001</button>{gaugeComp && <pre className="result-json">{JSON.stringify(gaugeComp, null, 2)}</pre>}{!gaugeComp && <p className="empty">Press 'Evaluate Gauge Station 001' to inspect gauge status.</p>}</section></>}
          {tab === 'Exposure' && <section className="panel"><h2>Exposure & Economic Loss Assessment</h2><p className="intro">Evaluates spatial overlay of numerical flood extents with settlement, farmland, and population layers. Missing datasets return UNAVAILABLE rather than zero.</p><div className="inline-form"><label>Selected Numerical Run<select value={selectedRun} onChange={(e) => setSelectedRun(e.target.value)}><option value="">Select run</option>{runs.filter((r) => r.state === 'SUCCEEDED').map((r) => <option key={r.id} value={r.id}>{r.id} · {r.input.request.engine}</option>)}</select></label><button className="primary" disabled={busy || !selectedRun} onClick={() => act(loadExposure)}>Evaluate Exposure & Loss</button></div>{exposureData && <pre className="result-json">{JSON.stringify(exposureData, null, 2)}</pre>}{!exposureData && <p className="empty">Select a successful run and press 'Evaluate Exposure & Loss' to compute exposure metrics.</p>}</section>}
          {tab === 'Exports' && <section className="panel unavailable"><h2>Exports available after processing</h2><p>GeoTIFF, KML, GeoJSON, Shapefile, CSV and report exports remain disabled until a compatible saved numerical result and independently reopened product are available.</p><button disabled>Export flood depth</button> <button disabled>Export technical report</button><div className="note">No placeholder file or synthetic export is offered.</div></section>}
        </>}
      </div>
      <footer><span>Hypothetical and synthetic evidence are labelled throughout.</span><span>UTC and simulation elapsed time are shown when the source provides them.</span></footer>
    </main>
  </div>;
}

function ResultsView({ run, metadata, raw, area, location, maxDepth, onLoad, onExport }: { run?: NumericalRun; metadata: ResultMetadata | null; raw: Window | null; area: ProductArea | null; location: LocationSeries | null; maxDepth: number | null; onLoad: () => void; onExport: (format: string) => void }) {
  if (!run || run.state !== 'SUCCEEDED') return <section className="panel"><h2>Numerical results</h2><p className="empty">Select a successful saved run from Numerical runs. Queued or failed runs cannot display numerical values.</p></section>;
  if (!metadata || !raw || !area) return <section className="panel"><h2>Numerical results</h2><button className="primary" onClick={onLoad}>Load saved numerical result</button><p className="empty">Only genuine saved solver frames are rendered; there is no synthetic UI fallback.</p></section>;
  const frame = raw.frames[0];
  const wet = frame?.states.filter((state) => state === 'WET').length ?? 0;
  return <><section className="alert"><strong>{metadata.input_mode} · {metadata.case_kind}</strong> — {metadata.engine} output, source run {metadata.source_run_id}. {metadata.cached ? 'This entry is a verified identical-configuration cache.' : 'This is a retained saved numerical result.'}</section>
    <div className="stats"><div><label>MAXIMUM DEPTH</label><strong>{maxDepth == null ? '—' : `${maxDepth.toFixed(3)} m`}</strong><small>Exact value from saved frame 0 window</small></div><div><label>WET CELLS IN FRAME 0</label><strong>{wet}</strong><small>Dry and nodata are not counted as wet</small></div><div><label>SIMULATION ELAPSED</label><strong className="word">{metadata.simulation_elapsed_seconds[1]} s</strong><small>{metadata.start_time ? `UTC start ${metadata.start_time}` : 'UTC start unavailable; source clock is not qualified'}</small></div></div>
    <section className="panel"><div className="panel-heading"><h2>Saved-frame playback</h2><span className="tag">VISUAL INTERPOLATION: NONE</span></div><div className="result-map"><div className="legend"><strong>Depth (m)</strong><span className="swatch shallow" />0.01 wet threshold<span className="swatch deep" />fixed display scale: 0–1 m</div>{raw.cells.map((cell, i) => <span key={cell.cell} className={`cell ${frame.states[i].toLowerCase()}`} style={{ left: `${(cell.x % 100 + 100) % 100}%`, top: `${(cell.y % 100 + 100) % 100}%` }} title={`Cell ${cell.cell}: ${frame.values[i] ?? 'NODATA'} m`} />)}</div><p className="caption">Frame {frame.frame} · {frame.elapsed_s} s elapsed · values in metres · WET, DRY and NODATA are distinct. The background is not an interpolated flood surface.</p></section>
    <section className="panel"><h2>Derived products</h2><div className="metric-grid"><div><strong>{area.frames[0]?.flooded_area_m2.toFixed(2)} m²</strong><small>Known flooded area at {area.threshold_m} m threshold</small></div><div><strong>{area.frames[0]?.unknown_area_m2.toFixed(2)} m²</strong><small>Unknown area, never treated as dry</small></div><div><strong>{location?.arrival_elapsed_s == null ? 'Not reached / unavailable' : `${location.arrival_elapsed_s} s`}</strong><small>{location?.name ?? 'Named location'} arrival time</small></div></div><p className="caption">{area.area_semantics}; baseline water: {area.baseline_water}. Duration and arrival use saved frames, not interpolated values.</p></section>
    <section className="panel"><h2>Technical details and exports</h2><div className="detail-grid"><span>CRS <b>{metadata.crs ?? 'Unknown'}</b></span><span>Vertical datum <b>{metadata.vertical_datum ?? 'Unknown'}</b></span><span>Units <b>h {metadata.units.h ?? '—'} · velocity {metadata.units.u ?? '—'}</b></span><span>Nodata <b>{metadata.nodata_encoding}</b></span><span>Frames / cells <b>{metadata.output_frame_count} / {metadata.cell_count}</b></span><span>Precision <b>{metadata.arrival_precision}</b></span></div><div className="export-actions">{['geotiff', 'kml', 'geojson', 'shapefile', 'csv', 'html'].map((format) => <button key={format} onClick={() => onExport(format)}>Download {format}</button>)}</div><p className="caption">Every export is written with provenance and must be independently reopenable; unsupported CRS or missing products returns an honest error.</p></section></>;
}

createRoot(document.getElementById('root')!).render(<App />);
