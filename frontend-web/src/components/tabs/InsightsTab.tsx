import React, { useMemo } from 'react';
import type { RepoAnalysis } from '../../lib/types';
import { IconBase } from '../Icons';

interface Props {
  repo: RepoAnalysis;
}

export const InsightsTab: React.FC<Props> = ({ repo }) => {
  const { hotspots, topImports, longestFiles } = useMemo(() => {
    // 1. Hotspots (Files with highest total cyclomatic complexity)
    const fileComplexity = repo.files.map(f => {
      const moduleComplexity = f.functions.reduce((acc, fn) => acc + fn.complexity, 0);
      const classComplexity = f.classes.reduce((acc, c) => 
        acc + c.methods.reduce((mAcc, m) => mAcc + m.complexity, 0)
      , 0);
      return { path: f.path, complexity: moduleComplexity + classComplexity };
    }).filter(f => f.complexity > 0).sort((a, b) => b.complexity - a.complexity).slice(0, 5);
    const maxComp = fileComplexity[0]?.complexity || 1;

    // 2. Top Imports
    const importCounts: Record<string, number> = {};
    repo.files.forEach(f => {
      f.imports.forEach(imp => {
        importCounts[imp.module] = (importCounts[imp.module] || 0) + 1;
      });
    });
    const topImportsArr = Object.entries(importCounts)
      .map(([module, count]) => ({ module, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 5);
    const maxImp = topImportsArr[0]?.count || 1;

    // 3. Longest files
    const longestArr = [...repo.files]
      .sort((a, b) => b.loc - a.loc)
      .slice(0, 5)
      .map(f => ({ path: f.path, loc: f.loc }));
    const maxLoc = longestArr[0]?.loc || 1;

    return { 
      hotspots: { items: fileComplexity, max: maxComp },
      topImports: { items: topImportsArr, max: maxImp },
      longestFiles: { items: longestArr, max: maxLoc }
    };
  }, [repo]);

  return (
    <div className="insights-grid">
      <div className="box insights-box">
        <div className="box-header">
          <IconBase id="flame" /> Hotspots
        </div>
        {hotspots.items.map(h => (
          <div className="insight-item" key={h.path}>
            <div className="row">
              <span className="name">{h.path}</span>
              <span className="num">{h.complexity}</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(h.complexity / hotspots.max) * 100}%` }}></div>
            </div>
          </div>
        ))}
        {hotspots.items.length === 0 && <div className="insight-item">No data</div>}
      </div>

      <div className="box insights-box">
        <div className="box-header">
          <IconBase id="cube" /> Top imports
        </div>
        {topImports.items.map(imp => (
          <div className="insight-item" key={imp.module}>
            <div className="row">
              <span className="name">{imp.module}</span>
              <span className="num">{imp.count}&times;</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill teal" style={{ width: `${(imp.count / topImports.max) * 100}%` }}></div>
            </div>
          </div>
        ))}
        {topImports.items.length === 0 && <div className="insight-item">No data</div>}
      </div>

      <div className="box insights-box">
        <div className="box-header">
          <IconBase id="bars" /> Longest files
        </div>
        {longestFiles.items.map(f => (
          <div className="insight-item" key={f.path}>
            <div className="row">
              <span className="name">{f.path}</span>
              <span className="num">{f.loc}</span>
            </div>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(f.loc / longestFiles.max) * 100}%` }}></div>
            </div>
          </div>
        ))}
        {longestFiles.items.length === 0 && <div className="insight-item">No data</div>}
      </div>
    </div>
  );
};
