import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { ResultCell, ResultFrame } from './types';

export function River3DViewer({ cells, frame, frameNumber, crs }: {
  cells: ResultCell[]; frame?: ResultFrame; frameNumber: number; crs: string | null;
}) {
  const host = useRef<HTMLDivElement>(null);
  const water = useRef<THREE.Mesh[]>([]);
  const scaleRef = useRef(1);
  const reset = useRef<() => void>(() => {});
  const [exaggeration, setExaggeration] = useState(20);
  const [error, setError] = useState('');
  const valid = cells.length > 0 && cells.length <= 2048 && crs === 'EPSG:32643' &&
    cells.every(c => Number.isFinite(c.bed_m) && c.polygon && c.polygon.length >= 4);
  useEffect(() => {
    const container = host.current;
    if (!container || !valid) return;
    let renderer: THREE.WebGLRenderer;
    try { renderer = new THREE.WebGLRenderer({ antialias: true }); }
    catch { setError('WebGL unavailable. Use the geographic 2D map.'); return; }
    setError('');
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2)); container.appendChild(renderer.domElement);
    renderer.domElement.setAttribute('aria-label', 'Native river mesh and saved water surface');
    const scene = new THREE.Scene(); scene.background = new THREE.Color('#eaf1f6');
    scene.add(new THREE.HemisphereLight(0xffffff, 0x738573, 2));
    const sunlight = new THREE.DirectionalLight(0xffffff, 2); sunlight.position.set(3, 8, 5); scene.add(sunlight);
    const xy = cells.flatMap(c => c.polygon!);
    const xs = xy.map(p => p[0]), ys = xy.map(p => p[1]);
    const x0 = (Math.min(...xs) + Math.max(...xs)) / 2;
    const y0 = (Math.min(...ys) + Math.max(...ys)) / 2;
    const bed0 = Math.min(...cells.map(c => c.bed_m));
    const scale = 12 / Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 1);
    scaleRef.current = scale * exaggeration;
    water.current = [];
    cells.forEach(cell => {
      const ring = cell.polygon!;
      const positions: number[] = [];
      // Native convex D-Flow faces, with piecewise constant saved cell bed.
      for (let i = 1; i < ring.length - 2; i++) {
        for (const [x, y] of [ring[0], ring[i], ring[i + 1]]) positions.push((x - x0) * scale, (cell.bed_m - bed0) * scale * exaggeration, -(y - y0) * scale);
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3)); geometry.computeVertexNormals();
      scene.add(new THREE.Mesh(geometry, new THREE.MeshStandardMaterial({ color: '#a3ad84', side: THREE.DoubleSide })));
      const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), new THREE.LineBasicMaterial({ color: '#829077', transparent: true, opacity: .4 }));
      scene.add(edges);
      const surface = new THREE.Mesh(geometry.clone(), new THREE.MeshStandardMaterial({ color: '#168ed1', side: THREE.DoubleSide, transparent: true, opacity: .85, roughness: .25 }));
      surface.visible = false; water.current.push(surface); scene.add(surface);
    });
    const camera = new THREE.PerspectiveCamera(45, 1, .01, 1000);
    const controls = new OrbitControls(camera, renderer.domElement); controls.enableDamping = true;
    const centre = new THREE.Box3().setFromObject(scene).getCenter(new THREE.Vector3());
    reset.current = () => { controls.target.copy(centre); camera.position.copy(centre).add(new THREE.Vector3(7, 10, 12)); controls.update(); };
    reset.current();
    const resize = () => { const w = container.clientWidth || 800, h = container.clientHeight || 520; renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix(); };
    const observer = new ResizeObserver(resize); observer.observe(container); resize();
    let animation = 0;
    const draw = () => { animation = requestAnimationFrame(draw); controls.update(); renderer.render(scene, camera); }; draw();
    return () => {
      cancelAnimationFrame(animation); observer.disconnect(); controls.dispose();
      scene.traverse(obj => { const m = obj as THREE.Mesh; m.geometry?.dispose(); if (m.material) (Array.isArray(m.material) ? m.material : [m.material]).forEach(v => v.dispose()); });
      renderer.dispose(); renderer.domElement.remove(); water.current = [];
    };
  }, [cells, valid, exaggeration]);
  useEffect(() => {
    water.current.forEach((mesh, i) => {
      const depth = frame?.values[i];
      mesh.visible = frame?.states[i] === 'WET' && depth != null && Number.isFinite(depth);
      mesh.position.y = Math.max(0, depth ?? 0) * scaleRef.current + .001;
      (mesh.material as THREE.MeshStandardMaterial).color.set(depth == null || depth < .5 ? '#93c5fd' : depth < 1 ? '#60a5fa' : depth < 2 ? '#3b82f6' : depth < 5 ? '#2563eb' : '#1d4ed8');
    });
  }, [frame, cells, exaggeration]);
  return <section className="card">
    <div className="card-header"><h2>River mesh & water surface</h2><button className="btn" onClick={() => reset.current()}>Reset view</button></div>
    <div className="card-body">
      <div className="river-3d-toolbar"><span>Frame {frameNumber} · {frame ? (frame.elapsed_s / 3600).toFixed(1) + ' hours' : 'Loading depth…'}</span>
        <label>Vertical exaggeration <select value={exaggeration} onChange={e => setExaggeration(Number(e.target.value))}>{[1, 5, 20, 50, 100].map(n => <option value={n} key={n}>{n}×</option>)}</select></label>
      </div>
      {!valid && <p>Native face polygons in EPSG:32643 are required for this river view.</p>}
      {error && <p role="alert">{error}</p>}
      <div ref={host} style={{ height: 520, width: '100%' }} />
      <p className="caption">Native computational face boundaries with saved cell bed elevations and water depth. Drag to orbit, right drag to pan, scroll to zoom. Heights exaggerated {exaggeration}×. Surrounding terrain and buildings are not supplied by this output. This is a 3D display of a 2D solver, not a full 3D hydraulic solution.</p>
    </div>
  </section>;
}
