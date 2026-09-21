import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

type Meta = {
  run_id: string; particle_count: number; boundary_particles_flat: number[];
  frames_count: number; default_decimation: number; scientific_disclaimer: string;
  bounds: { x_min: number; x_max: number; y_min: number; y_max: number; z_min: number; z_max: number };
};
type Frame = {
  frame_index: number; time_seconds: number; particle_count: number;
  flat_positions: number[]; flat_velocities: number[]; max_velocity: number; max_elevation: number;
};
export function Sph3DViewer({ runId, apiBase = '/api', onSelectAnotherRun, availableSphRuns = [] }: {
  runId: string; apiBase?: string; onSelectAnotherRun?: (id: string) => void; availableSphRuns?: string[];
}) {
  const host = useRef<HTMLDivElement>(null);
  const points = useRef<THREE.Points<THREE.BufferGeometry, THREE.PointsMaterial> | null>(null);
  const reset = useRef<() => void>(() => {});
  const [meta, setMeta] = useState<Meta | null>(null);
  const [frame, setFrame] = useState<Frame | null>(null);
  const [index, setIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [error, setError] = useState('');
  const [stride, setStride] = useState(1);
  const cache = useRef(new Map<string, Frame>());

  useEffect(() => {
    const abort = new AbortController();
    setMeta(null); setFrame(null); setIndex(0); setPlaying(false); setError(''); cache.current.clear();
    fetch(apiBase + '/runs/' + encodeURIComponent(runId) + '/sph/metadata', { signal: abort.signal })
      .then(async r => { if (!r.ok) throw new Error('SPH metadata unavailable (' + r.status + ')'); return r.json(); })
      .then((data: Meta) => { if (!abort.signal.aborted) { setMeta(data); setStride(data.default_decimation || 1); } })
      .catch(e => { if (!abort.signal.aborted) setError(String(e)); });
    return () => abort.abort();
  }, [runId, apiBase]);

  useEffect(() => {
    if (!meta || meta.run_id !== runId) return;
    const abort = new AbortController();
    const key = runId + ':' + index + ':' + stride;
    setFrame(null);
    const saved = cache.current.get(key);
    if (saved) { setFrame(saved); return; }
    fetch(apiBase + '/runs/' + encodeURIComponent(runId) + '/sph/frame?index=' + index + '&decimation=' + stride, { signal: abort.signal })
      .then(async r => { if (!r.ok) throw new Error('Particle frame unavailable (' + r.status + ')'); return r.json(); })
      .then((data: Frame) => {
        if (abort.signal.aborted) return;
        cache.current.set(key, data);
        if (cache.current.size > 12) cache.current.delete(cache.current.keys().next().value!);
        setFrame(data); setError('');
      }).catch(e => { if (!abort.signal.aborted) { setError(String(e)); setPlaying(false); } });
    return () => abort.abort();
  }, [meta, runId, apiBase, index, stride]);

  useEffect(() => {
    if (!playing || !frame || !meta || frame.frame_index !== index) return;
    const timer = setTimeout(() => {
      if (index >= meta.frames_count - 1) setPlaying(false);
      else setIndex(index + 1);
    }, 160);
    return () => clearTimeout(timer);
  }, [playing, frame, meta, index]);

  useEffect(() => {
    const container = host.current;
    if (!container || !meta) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
    catch { setError('WebGL is unavailable. Enable browser graphics acceleration to view particles.'); return; }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', 'Saved DualSPHysics particles');
    const scene = new THREE.Scene(); scene.background = new THREE.Color('#edf4fa');
    const camera = new THREE.PerspectiveCamera(42, 1, 0.001, 10000);
    camera.up.set(0, 0, 1);
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    const b = meta.bounds;
    const box = new THREE.Box3(new THREE.Vector3(b.x_min, b.y_min, b.z_min), new THREE.Vector3(b.x_max, b.y_max, b.z_max));
    const boundaryGeometry = new THREE.BufferGeometry();
    boundaryGeometry.setAttribute('position', new THREE.Float32BufferAttribute(meta.boundary_particles_flat, 3));
    boundaryGeometry.computeBoundingBox();
    if (boundaryGeometry.boundingBox && !boundaryGeometry.boundingBox.isEmpty()) box.union(boundaryGeometry.boundingBox);
    const centre = box.getCenter(new THREE.Vector3());
    const size = Math.max(box.getSize(new THREE.Vector3()).length(), 0.1);
    reset.current = () => {
      controls.target.copy(centre);
      camera.position.copy(centre).add(new THREE.Vector3(size * .65, -size * 1.35, size * .6));
      controls.update();
    };
    reset.current();
    scene.add(new THREE.Points(boundaryGeometry, new THREE.PointsMaterial({ color: '#94a3b8', size: 2, sizeAttenuation: false })));
    const fluid = new THREE.Points(new THREE.BufferGeometry(), new THREE.PointsMaterial({ size: 3, sizeAttenuation: false, vertexColors: true }));
    fluid.frustumCulled = false; scene.add(fluid); points.current = fluid;
    scene.add(new THREE.Box3Helper(box, new THREE.Color('#cbd5e1')));
    const resize = () => {
      const w = container.clientWidth || 800, h = container.clientHeight || 520;
      camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h);
    };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    let animation = 0;
    const draw = () => { animation = requestAnimationFrame(draw); controls.update(); renderer.render(scene, camera); };
    draw();
    return () => {
      cancelAnimationFrame(animation); observer.disconnect(); controls.dispose();
      scene.traverse(object => {
        const drawable = object as THREE.Mesh;
        drawable.geometry?.dispose();
        if (drawable.material) (Array.isArray(drawable.material) ? drawable.material : [drawable.material]).forEach(m => m.dispose());
      });
      renderer.dispose(); renderer.domElement.remove(); points.current = null;
    };
  }, [meta]);

  useEffect(() => {
    const fluid = points.current;
    if (!fluid) return;
    const positions = frame?.flat_positions ?? [];
    const colors = new Float32Array(positions.length);
    const color = new THREE.Color();
    for (let i = 0; i < positions.length / 3; i++) {
      color.setHSL(.61 - Math.min((frame?.flat_velocities[i] ?? 0) / 5, 1) * .12, .85, .45);
      color.toArray(colors, i * 3);
    }
    fluid.geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
    fluid.geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    fluid.geometry.computeBoundingSphere();
  }, [frame, meta]);

  return <section className="card sph-viewer">
    <div className="card-header"><h2>DualSPHysics · laboratory dam break</h2><button className="btn" onClick={() => reset.current()}>Reset view</button></div>
    <div className="card-body">
      {availableSphRuns.length > 1 && <label>Saved run <select value={runId} onChange={e => onSelectAnotherRun?.(e.target.value)}>{availableSphRuns.map(id => <option key={id}>{id}</option>)}</select></label>}
      <p>Real saved solver particles in local metre coordinates. These laboratory results have no river-map coordinates.</p>
      {error && <div role="alert" className="alert alert-error">{error}</div>}
      <div className="metric-grid">
        <div className="metric-card">Particles<strong>{frame ? frame.particle_count.toLocaleString() : 'Loading…'}</strong></div>
        <div className="metric-card">Maximum speed<strong>{frame ? frame.max_velocity.toFixed(3) + ' m/s' : '—'}</strong></div>
        <div className="metric-card">Maximum elevation Z<strong>{frame ? frame.max_elevation.toFixed(3) + ' m' : '—'}</strong></div>
        <div className="metric-card">Saved time<strong>{frame ? frame.time_seconds.toFixed(3) + ' s' : 'Loading…'}</strong></div>
      </div>
      <div ref={host} style={{ height: 520, width: '100%', borderRadius: 12, overflow: 'hidden' }} />
      <div className="timeline-bar">
        <button className="btn btn-primary" disabled={!meta} onClick={() => { if (meta && index === meta.frames_count - 1) setIndex(0); setPlaying(!playing); }}>{playing ? 'Pause' : 'Play'}</button>
        <input aria-label="SPH frame" type="range" min={0} max={Math.max(0, (meta?.frames_count ?? 1) - 1)} value={index} onChange={e => setIndex(Number(e.target.value))} />
        <span>Frame {index} / {Math.max(0, (meta?.frames_count ?? 1) - 1)}</span>
        <label>Sampling <select value={stride} onChange={e => setStride(Number(e.target.value))}>{[1, 2, 4, 8].map(n => <option key={n} value={n}>1 in {n}</option>)}</select></label>
      </div>
      <p className="caption">Drag to orbit · right drag to pan · scroll to zoom. Velocity colour: dark blue 0 to cyan 5+ m/s. Grey particles are boundaries. {meta?.scientific_disclaimer}</p>
    </div>
  </section>;
}
