import React, { useState } from 'react';
import { IconBase } from './Icons';
import type { JobResult, RepoAnalysis } from '../lib/types';
import { GuideTab } from './tabs/GuideTab';
import { MapTab } from './tabs/MapTab';
import { InsightsTab } from './tabs/InsightsTab';
import { RawTab } from './tabs/RawTab';
import { ChatTab } from './tabs/ChatTab';

interface Props {
  job: JobResult;
}

export const ResultsScreen: React.FC<Props> = ({ job }) => {
  const [activeTab, setActiveTab] = useState<'guide' | 'map' | 'insights' | 'raw' | 'chat'>('guide');

  const repo = job.repo_analysis;
  if (!repo) return null;

  const getLanguageBadges = (analysis: RepoAnalysis) => {
    const langs = new Set(analysis.files.map(f => f.language));
    langs.delete('unknown');
    langs.delete('markdown');
    langs.delete('text');
    return Array.from(langs).slice(0, 3); // Max 3 badges
  };

  const totalClasses = repo.files.reduce((acc, f) => acc + f.classes.length, 0);
  const totalFns = repo.files.reduce((acc, f) => acc + f.functions.length + f.classes.reduce((cAcc, c) => cAcc + c.methods.length, 0), 0);
  const totalEntry = repo.files.filter((f) => f.is_entry_point).length;

  return (
    <section className="screen active" id="screen-results">




      <div className="tabs">
        <div className={`tab ${activeTab === 'guide' ? 'active' : ''}`} onClick={() => setActiveTab('guide')}>Onboarding guide</div>
        <div className={`tab ${activeTab === 'map' ? 'active' : ''}`} onClick={() => setActiveTab('map')}>Dependency map</div>
        <div className={`tab ${activeTab === 'insights' ? 'active' : ''}`} onClick={() => setActiveTab('insights')}>Insights</div>
        <div className={`tab ${activeTab === 'raw' ? 'active' : ''}`} onClick={() => setActiveTab('raw')}>Raw structure</div>
        <div className={`tab ${activeTab === 'chat' ? 'active' : ''}`} onClick={() => setActiveTab('chat')}>Chat</div>
      </div>

      <div className={`tab-panel ${activeTab === 'guide' ? 'active' : ''}`}>
        <GuideTab guideMarkdown={job.markdown_guide} />
      </div>

      <div className={`tab-panel ${activeTab === 'map' ? 'active' : ''}`}>
        {activeTab === 'map' && <MapTab repo={repo} />}
      </div>

      <div className={`tab-panel ${activeTab === 'insights' ? 'active' : ''}`}>
        <InsightsTab repo={repo} />
      </div>

      <div className={`tab-panel ${activeTab === 'raw' ? 'active' : ''}`}>
        <RawTab repo={repo} />
      </div>
      
      <div className={`tab-panel ${activeTab === 'chat' ? 'active' : ''}`} style={activeTab === 'chat' ? { display: 'flex', flexDirection: 'column', overflow: 'hidden' } : {}}>
        <ChatTab jobId={job.job_id} isAvailable={job.chat_available} />
      </div>
    </section>
  );
};
