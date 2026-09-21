import React, { useEffect, useRef, useState } from 'react';
import type { Map as LibreMap } from 'maplibre-gl';
import type { ResultCell, ResultFrame } from '../types';

// ─── Ujjani Dam Geographic Constants ─────────────────────────────────────────
// Repository site reference (site/ujjani.py); primary-source review still required.
export const UJJANI_DAM_LNG = 75.1197;
export const UJJANI_DAM_LAT = 18.0772;

// ─── EPSG:32643 (UTM Zone 43N) → WGS84 projection ───────────────────────────
// proj4 import — used for cell coordinate transformation
let proj4: ((from: string, to: string, coord: [number, number]) => [number, number]) | null = null;
let projReady = false;
let projLoading = false;
const projCallbacks: Array<() => void> = [];

async function ensureProj4() {
  if (projReady) return;
  if (projLoading) {
    await new Promise<void>((resolve) => projCallbacks.push(resolve));
    return;
  }
  projLoading = true;
  const mod = await import('proj4');
  const p4 = mod.default ?? mod;
  // Register UTM Zone 43N
  (p4 as any).defs(
    'EPSG:32643',
    '+proj=utm +zone=43 +datum=WGS84 +units=m +no_defs'
  );
  proj4 = (from: string, to: string, coord: [number, number]) =>
    (p4 as any)(from, to, coord) as [number, number];
  projReady = true;
  projCallbacks.forEach((cb) => cb());
  projCallbacks.length = 0;
}

function utmToWgs84(x: number, y: number): [number, number] {
  if (!proj4) return [0, 0];
  try {
    const [lng, lat] = proj4('EPSG:32643', 'EPSG:4326', [x, y]);
    return [lng, lat];
  } catch {
    return [0, 0];
  }
}

// ─── Depth → RGBA colour (blue depth scale) ──────────────────────────────────
function depthColor(depth: number): string {
  if (depth < 0.5) return '#93C5FD';
  if (depth < 1) return '#60A5FA';
  if (depth < 2) return '#3B82F6';
  if (depth < 5) return '#2563EB';
  return '#1D4ED8';
}

function velocityColor(vel: number): string {
  if (vel < 0.5) return '#7FB3D5';
  if (vel < 1.0) return '#2980B9';
  if (vel < 2.0) return '#F59E0B';
  return '#DC2626';
}

// ─── Component ────────────────────────────────────────────────────────────────
type FloodMap2DProps = {
  bounds: [number, number, number, number] | null; // WGS84 [W, S, E, N]
  cells: ResultCell[];
  frame: ResultFrame | null;
  field: 'h' | 'velocity_magnitude';
  crs: string | null;
  showDamMarker?: boolean;
};

export function FloodMap2D({
  bounds,
  cells,
  frame,
  field,
  crs,
  showDamMarker = true,
}: FloodMap2DProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<LibreMap | null>(null);
  const cellsLoadedRef = useRef(false);
  const [mapReady, setMapReady] = useState(false);

  // Initialize map
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    let disposed = false;
    let mapInstance: LibreMap | null = null;

    (async () => {
      await ensureProj4();
      if (disposed) return;

      const lib = await import('maplibre-gl');
      if (disposed || !container) return;

      const [w, s, e, n] = bounds ?? [74.6, 17.65, 75.95, 18.35];

      const instance = new lib.Map({
        container,
        style: {
          version: 8,
          sources: {
            'osm-tiles': {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors',
              maxzoom: 18,
            },
          },
          layers: [
            {
              id: 'osm-layer',
              type: 'raster',
              source: 'osm-tiles',
              paint: { 'raster-opacity': 0.7 },
            },
          ],
        },
        bounds: [[w, s], [e, n]],
        fitBoundsOptions: { padding: 40 },
      });

      instance.addControl(new lib.NavigationControl(), 'top-left');
      instance.addControl(new lib.ScaleControl({ maxWidth: 100, unit: 'metric' }), 'bottom-left');

      instance.on('load', () => {
        if (disposed) return;

        // Model domain bounding box
        instance.addSource('domain', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: {
              type: 'Polygon',
              coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
            },
          },
        });
        instance.addLayer({
          id: 'domain-border',
          type: 'line',
          source: 'domain',
          paint: { 'line-color': '#F97316', 'line-width': 2, 'line-dasharray': [4, 3] },
        });

        // Flood cells source (initially empty)
        instance.addSource('flood-cells', {
          type: 'geojson',
          data: { type: 'FeatureCollection', features: [] },
        });
        instance.addLayer({
          id: 'flood-circles',
          type: 'circle',
          source: 'flood-cells',
          filter: ['==', ['geometry-type'], 'Point'],
          paint: {
            'circle-radius': ['get', 'radius'],
            'circle-color': ['get', 'color'],
            'circle-opacity': 0.85,
          },
        });

        instance.addLayer({
          id: 'flood-polygons', type: 'fill', source: 'flood-cells',
          filter: ['==', ['geometry-type'], 'Polygon'],
          paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.75, 'fill-outline-color': '#334155' },
        });

        // Dam marker
        if (showDamMarker) {
          instance.addSource('dam', {
            type: 'geojson',
            data: {
              type: 'Feature',
              properties: { name: 'Ujjani Dam' },
              geometry: { type: 'Point', coordinates: [UJJANI_DAM_LNG, UJJANI_DAM_LAT] },
            },
          });
          instance.addLayer({
            id: 'dam-dot',
            type: 'circle',
            source: 'dam',
            paint: {
              'circle-radius': 8,
              'circle-color': '#F97316',
              'circle-stroke-color': '#fff',
              'circle-stroke-width': 2,
            },
          });
        }
      });

      instance.on('load', () => { if (!disposed) setMapReady(true); });
      mapRef.current = instance;
      mapInstance = instance;
    })();

    return () => {
      disposed = true;
      mapInstance?.remove();
      mapRef.current = null;
      cellsLoadedRef.current = false;
      setMapReady(false);
    };
  }, [bounds, showDamMarker]);

  // Update flood cells when frame changes
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !projReady || !mapReady) return;
    if (!map.isStyleLoaded()) return;

    const source = map.getSource('flood-cells') as import('maplibre-gl').GeoJSONSource | undefined;
    if (!source) return;
    if (!frame || (crs !== 'EPSG:32643' && crs !== 'EPSG:4326')) {
      source.setData({ type: 'FeatureCollection', features: [] });
      return;
    }

    const features: GeoJSON.Feature[] = [];

    for (let i = 0; i < cells.length; i++) {
      const cell = cells[i];
      const state = frame.states[i];
      const [lng, lat] = crs === 'EPSG:4326' ? [cell.x, cell.y] : utmToWgs84(cell.x, cell.y);
      if (!isFinite(lng) || !isFinite(lat)) continue;

      let color = state === 'NODATA' ? '#475569' : '#94A3B8';
      if (state === 'WET') {
        const val = frame.values[i];
        if (val != null) {
          color = field === 'h' ? depthColor(val) : velocityColor(val);
        } else {
          color = '#60A5FA';
        }
      }

      const radius = Math.max(3, Math.min(12, Math.sqrt(cell.area_m2) / 300));

      features.push({
        type: 'Feature',
        properties: { color, radius, state, value: frame.values[i] },
        geometry: cell.polygon
          ? { type: 'Polygon', coordinates: [cell.polygon.map(([x, y]) => crs === 'EPSG:4326' ? [x, y] : utmToWgs84(x, y))] }
          : { type: 'Point', coordinates: [lng, lat] },
      });
    }

    source.setData({ type: 'FeatureCollection', features });
    if (!cellsLoadedRef.current && cells.length) {
      const coordinates = cells.flatMap(cell => cell.polygon ?? [[cell.x, cell.y] as [number, number]])
        .map(([x, y]) => crs === 'EPSG:4326' ? [x, y] : utmToWgs84(x, y));
      const xs = coordinates.map(p => p[0]), ys = coordinates.map(p => p[1]);
      map.fitBounds([[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]],
        { padding: 65, maxZoom: 16, duration: 0 });
      cellsLoadedRef.current = true;
    }
  }, [cells, frame, field, crs, mapReady]);

  // Handle case where cells/frame arrive before map finishes loading
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    const onLoad = () => {
      // Re-trigger frame update after map load
    };
    map.on('load', onLoad);
    return () => { map.off('load', onLoad); };
  }, []);

  return (
    <div className="flood-map-container">
      <div
        ref={containerRef}
        className="flood-map-inner"
        aria-label="Geographic flood extent map"
      />
      {/* Legend */}
      <div className="flood-legend">
        <div className="flood-legend-title">
          {field === 'h' ? 'Water Depth (m)' : 'Velocity (m/s)'}
        </div>
        {field === 'h' ? (
          <>
            {['< 0.5', '0.5 – 1', '1 – 2', '2 – 5', '≥ 5'].map((label, i) =>
              <div className="legend-row" key={label}><div className="legend-swatch" style={{ background: depthColor([0, .5, 1, 2, 5][i]) }} /><span>{label} m</span></div>)}
          </>
        ) : (
          <>
            <div className="legend-row"><div className="legend-swatch" style={{ background: '#7FB3D5' }} /><span>&lt; 0.5 m/s</span></div>
            <div className="legend-row"><div className="legend-swatch" style={{ background: '#2980B9' }} /><span>0.5 – 1 m/s</span></div>
            <div className="legend-row"><div className="legend-swatch" style={{ background: '#F59E0B' }} /><span>1 – 2 m/s</span></div>
            <div className="legend-row"><div className="legend-swatch" style={{ background: '#DC2626' }} /><span>≥ 2 m/s</span></div>
          </>
        )}
        <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '6px 0' }} />
        <div className="legend-row"><div className="legend-swatch" style={{ background: '#94A3B8' }} /><span>Dry</span></div>
        <div className="legend-row" style={{ opacity: 0.6 }}><div className="legend-swatch" style={{ background: '#475569', border: '1px dashed #64748B' }} /><span>Nodata</span></div>
        <hr style={{ border: 'none', borderTop: '1px solid rgba(255,255,255,0.1)', margin: '6px 0' }} />
        <div className="legend-row"><div style={{ width: 14, height: 14, background: '#F97316', borderRadius: '50%', border: '2px solid white' }} /><span>Ujjani Dam</span></div>
        <div className="legend-row" style={{ borderTop: '1px dashed #F97316', padding: '4px 0 0', marginTop: 2 }}><span style={{ fontSize: 10, color: '#F97316' }}>— Model Domain</span></div>
      </div>
    </div>
  );
}

// ─── Simple study-area preview (no cells, just bounds + dam marker) ───────────
type StudyMapProps = {
  bounds: [number, number, number, number] | null;
  height?: number;
};

export function StudyAreaMap({ bounds, height = 420 }: StudyMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    let disposed = false;
    let mapInstance: LibreMap | null = null;

    (async () => {
      const lib = await import('maplibre-gl');
      if (disposed || !container) return;

      const [w, s, e, n] = bounds ?? [74.6, 17.65, 75.95, 18.35];

      const instance = new lib.Map({
        container,
        style: {
          version: 8,
          sources: {
            'osm-tiles': {
              type: 'raster',
              tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
              tileSize: 256,
              attribution: '© OpenStreetMap contributors',
            },
          },
          layers: [{ id: 'osm', type: 'raster', source: 'osm-tiles' }],
        },
        bounds: [[w, s], [e, n]],
        fitBoundsOptions: { padding: 50 },
      });

      instance.addControl(new lib.NavigationControl(), 'top-left');

      instance.on('load', () => {
        if (disposed) return;

        // Domain bounding box
        instance.addSource('domain', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: {},
            geometry: {
              type: 'Polygon',
              coordinates: [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
            },
          },
        });
        instance.addLayer({
          id: 'domain-fill',
          type: 'fill',
          source: 'domain',
          paint: { 'fill-color': '#2563EB', 'fill-opacity': 0.06 },
        });
        instance.addLayer({
          id: 'domain-line',
          type: 'line',
          source: 'domain',
          paint: { 'line-color': '#F97316', 'line-width': 2, 'line-dasharray': [5, 3] },
        });

        // Dam marker
        instance.addSource('dam-marker', {
          type: 'geojson',
          data: {
            type: 'Feature',
            properties: { label: 'Ujjani Dam' },
            geometry: { type: 'Point', coordinates: [UJJANI_DAM_LNG, UJJANI_DAM_LAT] },
          },
        });
        instance.addLayer({
          id: 'dam-circle',
          type: 'circle',
          source: 'dam-marker',
          paint: {
            'circle-radius': 10,
            'circle-color': '#F97316',
            'circle-stroke-color': '#fff',
            'circle-stroke-width': 3,
          },
        });

        // Popup on dam marker
        const popup = new lib.Popup({ offset: 20 })
          .setHTML('<strong>Ujjani Dam</strong><br>Bhima River, Maharashtra<br>18.05°N 75.10°E');
        instance.on('click', 'dam-circle', (e) => {
          if (e.lngLat) popup.setLngLat(e.lngLat).addTo(instance);
        });
        instance.on('mouseenter', 'dam-circle', () => {
          instance.getCanvas().style.cursor = 'pointer';
        });
        instance.on('mouseleave', 'dam-circle', () => {
          instance.getCanvas().style.cursor = '';
        });
      });

      mapRef.current = instance;
      mapInstance = instance;
    })();

    return () => {
      disposed = true;
      mapInstance?.remove();
    };
  }, [bounds]);

  const mapRef = useRef<LibreMap | null>(null);

  return (
    <div
      ref={containerRef}
      className="map-container"
      style={{ height }}
      aria-label="Ujjani Dam study area map"
    />
  );
}
