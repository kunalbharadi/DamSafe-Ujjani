import React from 'react';
import type { Page } from '../types';

type NavItem = {
  id: Page;
  label: string;
  icon: string;
  step: string;
};

const NAV_ITEMS: NavItem[] = [
  { id: 'dashboard',        label: 'Dashboard',        icon: '⌂', step: '' },
  { id: 'study-area',       label: 'Study Area',       icon: '🗺', step: '①' },
  { id: 'data-setup',       label: 'Data Setup',       icon: '📊', step: '②' },
  { id: 'scenario-builder', label: 'Scenario Builder', icon: '⚙', step: '③' },
  { id: 'simulation',       label: 'Simulation',       icon: '▶', step: '④' },
  { id: 'results',          label: 'Results',          icon: '🌊', step: '⑤' },
  { id: 'validation',       label: 'Validation',       icon: '✓', step: '⑥' },
  { id: 'impact',           label: 'Impact & HADR',    icon: '🚨', step: '⑦' },
  { id: 'reports',          label: 'Reports & Export', icon: '↓', step: '⑧' },
];

type SidebarProps = {
  active: Page;
  onNavigate: (page: Page) => void;
  projectName?: string;
  isPreview?: boolean;
  hasSucceededRun?: boolean;
};

export function Sidebar({ active, onNavigate, projectName, isPreview, hasSucceededRun }: SidebarProps) {
  return (
    <aside className="sidebar" role="navigation" aria-label="Main navigation">
      {/* Brand */}
      <div className="sidebar-header">
        <div className="brand">
          <svg className="brand-icon" viewBox="0 0 48 48" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="5" strokeLinecap="round">
            <path d="M4 13 Q14 2 24 13 T44 13 M4 25 Q14 14 24 25 T44 25 M4 37 Q14 26 24 37 T44 37" />
          </svg>
          <span className="brand-name">DamSafe</span>
        </div>
        <div className="brand-tagline">
          Dam Break Inundation Modelling<br />
          &amp; Decision Support System
        </div>
      </div>

      {/* Project indicator */}
      <div className="sidebar-project">
        <div className="sidebar-project-label">Active Project</div>
        <div className="sidebar-project-name">
          {projectName ?? 'Ujjani Dam · Bhima River'}
        </div>
        <div className="sidebar-project-sub">Maharashtra · SIH PS 26161</div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Workflow</div>
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            id={`nav-${item.id}`}
            className={`nav-item${active === item.id ? ' active' : ''}`}
            onClick={() => onNavigate(item.id)}
            aria-current={active === item.id ? 'page' : undefined}
          >
            <span className="nav-item-icon" aria-hidden="true">{item.icon}</span>
            <span>{item.label}</span>
            {item.step && (
              <span className="nav-item-step">{item.step}</span>
            )}
          </button>
        ))}
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <span className="sidebar-footer-dot" />
        {isPreview ? 'SQLite preview mode' : 'Connected'}
        <br />
        <span style={{ color: '#475569', fontSize: 10 }}>
          {hasSucceededRun ? '✓ Run available' : 'No run yet'}
        </span>
      </div>
    </aside>
  );
}
