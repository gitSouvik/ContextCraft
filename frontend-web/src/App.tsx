import React, { useState, useEffect } from 'react';
import { IconsDefs, IconBase } from './components/Icons';
import { InputScreen } from './components/InputScreen';
import { ScanningScreen } from './components/ScanningScreen';
import { ResultsScreen } from './components/ResultsScreen';
import { startAnalysis, getJobResult } from './lib/api';
import type { JobResult } from './lib/types';
import './index.css';

type ScreenState = 'input' | 'scanning' | 'results';

function App() {
  const [currentScreen, setCurrentScreen] = useState<ScreenState>('input');
  const [repoUrl, setRepoUrl] = useState('');
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobResult, setJobResult] = useState<JobResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleAnalyze = async (url: string) => {
    if (!url) return;
    setRepoUrl(url);
    setCurrentScreen('scanning');
    setError(null);
    setJobResult(null);

    try {
      const id = await startAnalysis(url);
      setJobId(id);
    } catch (err: any) {
      setError(err.message);
      setCurrentScreen('input');
    }
  };

  useEffect(() => {
    let intervalId: any;

    if (jobId && currentScreen === 'scanning') {
      intervalId = setInterval(async () => {
        try {
          const result = await getJobResult(jobId);
          setJobResult(result);
          
          if (result.status === 'done') {
            clearInterval(intervalId);
            setTimeout(() => setCurrentScreen('results'), 1000);
          } else if (result.status === 'error') {
            clearInterval(intervalId);
            setError(result.error || 'Unknown error occurred.');
            setCurrentScreen('input');
          }
        } catch (err: any) {
          clearInterval(intervalId);
          setError(err.message);
          setCurrentScreen('input');
        }
      }, 2000);
    }

    return () => clearInterval(intervalId);
  }, [jobId, currentScreen]);

  const resetApp = () => {
    setJobId(null);
    setJobResult(null);
    setRepoUrl('');
    setCurrentScreen('input');
    setError(null);
  };

  return (
    <>
      <IconsDefs />
      <div className="app">
        <div className="topbar">
          <div className="brand" onClick={resetApp} style={{ cursor: 'pointer' }}>
            <IconBase id="compass" className="mark" style={{ verticalAlign: '-5px', width: 20, height: 20 }} />
            <span className="wordmark">CONTEXTCRAFT</span>
            <span className="tagline">/ {jobResult?.repo_analysis?.repo_name || repoUrl.replace('https://github.com/', '') || 'static repo cartographer'}</span>
          </div>
          {currentScreen === 'results' && (
            <div className="repo-context show" id="repo-context">
              <button className="btn-ghost" onClick={resetApp}>
                <IconBase id="reset" /> New survey
              </button>
            </div>
          )}
        </div>

        <div className="canvas">
          {error && <div style={{ color: 'red', padding: 20, textAlign: 'center' }}>Error: {error}</div>}
          
          {currentScreen === 'input' && <InputScreen onAnalyze={handleAnalyze} />}
          
          {currentScreen === 'scanning' && (
            <ScanningScreen status={jobResult?.status || 'pending'} repoUrl={repoUrl} />
          )}
          
          {currentScreen === 'results' && jobResult && (
            <ResultsScreen job={jobResult} />
          )}
        </div>
      </div>
    </>
  );
}

export default App;
