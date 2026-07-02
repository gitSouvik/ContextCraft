import React, { useState } from 'react';
import { IconBase } from './Icons';

interface Props {
  onAnalyze: (url: string) => void;
}

export const InputScreen: React.FC<Props> = ({ onAnalyze }) => {
  const [url, setUrl] = useState('https://github.com/gitSouvik/ContextCraft');

  return (
    <section className="screen active" id="screen-input">
      <IconBase id="compass" className="hero-mark" style={{ width: 48, height: 48 }} />
      <h1>Survey any repository</h1>
      <p className="sub">
        Paste a public GitHub URL. ContextCraft clones it, statically maps the structure,<br />
        and writes an onboarding guide from that map alone.
      </p>
      <div className="input-row">
        <input
          type="text"
          placeholder="https://github.com/owner/repo"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && onAnalyze(url)}
        />
        <button className="btn-primary" onClick={() => onAnalyze(url)}>
          Analyze <IconBase id="arrow-right" />
        </button>
      </div>
      <div className="hint">Supports Python, JS/TS, Go, Java, Rust, C/C++, Ruby · up to 50 files</div>

      <div className="section-eyebrow">
        <IconBase id="sparkle" /> Try an example
      </div>
      <div className="example-grid">
        <div
          className={`example-card ${url === 'https://github.com/gitSouvik/ContextCraft' ? 'selected' : ''}`}
          onClick={() => setUrl('https://github.com/gitSouvik/ContextCraft')}
        >
          <div className="name">gitSouvik/ContextCraft</div>
          <div className="desc">Polyglot Code Analyzer</div>
        </div>
        <div
          className={`example-card ${url === 'https://github.com/gitSouvik/S3-FIFO-Cache-Library' ? 'selected' : ''}`}
          onClick={() => setUrl('https://github.com/gitSouvik/S3-FIFO-Cache-Library')}
        >
          <div className="name">gitSouvik/S3-FIFO</div>
          <div className="desc">S3-FIFO Cache Implementation</div>
        </div>
        <div
          className={`example-card ${url === 'https://github.com/fastapi/fastapi' ? 'selected' : ''}`}
          onClick={() => setUrl('https://github.com/fastapi/fastapi')}
        >
          <div className="name">fastapi/fastapi</div>
          <div className="desc">Python Web Framework</div>
        </div>
      </div>
    </section>
  );
};
