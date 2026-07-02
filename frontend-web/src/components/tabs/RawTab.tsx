import React from 'react';
import type { RepoAnalysis } from '../../lib/types';
import { IconBase } from '../Icons';

interface Props {
  repo: RepoAnalysis;
}

export const RawTab: React.FC<Props> = ({ repo }) => {
  return (
    <div className="raw-grid">
      {repo.files.filter(f => f.classes.length > 0 || f.functions.length > 0).map(f => (
        <div className="box raw-box" key={f.path}>
          <div className="box-header">
            <IconBase id="file" /> {f.path}
          </div>
          {f.classes.map(c => (
            <React.Fragment key={`c-${c.name}`}>
              <div className="raw-item">
                <span className="raw-left">
                  <span className="tag tag-cls">class</span>{c.name}
                </span>
              </div>
              {c.methods.map(m => (
                <div className="raw-item" key={`m-${c.name}-${m.name}`}>
                  <span className="raw-left" style={{ marginLeft: 20 }}>
                    <span className="tag tag-fn">fn</span>{m.name}
                  </span>
                  <span className="complexity">complexity {m.complexity}</span>
                </div>
              ))}
            </React.Fragment>
          ))}
          {f.functions.map(fn => (
            <div className="raw-item" key={`fn-${fn.name}`}>
              <span className="raw-left">
                <span className="tag tag-fn">fn</span>{fn.name}
              </span>
              <span className="complexity">complexity {fn.complexity}</span>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
};
