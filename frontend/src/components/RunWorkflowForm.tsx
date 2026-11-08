import React, { useState } from 'react';
import { PackSummary, RunResponse } from '../types';
import { createRun } from '../api/client';

interface RunWorkflowFormProps {
  packs: PackSummary[];
  onRunCreated: (run: RunResponse) => void;
}

const TEMPLATES: Record<string, Record<string, any>> = {
  'it_ticket_triage:standard': {
    ticket_id: 'INC-1001',
    issue: 'Users reporting connection timeouts to corporate production VPN',
    priority: 'High',
    reporter: 'alice@company.com',
  },
  'it_ticket_triage:critical': {
    ticket_id: 'INC-SEC-09',
    issue: 'critical database unauthorized root access attempts detected',
    priority: 'Critical',
    reporter: 'security-bot@company.com',
  },
  'loan_prescreening:prime': {
    applicant_id: 'APP-501',
    full_name: 'Jane Doe',
    requested_loan_amount: 450000,
    annual_income: 114000,
    property_value: 600000,
  },
  'loan_prescreening:high_dti': {
    applicant_id: 'APP-502',
    full_name: 'John Smith',
    requested_loan_amount: 800000,
    annual_income: 84000,
    property_value: 950000,
  },
};

export const RunWorkflowForm: React.FC<RunWorkflowFormProps> = ({
  packs,
  onRunCreated,
}) => {
  const [selectedPack, setSelectedPack] = useState<string>(
    packs[0]?.name || 'it_ticket_triage'
  );
  const [sessionId, setSessionId] = useState<string>('session-demo-1');
  const [jsonInput, setJsonInput] = useState<string>(
    JSON.stringify(TEMPLATES['it_ticket_triage:standard'], null, 2)
  );
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const currentPackMeta = packs.find((p) => p.name === selectedPack);

  const handlePackChange = (packName: string) => {
    setSelectedPack(packName);
    const defaultTemplateKey = `${packName}:standard` in TEMPLATES
      ? `${packName}:standard`
      : Object.keys(TEMPLATES).find((k) => k.startsWith(packName)) || '';
    if (defaultTemplateKey && TEMPLATES[defaultTemplateKey]) {
      setJsonInput(JSON.stringify(TEMPLATES[defaultTemplateKey], null, 2));
    }
  };

  const handleLoadTemplate = (key: string) => {
    if (TEMPLATES[key]) {
      setJsonInput(JSON.stringify(TEMPLATES[key], null, 2));
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const parsedData = JSON.parse(jsonInput);
      const res = await createRun({
        pack_name: selectedPack,
        input_data: parsedData,
        session_id: sessionId.trim() || undefined,
      });
      onRunCreated(res);
    } catch (err: any) {
      setError(err.message || 'Invalid JSON format or server request failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2 style={{ fontSize: '20px', marginBottom: '8px' }}>Launch Domain Workflow</h2>
      <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '20px' }}>
        Select a validated domain pack and supply initial business event data. The orchestrator dynamically builds and runs the multi-agent graph.
      </p>

      {error && (
        <div
          style={{
            background: '#fee2e2',
            border: '1px solid #f87171',
            color: '#b91c1c',
            padding: '12px',
            borderRadius: 'var(--radius-sm)',
            marginBottom: '18px',
            fontSize: '14px',
          }}
        >
          {error}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label className="form-label" htmlFor="pack-select">Domain Pack</label>
          <select
            id="pack-select"
            className="form-control"
            value={selectedPack}
            onChange={(e) => handlePackChange(e.target.value)}
          >
            {packs.map((p) => (
              <option key={p.name} value={p.name}>
                {p.name} (v{p.version}) - {p.description.slice(0, 70)}...
              </option>
            ))}
          </select>
        </div>

        {currentPackMeta && (
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-sm)',
              padding: '12px 16px',
              marginBottom: '18px',
              fontSize: '13px',
            }}
          >
            <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '4px' }}>
              Pack Summary
            </div>
            <div style={{ color: 'var(--text-secondary)', marginBottom: '8px' }}>
              {currentPackMeta.description}
            </div>
            <div style={{ display: 'flex', gap: '16px', color: 'var(--text-muted)' }}>
              <span>
                <strong>Entry Agent:</strong> {currentPackMeta.entry_agent}
              </span>
              <span>
                <strong>Agents:</strong> {currentPackMeta.agents.join(' → ')}
              </span>
              <span>
                <strong>Confidence Threshold:</strong>{' '}
                {Math.round(currentPackMeta.default_confidence_threshold * 100)}%
              </span>
            </div>
          </div>
        )}

        <div className="form-group">
          <label className="form-label">Quick Scenario Presets</label>
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
            {selectedPack === 'it_ticket_triage' ? (
              <>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLoadTemplate('it_ticket_triage:standard')}
                >
                  Standard VPN Issue (Passes Autonomously)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLoadTemplate('it_ticket_triage:critical')}
                >
                  Critical Security Breach (Escalates to Human)
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLoadTemplate('loan_prescreening:prime')}
                >
                  Prime Mortgage (Passes Autonomously)
                </button>
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={() => handleLoadTemplate('loan_prescreening:high_dti')}
                >
                  Jumbo / High DTI (Escalates to Senior Underwriter)
                </button>
              </>
            )}
          </div>
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="session-id">
            Session ID (Cross-Run Stateful Memory)
          </label>
          <input
            id="session-id"
            className="form-control"
            type="text"
            value={sessionId}
            onChange={(e) => setSessionId(e.target.value)}
            placeholder="e.g. user-session-123"
          />
        </div>

        <div className="form-group">
          <label className="form-label" htmlFor="json-payload">
            Input Data Payload (JSON)
          </label>
          <textarea
            id="json-payload"
            className="form-control"
            rows={8}
            style={{ fontFamily: 'monospace', fontSize: '13px' }}
            value={jsonInput}
            onChange={(e) => setJsonInput(e.target.value)}
          />
        </div>

        <button
          type="submit"
          className="btn btn-primary"
          disabled={loading}
          style={{ width: '100%', padding: '12px' }}
        >
          {loading ? 'Executing Multi-Agent Graph...' : 'Start Workflow Run'}
        </button>
      </form>
    </div>
  );
};
