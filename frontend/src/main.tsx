import React, { useCallback, useEffect, useRef, useState } from 'react';
import ReactDOM from 'react-dom/client';
import './style.css';
import 'maplibre-gl/dist/maplibre-gl.css';

import {
  getHealth, listProjects, getProject, listDatasets, getReadiness, listJobs,
  listScenarios, listRuns, listEnsembles, getResultMetadata, getResultWindow,
  getProductArea, getLocationSeries, listSphRuns, downloadExport,
} from './api';
import type {
  Dataset, Ensemble, HealthStatus, Job, LocationSeries, NumericalRun,
  ProductArea, Project, Readiness, ResultMetadata, ResultWindow, Scenario, Page,
} from './types';

import { Sidebar } from './components/Sidebar';
import { Dashboard } from './pages/Dashboard';
import { StudyArea } from './pages/StudyArea';
import { DataSetup } from './pages/DataSetup';
import { ScenarioBuilder } from './pages/ScenarioBuilder';
import { Simulation } from './pages/Simulation';
import { Results } from './pages/Results';
import { Validation } from './pages/Validation';
import { ImpactHadr } from './pages/ImpactHadr';
import { ReportsExport } from './pages/ReportsExport';

const POLL_INTERVAL_MS = 1500;
const RESULTS_LOCATION_X = 516000; // UTM zone 43N approximate Bhima reach
const RESULTS_LOCATION_Y = 1997000;
const RESULTS_LOCATION_RADIUS_M = 5000;

function App() {
  // ── Navigation ──────────────────────────────────────────────────────────────
  const [page, setPage] = useState<Page>('dashboard');

  // ── Global state ─────────────────────────────────────────────────────────────
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // ── API data ─────────────────────────────────────────────────────────────────
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [readiness, setReadiness] = useState<Readiness | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [runs, setRuns] = useState<NumericalRun[]>([]);
  const [ensembles, setEnsembles] = useState<Ensemble[]>([]);

  // ── Results state ─────────────────────────────────────────────────────────────
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [resultMeta, setResultMeta] = useState<ResultMetadata | null>(null);
  const [resultWindow, setResultWindow] = useState<ResultWindow | null>(null);
  const [productArea, setProductArea] = useState<ProductArea | null>(null);
  const [locationSeries, setLocationSeries] = useState<LocationSeries | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [field, setField] = useState<'h' | 'velocity_magnitude'>('h');

  // ── SPH state ────────────────────────────────────────────────────────────────
  const [sphRuns, setSphRuns] = useState<string[]>([]);
  const [sphRunId, setSphRunId] = useState('');

  // ── Polling ───────────────────────────────────────────────────────────────────
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const resultRequest = useRef(0);

  const showError = useCallback((msg: string) => { setError(msg); }, []);
  const showNotice = useCallback((msg: string) => { setNotice(msg); }, []);
  const clearNotice = useCallback(() => setNotice(null), []);
  const clearError = useCallback(() => setError(null), []);

  // ── Initial data load ─────────────────────────────────────────────────────────
  useEffect(() => {
    async function init() {
      try {
        const [h, ps] = await Promise.all([getHealth(), listProjects()]);
        setHealth(h);
        setProjects(ps);
        if (ps.length > 0) {
          setProject(ps.find(p => p.id === 'ujjani-persistent-proj-001') ?? ps[0]);
        }
      } catch (e) {
        showError(`Startup failed: ${e}`);
      }
    }
    init();
  }, []);

  // SPH runs on mount
  useEffect(() => {
    listSphRuns()
      .then((r) => {
        setSphRuns(r.runs ?? []);
        if ((r.runs ?? []).length > 0) setSphRunId(r.runs[0]);
      })
      .catch(() => { /* SPH may not be available */ });
  }, []);

  // ── Reload project-level data when project changes ────────────────────────────
  useEffect(() => {
    if (!project) return;
    let cancelled = false;
    ++resultRequest.current;
    setSelectedRunId(null);
    setResultMeta(null);
    setResultWindow(null);
    setProductArea(null);
    setLocationSeries(null);
    setReadiness(null);
    setIsPlaying(false);
    setCurrentFrame(0);
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null; }

    async function load() {
      try {
        const [ds, sc, ru, ens, jr] = await Promise.all([
          listDatasets(project!.id),
          listScenarios(project!.id),
          listRuns(project!.id),
          listEnsembles(project!.id),
          listJobs(project!.id),
        ]);
        if (cancelled) return;
        setDatasets(ds);
        setScenarios(sc);
        setRuns(ru);
        setEnsembles(ens);
        setJobs(jr as Job[]);

        // Try readiness (may not have a scenario yet)
        try {
          const rd = await getReadiness(project!.id);
          if (!cancelled) setReadiness(rd);
        } catch { /* Readiness may need a scenario first */ }
      } catch (e) {
        if (!cancelled) showError(`Failed to load project data: ${e}`);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [project]);

  // ── Polling for active runs ───────────────────────────────────────────────────
  useEffect(() => {
    const hasActive = runs.some((r) => ['QUEUED', 'RUNNING'].includes(r.state));
    if (hasActive && !pollRef.current && project) {
      pollRef.current = setInterval(async () => {
        try {
          const updated = await listRuns(project!.id);
          setRuns(updated);
          const stillActive = updated.some((r) => ['QUEUED', 'RUNNING'].includes(r.state));
          if (!stillActive && pollRef.current) {
            clearInterval(pollRef.current);
            pollRef.current = null;
          }
        } catch { /* ignore poll errors */ }
      }, POLL_INTERVAL_MS);
    } else if (!hasActive && pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    return () => {};
  }, [runs, project]);

  // ── Playback ─────────────────────────────────────────────────────────────────
  const playRef = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (isPlaying && resultMeta) {
      playRef.current = setInterval(() => {
        setCurrentFrame((f) => {
          if (resultWindow?.field !== field || !resultWindow.frames.some(frame => frame.frame === f)) return f;
          if (f >= resultMeta.output_frame_count - 1) {
            setIsPlaying(false);
            return 0;
          }
          return f + 1;
        });
      }, 300);
    } else if (playRef.current) {
      clearInterval(playRef.current);
      playRef.current = null;
    }
    return () => { if (playRef.current) clearInterval(playRef.current); };
  }, [isPlaying, resultMeta, resultWindow, field]);

  // ── Result loading ────────────────────────────────────────────────────────────
  async function loadResults(runId?: string) {
    if (!project) return;
    const rId = runId ?? selectedRunId ?? runs.find((r) => r.state === 'SUCCEEDED')?.id;
    if (!rId) { showError('No succeeded run to load results from.'); return; }

    // Navigate immediately; an in-flight result response must not pull the user
    // back after they have already opened another page.
    setPage('results');
    setBusy(true);
    try {
      const requestId = ++resultRequest.current;
      const meta = await getResultMetadata(project.id, rId);
      const win = await getResultWindow(project.id, rId, 'h', 0, Math.min(32, meta.output_frame_count));
      const area = await getProductArea(project.id, rId, 0, Math.min(32, meta.output_frame_count));
      if (requestId !== resultRequest.current) return;
      setField('h');
      setSelectedRunId(rId);
      setResultMeta(meta);
      setResultWindow(win);
      setProductArea(area);
      setCurrentFrame(0);
      setIsPlaying(false);

      // Load location series asynchronously
      getLocationSeries(project.id, rId, 'bhima-reach', RESULTS_LOCATION_X, RESULTS_LOCATION_Y, RESULTS_LOCATION_RADIUS_M)
        .then(data => { if (requestId === resultRequest.current) setLocationSeries(data); })
        .catch(() => { if (requestId === resultRequest.current) setLocationSeries(null); });
    } catch (e) {
      showError(`Results load failed: ${e}`);
    } finally {
      setBusy(false);
    }
  }

  // When frame changes, fetch new frame window if needed
  useEffect(() => {
    if (!project || !selectedRunId || !resultMeta) return;
    const existing = resultWindow?.frames.find((f) => f.frame === currentFrame);
    if (existing && resultWindow?.field === field) return;
    let cancelled = false;
    const first = Math.floor(currentFrame / 32) * 32;

    // Fetch the new frame (don't block UI)
    getResultWindow(project.id, selectedRunId, field, first, Math.min(32, resultMeta.output_frame_count - first))
      .then((win) => {
        return getProductArea(project.id, selectedRunId, first, Math.min(32, resultMeta.output_frame_count - first))
          .then(area => { if (!cancelled) { setResultWindow(win); setProductArea(area); } });
      })
      .catch((e) => { if (!cancelled) { setIsPlaying(false); showError(String(e)); } });
    return () => { cancelled = true; };
  }, [currentFrame, field, project, selectedRunId, resultMeta]);

  // ── Refresh helper ────────────────────────────────────────────────────────────
  async function refresh() {
    if (!project) return;
    const [ds, sc, ru, ens, jr] = await Promise.all([
      listDatasets(project.id),
      listScenarios(project.id),
      listRuns(project.id),
      listEnsembles(project.id),
      listJobs(project.id),
    ]);
    setDatasets(ds);
    setScenarios(sc);
    setRuns(ru);
    setEnsembles(ens);
    setJobs(jr as Job[]);
    try {
      const rd = await getReadiness(project.id);
      setReadiness(rd);
    } catch { /* ok */ }
  }

  // ── Export ────────────────────────────────────────────────────────────────────
  async function handleExport(format: string) {
    if (!project || !selectedRunId) { showError('Load results first.'); return; }
    setBusy(true);
    try {
      await downloadExport(project.id, selectedRunId, format);
      showNotice(`${format.toUpperCase()} export downloaded.`);
    } catch (e) {
      showError(String(e));
    } finally {
      setBusy(false);
    }
  }

  // ── Navigate helper (also loads results when going to Results page) ───────────
  function navigate(p: Page) {
    setPage(p);
    if (p === 'results' && !resultMeta && runs.some((r) => r.state === 'SUCCEEDED')) {
      loadResults();
    }
  }

  const latestSucceeded = runs.find((r) => r.state === 'SUCCEEDED');
  const selectedRun = runs.find((r) => r.id === selectedRunId) ?? latestSucceeded ?? null;

  // ── Page → label for topbar ───────────────────────────────────────────────────
  const PAGE_LABELS: Record<Page, string> = {
    'dashboard': 'Mission Control',
    'study-area': 'Study Area',
    'data-setup': 'Data Setup',
    'scenario-builder': 'Scenario Builder',
    'simulation': 'Simulation',
    'results': 'Results',
    'validation': 'Validation',
    'impact': 'Impact & HADR',
    'reports': 'Reports & Export',
  };

  return (
    <div className="shell">
      <Sidebar
        active={page}
        onNavigate={navigate}
        projectName={project?.name}
        isPreview={health?.preview}
        hasSucceededRun={!!latestSucceeded}
      />

      <div className="main">
        {/* Topbar */}
        <header className="topbar" role="banner">
          <div className="topbar-breadcrumb">
            <span>DamSafe</span>
            <span>›</span>
            <strong>{PAGE_LABELS[page]}</strong>
          </div>
          <div className="topbar-right">
            <select aria-label="Active project" className="form-select" value={project?.id ?? ''} onChange={e => {
              const next = projects.find(p => p.id === e.target.value);
              if (next) { setRuns([]); setProject(next); }
            }} style={{ maxWidth: 290 }}>
              {projects.map(p => <option key={p.id} value={p.id}>{p.name}{p.synthetic ? ' · laboratory' : ''}</option>)}
            </select>
            {health?.preview && (
              <span className="topbar-badge">PREVIEW MODE</span>
            )}
            {project?.synthetic && (
              <span className="topbar-badge">SYNTHETIC EXAMPLE</span>
            )}
            <span className="topbar-badge blue">SIH PS 26161</span>
          </div>
        </header>

        {/* Global notice / error */}
        {error && (
          <div className="alert alert-error" style={{ margin: '12px 32px 0', cursor: 'pointer' }} onClick={clearError}>
            ✕ {error}
          </div>
        )}
        {notice && (
          <div className="alert alert-info" style={{ margin: '12px 32px 0', cursor: 'pointer' }} onClick={clearNotice}>
            ℹ {notice}
          </div>
        )}

        {/* Page content */}
        <main className="page-content" role="main">
          {page === 'dashboard' && (
            <Dashboard
              project={project}
              health={health}
              readiness={readiness}
              runs={runs}
              onNavigate={navigate}
            />
          )}
          {page === 'study-area' && (
            <StudyArea project={project} />
          )}
          {page === 'data-setup' && (
            <DataSetup
              project={project}
              datasets={datasets}
              readiness={readiness}
              jobs={jobs}
              onRefresh={refresh}
              onError={showError}
              onNotice={showNotice}
              busy={busy}
              setBusy={setBusy}
            />
          )}
          {page === 'scenario-builder' && (
            <ScenarioBuilder
              project={project}
              datasets={datasets}
              scenarios={scenarios}
              ensembles={ensembles}
              onRefresh={refresh}
              onError={showError}
              onNotice={showNotice}
              busy={busy}
              setBusy={setBusy}
            />
          )}
          {page === 'simulation' && (
            <Simulation
              project={project}
              health={health}
              runs={runs}
              scenarios={scenarios}
              onRefresh={refresh}
              onError={showError}
              onNotice={showNotice}
              onLoadResults={(runId) => loadResults(runId)}
              busy={busy}
              setBusy={setBusy}
            />
          )}
          {page === 'results' && (
            <Results
              project={project}
              run={selectedRun}
              metadata={resultMeta}
              raw={resultWindow}
              area={productArea}
              location={locationSeries}
              currentFrame={currentFrame}
              onFrameChange={setCurrentFrame}
              field={field}
              onFieldChange={setField}
              isPlaying={isPlaying}
              onTogglePlay={() => setIsPlaying((p) => !p)}
              onLoad={loadResults}
              onExport={handleExport}
              sphRunId={sphRunId}
              availableSphRuns={sphRuns}
              onSphRunChange={setSphRunId}
              runs={runs}
              onError={showError}
              onNotice={showNotice}
            />
          )}
          {page === 'validation' && (
            <Validation
              project={project}
              runs={runs}
              onError={showError}
              onNotice={showNotice}
            />
          )}
          {page === 'impact' && (
            <ImpactHadr
              project={project}
              runs={runs}
              onError={showError}
              onNotice={showNotice}
            />
          )}
          {page === 'reports' && (
            <ReportsExport
              project={project}
              runs={runs}
              scenarios={scenarios}
              metadata={resultMeta}
              onError={showError}
              onNotice={showNotice}
            />
          )}
        </main>
      </div>
    </div>
  );
}

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
