import React, { useState } from 'react';
import type { ExposureResult, NumericalRun, Project } from '../types';
import { StatusBadge, DataRequiredBox } from '../components/StatusBadge';
import { getExposure } from '../api';

type ImpactHadrProps = {
  project: Project | null;
  runs: NumericalRun[];
  onError: (e: string) => void;
  onNotice: (n: string) => void;
};

export function ImpactHadr({ project, runs, onError, onNotice }: ImpactHadrProps) {
  const [selectedRunId, setSelectedRunId] = useState('');
  const [exposure, setExposure] = useState<ExposureResult | null>(null);
  const [loading, setLoading] = useState(false);

  const succeededRuns = runs.filter((r) => r.state === 'SUCCEEDED');

  async function handleEvaluate() {
    if (!project || !selectedRunId) return;
    setLoading(true);
    try {
      const result = await getExposure(project.id, selectedRunId);
      setExposure(result);
      onNotice('Exposure evaluation complete. DATA REQUIRED fields are not estimates — they require supplementary input data.');
    } catch (e) {
      onError(String(e));
    } finally {
      setLoading(false);
    }
  }

  const settlements = exposure?.settlements;
  const ag = exposure?.agricultural_area_km2;
  const roads = exposure?.roads_km;
  const infra = exposure?.critical_infrastructure;
  const riskZones = exposure?.risk_zones;

  return (
    <div id="page-impact">
      <div className="page-header">
        <div className="page-eyebrow">⑦ Impact &amp; HADR</div>
        <h1 className="page-title">Exposure &amp; Disaster Response</h1>
        <p className="page-subtitle">
          Evaluate the flood footprint against exposed assets. Population, monetary loss, and evacuation
          routes require supplementary data — they are labeled DATA REQUIRED, not estimated.
        </p>
      </div>

      {/* Run selector */}
      <div className="card" style={{ marginBottom: 20 }}>
        <div className="card-body" style={{ padding: 16 }}>
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', flexWrap: 'wrap' }}>
            <div className="form-group" style={{ marginBottom: 0, minWidth: 320 }}>
              <label className="form-label">Numerical Run</label>
              <select
                id="impact-run-select"
                className="form-select"
                value={selectedRunId}
                onChange={(e) => setSelectedRunId(e.target.value)}
              >
                <option value="">— Select a succeeded run —</option>
                {succeededRuns.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.id.slice(0, 16)}… · {r.input.request.engine}
                  </option>
                ))}
              </select>
            </div>
            <button
              id="btn-evaluate-exposure"
              className="btn btn-primary"
              disabled={loading || !selectedRunId || !project}
              onClick={handleEvaluate}
            >
              {loading ? <span className="spinner" /> : '🔍'} Evaluate Exposure
            </button>
          </div>
        </div>
      </div>

      {/* Exposure results grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 16, marginBottom: 24 }}>
        {/* Settlements */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🏘 Settlements</span>
            <StatusBadge value={settlements?.status ?? 'DATA REQUIRED'} />
          </div>
          <div className="card-body">
            {settlements?.count != null ? (
              <div>
                <div className="stat-value" style={{ fontSize: 32 }}>{settlements.count}</div>
                <div className="stat-sub">settlements potentially affected by flood extent</div>
                {settlements.note && <p className="caption" style={{ marginTop: 8 }}>{settlements.note}</p>}
              </div>
            ) : (
              <DataRequiredBox
                label="DATA REQUIRED"
                reason={settlements?.note ?? 'Settlement data not loaded. Upload village/town shapefile to Data Setup.'}
              />
            )}
          </div>
        </div>

        {/* Agricultural area */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🌾 Agricultural Area</span>
            <StatusBadge value={ag?.status ?? 'DATA REQUIRED'} />
          </div>
          <div className="card-body">
            {ag?.value != null ? (
              <div>
                <div className="stat-value blue" style={{ fontSize: 32 }}>{ag.value} km²</div>
                <div className="stat-sub">agricultural area within flood extent</div>
                {ag.note && <p className="caption" style={{ marginTop: 8 }}>{ag.note}</p>}
              </div>
            ) : (
              <DataRequiredBox
                label="DATA REQUIRED"
                reason={ag?.note ?? 'Agricultural land-use data not available. Upload LULC raster.'}
              />
            )}
          </div>
        </div>

        {/* Roads */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">🛣 Roads</span>
            <StatusBadge value={roads?.status ?? 'DATA REQUIRED'} />
          </div>
          <div className="card-body">
            {roads?.value != null ? (
              <div>
                <div className="stat-value" style={{ fontSize: 32 }}>{roads.value} km</div>
                <div className="stat-sub">road length within flood extent</div>
                {roads.note && <p className="caption" style={{ marginTop: 8 }}>{roads.note}</p>}
              </div>
            ) : (
              <DataRequiredBox
                label="DATA REQUIRED"
                reason={roads?.note ?? 'Road network data not available. Upload OSM or NHD road network.'}
              />
            )}
          </div>
        </div>

        {/* Critical infrastructure */}
        <div className="card">
          <div className="card-header">
            <span className="card-title">⚡ Critical Infrastructure</span>
            <StatusBadge value={infra?.status ?? 'DATA REQUIRED'} />
          </div>
          <div className="card-body">
            {infra?.items != null ? (
              <div>
                <div className="stat-value" style={{ fontSize: 32 }}>{(infra.items as unknown[]).length}</div>
                <div className="stat-sub">infrastructure assets within flood extent</div>
                {infra.note && <p className="caption" style={{ marginTop: 8 }}>{infra.note}</p>}
              </div>
            ) : (
              <DataRequiredBox
                label="DATA REQUIRED"
                reason={infra?.note ?? 'Infrastructure point data not available. Upload power/hospital/water assets.'}
              />
            )}
          </div>
        </div>

        {/* Risk zones */}
        <div className="card" style={{ gridColumn: '1 / -1' }}>
          <div className="card-header">
            <span className="card-title">⚠ Risk Zones</span>
            <StatusBadge value={riskZones?.status ?? 'DATA REQUIRED'} />
          </div>
          <div className="card-body">
            {riskZones?.zones ? (
              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                {riskZones.zones.map((z) => {
                  const cls =
                    z.level === 'EXTREME' ? 'badge-red'
                    : z.level === 'HIGH' ? 'badge-orange'
                    : z.level === 'MODERATE' ? 'badge-amber'
                    : 'badge-green';
                  return (
                    <div key={z.level} className="card" style={{ padding: 16, minWidth: 120, textAlign: 'center' }}>
                      <span className={`badge ${cls}`} style={{ marginBottom: 8 }}>{z.level}</span>
                      <div style={{ fontSize: 22, fontWeight: 800 }}>{z.cells}</div>
                      <div style={{ fontSize: 11, color: '#64748B' }}>cells</div>
                    </div>
                  );
                })}
              </div>
            ) : (
              <DataRequiredBox
                label="DATA REQUIRED"
                reason={riskZones?.note ?? 'Risk zone classification not available. Run flood classification analysis first.'}
              />
            )}
          </div>
        </div>
      </div>

      {/* Not-implemented sections */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">👥 Population at Risk</span>
          <span className="badge badge-data-required">DATA REQUIRED</span>
        </div>
        <div className="card-body">
          <DataRequiredBox
            label="DATA REQUIRED"
            reason="Population count within flood extent requires census grid (WorldPop / Census of India). Not available in current data setup. Upload gridded population raster to enable."
          />
          <p className="caption" style={{ marginTop: 8 }}>
            Population estimates are <strong>not generated from simulation results alone</strong>.
            Do not extrapolate from cell count or area without demographic input data.
          </p>
        </div>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="card-header">
          <span className="card-title">💰 Monetary Loss Estimate</span>
          <span className="badge badge-data-required">DATA REQUIRED</span>
        </div>
        <div className="card-body">
          <DataRequiredBox
            label="DATA REQUIRED"
            reason="Economic impact assessment requires asset inventory, property valuations, and crop damage models — none of which are available in the current data setup."
          />
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <span className="card-title">🚁 HADR Response Priorities</span>
          <span className="badge badge-data-required">DATA REQUIRED</span>
        </div>
        <div className="card-body">
          <p style={{ fontSize: 13, color: '#64748B', marginBottom: 12, lineHeight: 1.6 }}>
            HADR (Humanitarian Assistance and Disaster Response) priorities — relief staging areas,
            helicopter landing zones, evacuation corridors, early warning dissemination — require
            integration with NDRF/SDRF operational data and road accessibility analysis.
          </p>
          <DataRequiredBox
            label="DATA REQUIRED"
            reason="HADR planning requires evacuation route network (road accessibility under flood), NDRF staging areas, and community vulnerability index. Upload supplementary data to enable."
          />
        </div>
      </div>
    </div>
  );
}
