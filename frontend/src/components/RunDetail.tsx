import React, { useState } from 'react';
import { RunResponse, StepTrace, ToolCallRecord } from '../types';
import { StatusBadge } from './StatusBadge';
import { approveRun, rejectRun } from '../api/client';

interface RunDetailProps {
  run: RunResponse;
  onRunUpdated: (updated: RunResponse) => void;
  onBack: () => void;
}

export const RunDetail: React.FC<RunDetailProps> = ({
  run,
  onRunUpdated,
  onBack,
}) => {
  const [editedOutput, setEditedOutput] = useState<string>(
    run.final_output ? JSON.stringify(run.final_output, null, 2) : ''
  );
  const [approvalNotes, setApprovalNotes] = useState<string>('');
  const [rejectReason, setRejectReason] = useState<string>('Risk threshold exceeded');
  const [actionLoading, setActionLoading] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const isAwaitingApproval = run.status === 'awaiting_approval';
  const jaegerUrl =
    import.meta.env.VITE_JAEGER_URL || 'http://localhost:16686';

  const handleApprove = async () => {
    setActionLoading(true);
    setActionError(null);
    try {
      let parsedEdit = undefined;
      if (editedOutput.trim()) {
        parsedEdit = JSON.parse(editedOutput);
      }
      const updated = await approveRun(run.run_id, {
        edited_output: parsedEdit,
        notes: approvalNotes,
      });
      onRunUpdated(updated);
    } catch (err: any) {
      setActionError(err.message || 'Approval action failed');
    } finally {
      setActionLoading(false);
    }
  };

  const handleReject = async () => {
    if (!rejectReason.trim()) {
      setActionError('Please provide a rejection reason');
      return;
    }
    setActionLoading(true);
    setActionError(null);
    try {
      const updated = await rejectRun(run.run_id, {
        reason: rejectReason,
      });
      onRunUpdated(updated);
    } catch (err: any) {
      setActionError(err.message || 'Rejection action failed');
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div>
      {/* Top Navigation & Status */}
      <div style={{ marginBottom: '16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <button className="btn btn-secondary" onClick={onBack}>
          ← Back to All Runs
        </button>
        <a
          href={`${jaegerUrl}/search?service=orchestrator-service`}
          target="_blank"
          rel="noreferrer"
          className="btn btn-secondary"
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
        >
          <span>🔍 View Trace in Jaeger</span>
        </a>
      </div>

      {/* Overview Card */}
      <div className="card">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '8px' }}>
              <h1 style={{ fontSize: '22px' }}>Workflow Run Details</h1>
              <StatusBadge status={run.status} />
            </div>
            <div style={{ fontFamily: 'monospace', color: 'var(--text-secondary)', fontSize: '14px', marginBottom: '4px' }}>
              ID: {run.run_id}
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
              Domain Pack: <strong>{run.pack_name}</strong> &nbsp;|&nbsp; Session: <code>{run.session_id}</code>
            </div>
          </div>

          <div style={{ textAlign: 'right' }}>
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '4px' }}>Confidence Score</div>
            <div style={{ fontSize: '24px', fontWeight: 700, color: run.confidence >= 0.75 ? '#16a34a' : '#d97706' }}>
              {Math.round(run.confidence * 100)}%
            </div>
          </div>
        </div>
      </div>

      {/* Human-in-the-Loop Escalation Banner */}
      {isAwaitingApproval && (
        <div
          className="card"
          style={{
            borderColor: '#f59e0b',
            background: '#fffbeb',
            boxShadow: '0 4px 12px rgba(245, 158, 11, 0.15)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: '#b45309' }}>
            <span style={{ fontSize: '20px' }}>⚠️</span>
            <h3 style={{ fontSize: '18px', fontWeight: 700 }}>Human-in-the-Loop Approval Required</h3>
          </div>

          <p style={{ color: '#92400e', fontSize: '14px', marginBottom: '16px' }}>
            <strong>Escalation Trigger:</strong> {run.escalation_reason || 'Confidence fell below threshold or policy rule triggered.'}
          </p>

          {actionError && (
            <div style={{ background: '#fee2e2', border: '1px solid #f87171', color: '#b91c1c', padding: '10px', borderRadius: '4px', marginBottom: '14px', fontSize: '13px' }}>
              {actionError}
            </div>
          )}

          <div className="form-group">
            <label className="form-label" style={{ color: '#78350f' }}>
              Edit Proposed Output (Optional Override):
            </label>
            <textarea
              className="form-control"
              rows={4}
              style={{ fontFamily: 'monospace', fontSize: '13px' }}
              value={editedOutput}
              onChange={(e) => setEditedOutput(e.target.value)}
              placeholder='{"resolution": "Custom human resolution..."}'
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
            <div>
              <label className="form-label" style={{ color: '#78350f' }}>Approval Notes (Optional):</label>
              <input
                className="form-control"
                type="text"
                value={approvalNotes}
                onChange={(e) => setApprovalNotes(e.target.value)}
                placeholder="Reason for approval / sign-off"
              />
            </div>
            <div>
              <label className="form-label" style={{ color: '#78350f' }}>Rejection Reason (If rejecting):</label>
              <input
                className="form-control"
                type="text"
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                placeholder="Rationale for stopping execution"
              />
            </div>
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button
              className="btn btn-success"
              onClick={handleApprove}
              disabled={actionLoading}
            >
              ✓ Approve &amp; Finalize Workflow
            </button>
            <button
              className="btn btn-danger"
              onClick={handleReject}
              disabled={actionLoading}
            >
              ✕ Reject Workflow
            </button>
          </div>
        </div>
      )}

      {/* Step Trace Timeline */}
      <div className="card">
        <h2 style={{ fontSize: '18px', marginBottom: '6px' }}>Agent Execution Timeline</h2>
        <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '20px' }}>
          Chronological audit trace of every agent node, structured tool invocation, and verification report.
        </p>

        <div className="timeline">
          {run.trace_steps.map((step: StepTrace) => (
            <div key={step.step_index} className="timeline-item">
              <div
                className={`timeline-dot ${step.escalation_triggered ? 'escalated' : ''}`}
              />
              <div className="timeline-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span style={{ fontWeight: 700, fontSize: '15px' }}>
                      Step {step.step_index}: {step.agent_name}
                    </span>
                    {step.escalation_triggered && (
                      <span className="badge badge-awaiting_approval" style={{ fontSize: '11px' }}>
                        Escalated
                      </span>
                    )}
                  </div>
                  <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                    Confidence: <strong>{Math.round(step.confidence * 100)}%</strong> &nbsp;|&nbsp;{' '}
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </div>
                </div>

                {step.escalation_reason && (
                  <div
                    style={{
                      background: '#fffbeb',
                      borderLeft: '4px solid #f59e0b',
                      padding: '8px 12px',
                      fontSize: '13px',
                      color: '#92400e',
                      marginBottom: '12px',
                    }}
                  >
                    <strong>Escalation:</strong> {step.escalation_reason}
                  </div>
                )}

                {/* Agent Decisions */}
                <div style={{ fontSize: '13px', marginBottom: '12px' }}>
                  <div style={{ color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    <strong>Decision / Summary:</strong> {step.output_data.summary || step.output_data.reasoning || 'Step processed successfully.'}
                  </div>
                  {step.output_data.final_response && (
                    <div style={{ background: '#f8fafc', padding: '8px', borderRadius: '4px', border: '1px solid var(--border)' }}>
                      <strong>Response:</strong> {typeof step.output_data.final_response === 'string' ? step.output_data.final_response : JSON.stringify(step.output_data.final_response)}
                    </div>
                  )}
                </div>

                {/* Tool Calls */}
                {step.tool_calls && step.tool_calls.length > 0 && (
                  <div style={{ marginTop: '12px' }}>
                    <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '6px' }}>
                      STRUCTURED TOOL INVOCATIONS ({step.tool_calls.length})
                    </div>
                    {step.tool_calls.map((tool: ToolCallRecord, tIdx: number) => (
                      <div
                        key={tIdx}
                        style={{
                          background: '#f8fafc',
                          border: '1px solid var(--border)',
                          borderRadius: 'var(--radius-sm)',
                          padding: '10px 12px',
                          marginBottom: '8px',
                          fontSize: '13px',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontWeight: 600, color: 'var(--primary)' }}>
                            🔧 {tool.tool_name}
                          </span>
                          <span style={{ color: 'var(--text-muted)', fontSize: '11px' }}>
                            {tool.execution_time_ms}ms
                          </span>
                        </div>

                        {tool.error && (
                          <div style={{ color: '#dc2626', fontSize: '12px', marginTop: '4px' }}>
                            Error: {tool.error}
                          </div>
                        )}

                        {/* Special Rich Rendering for Verifier Code Generation */}
                        {tool.tool_name === 'generate_code' && tool.output && (
                          <div style={{ marginTop: '8px' }}>
                            <div style={{ fontWeight: 600, fontSize: '12px', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                              AI-Generated Code:
                            </div>
                            <pre className="json-view" style={{ maxHeight: '180px', marginBottom: '8px' }}>
                              {tool.output.code}
                            </pre>

                            {tool.output.verification_report && (
                              <div
                                style={{
                                  background: tool.output.verification_report.passed ? '#f0fdf4' : '#fef2f2',
                                  border: `1px solid ${tool.output.verification_report.passed ? '#86efac' : '#fca5a5'}`,
                                  borderRadius: '4px',
                                  padding: '8px 12px',
                                  fontSize: '12px',
                                }}
                              >
                                <div style={{ fontWeight: 700, color: tool.output.verification_report.passed ? '#16a34a' : '#dc2626', marginBottom: '4px' }}>
                                  Automated Verification Report: {tool.output.verification_report.passed ? 'PASSED ✓' : 'FAILED ✕'}
                                </div>
                                <div style={{ display: 'flex', gap: '12px', color: 'var(--text-secondary)' }}>
                                  <span>Checks: {tool.output.verification_report.summary?.checks_passed || 0}/3</span>
                                  <span>Unit Tests: {tool.output.verification_report.summary?.tests_passed || 0} passed</span>
                                  <span>Time: {tool.output.verification_report.total_execution_time_ms || 0}ms</span>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        {tool.tool_name !== 'generate_code' && (
                          <details style={{ marginTop: '4px' }}>
                            <summary style={{ cursor: 'pointer', color: 'var(--text-muted)', fontSize: '11px' }}>
                              View Arguments &amp; Output
                            </summary>
                            <div style={{ marginTop: '6px' }}>
                              <pre className="json-view" style={{ maxHeight: '140px', fontSize: '11px' }}>
                                {JSON.stringify(tool.output, null, 2)}
                              </pre>
                            </div>
                          </details>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Raw Final Output & Input Panels */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        <div className="card">
          <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>Initial Input Data</h3>
          <pre className="json-view">
            {JSON.stringify(run.input_data, null, 2)}
          </pre>
        </div>

        <div className="card">
          <h3 style={{ fontSize: '16px', marginBottom: '8px' }}>Final Output Result</h3>
          <pre className="json-view">
            {run.final_output ? JSON.stringify(run.final_output, null, 2) : 'Awaiting completion / approval'}
          </pre>
        </div>
      </div>
    </div>
  );
};
