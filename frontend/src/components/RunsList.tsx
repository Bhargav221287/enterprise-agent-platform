import React from 'react';
import { RunResponse } from '../types';
import { StatusBadge } from './StatusBadge';

interface RunsListProps {
  runs: RunResponse[];
  onSelectRun: (runId: string) => void;
  onRefresh: () => void;
  loading: boolean;
}

export const RunsList: React.FC<RunsListProps> = ({
  runs,
  onSelectRun,
  onRefresh,
  loading,
}) => {
  return (
    <div className="card">
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '18px',
        }}
      >
        <div>
          <h2 style={{ fontSize: '20px' }}>Workflow Execution Runs</h2>
          <p style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
            Historical record of all domain workflows with status, confidence metrics, and step traces.
          </p>
        </div>
        <button
          className="btn btn-secondary"
          onClick={onRefresh}
          disabled={loading}
        >
          {loading ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>

      {runs.length === 0 ? (
        <div
          style={{
            textAlign: 'center',
            padding: '48px 0',
            color: 'var(--text-muted)',
          }}
        >
          No workflow runs recorded yet. Launch one from the "Run Workflow" tab!
        </div>
      ) : (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Run ID</th>
                <th>Domain Pack</th>
                <th>Status</th>
                <th>Confidence</th>
                <th>Steps</th>
                <th>Created At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((run) => (
                <tr key={run.run_id}>
                  <td>
                    <span
                      style={{
                        fontFamily: 'monospace',
                        fontWeight: 600,
                        color: 'var(--primary)',
                      }}
                    >
                      {run.run_id.slice(0, 8)}...
                    </span>
                  </td>
                  <td>
                    <strong>{run.pack_name}</strong>
                  </td>
                  <td>
                    <StatusBadge status={run.status} />
                  </td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '70px',
                          height: '8px',
                          background: '#e2e8f0',
                          borderRadius: '4px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.round(run.confidence * 100)}%`,
                            height: '100%',
                            background:
                              run.confidence >= 0.75
                                ? '#16a34a'
                                : run.confidence >= 0.6
                                ? '#d97706'
                                : '#dc2626',
                          }}
                        />
                      </div>
                      <span style={{ fontSize: '12px', fontWeight: 600 }}>
                        {Math.round(run.confidence * 100)}%
                      </span>
                    </div>
                  </td>
                  <td>{run.trace_steps.length} steps</td>
                  <td style={{ color: 'var(--text-muted)', fontSize: '13px' }}>
                    {new Date(run.created_at).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </td>
                  <td>
                    <button
                      className="btn btn-secondary"
                      style={{ padding: '6px 12px', fontSize: '12px' }}
                      onClick={() => onSelectRun(run.run_id)}
                    >
                      View Details
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
};
