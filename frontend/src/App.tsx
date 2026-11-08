import React, { useEffect, useState } from 'react';
import { Header } from './components/Header';
import { RunWorkflowForm } from './components/RunWorkflowForm';
import { RunsList } from './components/RunsList';
import { RunDetail } from './components/RunDetail';
import { PackSummary, RunResponse } from './types';
import { fetchHealth, fetchPacks, fetchRun, fetchRuns } from './api/client';

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'run' | 'list' | 'detail'>('run');
  const [packs, setPacks] = useState<PackSummary[]>([]);
  const [runs, setRuns] = useState<RunResponse[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunResponse | null>(null);
  const [serverHealth, setServerHealth] = useState<boolean | null>(null);
  const [loadingRuns, setLoadingRuns] = useState<boolean>(false);

  const checkHealthAndLoadPacks = async () => {
    try {
      const h = await fetchHealth();
      setServerHealth(h.status === 'ok');
      const p = await fetchPacks();
      setPacks(p);
    } catch {
      setServerHealth(false);
    }
  };

  const loadRunsList = async () => {
    setLoadingRuns(true);
    try {
      const list = await fetchRuns();
      setRuns(list);
    } catch (err) {
      console.error('Failed to load runs:', err);
    } finally {
      setLoadingRuns(false);
    }
  };

  useEffect(() => {
    checkHealthAndLoadPacks();
    loadRunsList();
    const interval = setInterval(checkHealthAndLoadPacks, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleRunCreated = (run: RunResponse) => {
    setSelectedRun(run);
    setRuns((prev) => [run, ...prev]);
    setActiveTab('detail');
  };

  const handleSelectRun = async (runId: string) => {
    try {
      const run = await fetchRun(runId);
      setSelectedRun(run);
      setActiveTab('detail');
    } catch (err) {
      console.error('Failed to fetch run details:', err);
    }
  };

  const handleRunUpdated = (updated: RunResponse) => {
    setSelectedRun(updated);
    setRuns((prev) =>
      prev.map((r) => (r.run_id === updated.run_id ? updated : r))
    );
  };

  return (
    <div className="app-container">
      <Header
        activeTab={activeTab}
        setActiveTab={(tab) => {
          setActiveTab(tab);
          if (tab === 'list') {
            loadRunsList();
          }
        }}
        selectedRunId={selectedRun?.run_id || null}
        serverHealth={serverHealth}
      />

      <main className="main-content">
        {activeTab === 'run' && (
          <RunWorkflowForm
            packs={packs}
            onRunCreated={handleRunCreated}
          />
        )}

        {activeTab === 'list' && (
          <RunsList
            runs={runs}
            onSelectRun={handleSelectRun}
            onRefresh={loadRunsList}
            loading={loadingRuns}
          />
        )}

        {activeTab === 'detail' && selectedRun && (
          <RunDetail
            run={selectedRun}
            onRunUpdated={handleRunUpdated}
            onBack={() => {
              setActiveTab('list');
              loadRunsList();
            }}
          />
        )}
      </main>
    </div>
  );
};

export default App;
