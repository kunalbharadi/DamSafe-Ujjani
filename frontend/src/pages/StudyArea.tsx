import React from 'react';
import type { Project } from '../types';
import { StudyAreaMap } from '../components/FloodMap2D';

type StudyAreaProps = {
  project: Project | null;
};

export function StudyArea({ project }: StudyAreaProps) {
  const bounds = project?.verified_bounds_wgs84 ?? null;

  return (
    <div id="page-study-area">
      <div className="page-header">
        <div className="page-eyebrow">Study Area</div>
        <h1 className="page-title">Ujjani Dam — Bhima River</h1>
        <p className="page-subtitle">
          Geographic extent of the hydrodynamic model domain. Dam marker, reservoir extent, river reach, and model boundary shown.
        </p>
      </div>

      <div className="two-col-6040" style={{ marginBottom: 24 }}>
        {/* Main map */}
        <div className="card" style={{ overflow: 'hidden' }}>
          <div className="card-header">
            <span className="card-title">Model Domain</span>
            <div style={{ display: 'flex', gap: 8 }}>
              <span className="badge badge-blue">WGS84</span>
              <span className="badge badge-orange">Bhima Basin</span>
            </div>
          </div>
          <StudyAreaMap bounds={bounds} height={460} />
          <div className="card-footer caption">
            MapLibre GL · OpenStreetMap base · Orange dashed line = model domain boundary · Orange dot = Ujjani Dam
          </div>
        </div>

        {/* Metadata panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Dam metadata */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Dam Details</span>
              <span className="badge badge-orange">Ujjani</span>
            </div>
            <div className="card-body">
              <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="detail-item">
                  <span className="detail-label">Dam Name</span>
                  <span className="detail-value">Ujjani Dam</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">River</span>
                  <span className="detail-value">Bhima River</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">State</span>
                  <span className="detail-value">Maharashtra</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">District</span>
                  <span className="detail-value">Solapur</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Coordinates</span>
                  <span className="detail-value" style={{ fontSize: 12 }}>18.05°N, 75.10°E</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Dam Height</span>
                  <span className="detail-value">
                    ~65 m <span className="badge badge-assumption">ASSUMPTION</span>
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Reservoir Capacity</span>
                  <span className="detail-value">
                    ~3.3 TMC <span className="badge badge-assumption">ASSUMPTION</span>
                  </span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Type</span>
                  <span className="detail-value">Earthen Masonry</span>
                </div>
              </div>
            </div>
          </div>

          {/* Project metadata */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Model Configuration</span>
            </div>
            <div className="card-body">
              <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="detail-item">
                  <span className="detail-label">Site Key</span>
                  <span className="detail-value"><code>{project?.site_key ?? 'ujjani-bhima'}</code></span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Computation CRS</span>
                  <span className="detail-value"><code>{project?.computation_crs ?? 'EPSG:32643'}</code></span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Vertical Datum</span>
                  <span className="detail-value">{project?.vertical_reference ?? 'MSL (assumed)'}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Domain</span>
                  <span className="detail-value" style={{ fontSize: 11 }}>
                    {bounds
                      ? `${bounds[0].toFixed(2)}°E–${bounds[2].toFixed(2)}°E, ${bounds[1].toFixed(2)}°N–${bounds[3].toFixed(2)}°N`
                      : 'Not verified'}
                  </span>
                </div>
              </div>

              {/* Domain status */}
              <div style={{ marginTop: 12 }}>
                {bounds ? (
                  <div className="alert alert-success" style={{ marginBottom: 0 }}>
                    ✓ Verified model bounds on file ({bounds[0].toFixed(2)}°–{bounds[2].toFixed(2)}°E, {bounds[1].toFixed(2)}°–{bounds[3].toFixed(2)}°N)
                  </div>
                ) : (
                  <div className="alert alert-warning" style={{ marginBottom: 0 }}>
                    ⚠ Model domain bounds not yet verified. Shown bounds are indicative only.
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* River metadata */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">River System</span>
            </div>
            <div className="card-body">
              <div className="detail-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
                <div className="detail-item">
                  <span className="detail-label">River</span>
                  <span className="detail-value">Bhima River</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Basin</span>
                  <span className="detail-value">Krishna Basin</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Reach</span>
                  <span className="detail-value">Upstream of Pandharpur</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Flow Direction</span>
                  <span className="detail-value">West → East → South</span>
                </div>
              </div>
              <p className="caption" style={{ marginTop: 12 }}>
                Geometry marked <span className="badge badge-assumption">ASSUMPTION</span> has not been verified from surveyed cross-sections.
                Use Data Setup to upload verified river geometry.
              </p>
            </div>
          </div>

          {/* Future dam selector */}
          <div className="card">
            <div className="card-header">
              <span className="card-title">Dam Selection</span>
              <span className="badge badge-not-implemented">Future Release</span>
            </div>
            <div className="card-body">
              <div className="not-implemented-box">
                <span>🔒</span>
                <span>Multi-dam selection is planned for a future release. The current demonstration is fixed to Ujjani Dam on the Bhima River.</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
