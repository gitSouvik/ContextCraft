import React, { useEffect, useState } from 'react';
import { IconBase } from './Icons';
import type { JobStatus } from '../lib/types';

interface Props {
  status: JobStatus;
  repoUrl: string;
}

export const ScanningScreen: React.FC<Props> = ({ status, repoUrl }) => {
  const [scanCount, setScanCount] = useState(0);

  useEffect(() => {
    let interval: any;
    if (status === 'analyzing') {
      interval = setInterval(() => {
        setScanCount((c) => Math.min(50, c + Math.ceil(Math.random() * 4)));
      }, 300);
    }
    return () => clearInterval(interval);
  }, [status]);

  const isCloneDone = status !== 'pending' && status !== 'cloning';
  const isAnalyzeDone = isCloneDone && status !== 'analyzing';
  const isGuideDone = status === 'done';

  const getStatusText = () => {
    if (status === 'pending' || status === 'cloning') return 'Cloning repository...';
    if (status === 'analyzing' || status === 'embedding') return <span>Walking file tree — <span id="scan-count">{scanCount}</span> files found so far...</span>;
    if (status === 'generating_guide') return 'Generating onboarding guide...';
    if (status === 'done') return 'Complete!';
    if (status === 'error') return 'An error occurred during analysis.';
    return 'Processing...';
  };

  return (
    <section className="screen active" id="screen-scanning">
      <div className="steps">
        <div className={`step ${isCloneDone ? 'done' : status === 'cloning' ? 'active' : ''}`}>
          <span className="dot"></span>Cloning
        </div>
        <div className="step-rule"></div>
        <div className={`step ${isAnalyzeDone ? 'done' : status === 'analyzing' || status === 'embedding' ? 'active' : ''}`}>
          <span className="dot"></span>Analyzing
        </div>
        <div className="step-rule"></div>
        <div className={`step ${isGuideDone ? 'done' : status === 'generating_guide' ? 'active' : ''}`}>
          <span className="dot"></span>Writing guide
        </div>
      </div>
      
      <IconBase 
        id="compass" 
        className={`scan-mark ${status !== 'done' && status !== 'error' ? 'spin' : ''}`} 
        style={{ width: 44, height: 44 }} 
      />
      <div id="scan-status">{getStatusText()}</div>
      
      <div className="scan-target">
        target &#9656; <span id="scan-target-url">{repoUrl}</span>
      </div>
    </section>
  );
};
