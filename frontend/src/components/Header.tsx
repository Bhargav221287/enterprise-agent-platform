import React from 'react';

interface HeaderProps {
  activeTab: 'run' | 'list' | 'detail';
  setActiveTab: (tab: 'run' | 'list') => void;
  selectedRunId: string | null;
  serverHealth: boolean | null;
}

export const Header: React.FC<HeaderProps> = ({
  activeTab,
  setActiveTab,
  selectedRunId,
  serverHealth,
}) => {
  return (
    <header className="navbar">
      <div className="brand">
        <div className="brand-icon">E</div>
        <div>
          <span>Enterprise Agent Platform</span>
          <span
            style={{
              fontSize: '11px',
              fontWeight: 400,
              display: 'block',
              color: 'var(--text-muted)',
            }}
          >
            Multi-Agent Orchestration &amp; Code Verification
          </span>
        </div>
      </div>

      <nav className="nav-links">
        <button
          className={`nav-btn ${activeTab === 'run' ? 'active' : ''}`}
          onClick={() => setActiveTab('run')}
        >
          Run Workflow
        </button>
        <button
          className={`nav-btn ${activeTab === 'list' ? 'active' : ''}`}
          onClick={() => setActiveTab('list')}
        >
          Workflows List
        </button>
        {selectedRunId && (
          <button
            className={`nav-btn ${activeTab === 'detail' ? 'active' : ''}`}
            disabled
          >
            Run #{selectedRunId.slice(0, 8)}
          </button>
        )}
      </nav>

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px' }}>
        <span
          style={{
            width: '8px',
            height: '8px',
            borderRadius: '50%',
            background: serverHealth ? '#16a34a' : '#ef4444',
            display: 'inline-block',
          }}
        />
        <span style={{ color: 'var(--text-secondary)' }}>
          {serverHealth ? 'System Operational' : 'Connecting...'}
        </span>
      </div>
    </header>
  );
};
