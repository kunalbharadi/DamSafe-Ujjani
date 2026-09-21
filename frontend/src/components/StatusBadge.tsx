import React from 'react';

type StatusBadgeProps = {
  value: string;
  className?: string;
};

const STATUS_MAP: Record<string, string> = {
  // Run states
  SUCCEEDED: 'badge-succeeded',
  RUNNING: 'badge-running',
  QUEUED: 'badge-queued',
  FAILED: 'badge-failed',
  CANCELLED: 'badge-cancelled',
  // Data states
  AVAILABLE: 'badge-succeeded',
  ASSUMPTION: 'badge-assumption',
  'DATA REQUIRED': 'badge-data-required',
  BLOCKED: 'badge-blocked',
  // Validation
  NOT_VALIDATED: 'badge-gray',
  NOT_IMPLEMENTED: 'badge-not-implemented',
  UNAVAILABLE: 'badge-gray',
  // Input mode
  OBSERVED: 'badge-blue',
  MIXED_ASSUMPTIONS: 'badge-amber',
  SYNTHETIC: 'badge-dark',
  // Engine states
  available: 'badge-succeeded',
  unavailable: 'badge-gray',
};

export function StatusBadge({ value = 'UNASSESSED', className = '' }: StatusBadgeProps) {
  const cls = STATUS_MAP[value] ?? STATUS_MAP[value.toUpperCase()] ?? 'badge-gray';
  return (
    <span className={`badge ${cls} ${className}`}>{value}</span>
  );
}

type DataRequiredBoxProps = {
  label?: string;
  reason?: string;
};

export function DataRequiredBox({ label = 'DATA REQUIRED', reason }: DataRequiredBoxProps) {
  return (
    <div className="data-required-box">
      <span className="badge badge-data-required">{label}</span>
      {reason && <p style={{ marginTop: 6, fontSize: 12 }}>{reason}</p>}
    </div>
  );
}

export function NotImplementedBox({ feature }: { feature: string }) {
  return (
    <div className="not-implemented-box">
      <span className="badge badge-not-implemented">NOT IMPLEMENTED</span>
      <span>{feature} is not implemented in the current backend.</span>
    </div>
  );
}
