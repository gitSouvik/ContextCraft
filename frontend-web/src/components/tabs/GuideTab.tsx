import React from 'react';
import ReactMarkdown from 'react-markdown';
import { IconBase } from '../Icons';

interface Props {
  guideMarkdown?: string;
}

export const GuideTab: React.FC<Props> = ({ guideMarkdown }) => {
  if (!guideMarkdown) {
    return <div className="guide-box-body">Guide is not available.</div>;
  }

  return (
    <div className="guide-grid">
      <div className="box guide-box" style={{ gridColumn: '1 / -1' }}>
        <div className="box-header">
          <IconBase id="compass" /> Onboarding Guide
        </div>
        <div className="guide-box-body guide-markdown">
          <ReactMarkdown>{guideMarkdown}</ReactMarkdown>
        </div>
      </div>
    </div>
  );
};
