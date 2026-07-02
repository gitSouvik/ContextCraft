import React, { useMemo } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  Controls,
  Background,
} from '@xyflow/react';
import type { Node, Edge } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import type { RepoAnalysis } from '../../lib/types';

interface Props {
  repo: RepoAnalysis;
}

const nodeWidth = 200;
const nodeHeight = 50;

const getLayoutedElements = (nodes: Node[], edges: Edge[]) => {
  const dagreGraph = new dagre.graphlib.Graph();
  dagreGraph.setDefaultEdgeLabel(() => ({}));
  dagreGraph.setGraph({ rankdir: 'TB', nodesep: 50, ranksep: 100 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  nodes.forEach((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    node.targetPosition = 'top' as any;
    node.sourcePosition = 'bottom' as any;
    node.position = {
      x: nodeWithPosition.x - nodeWidth / 2,
      y: nodeWithPosition.y - nodeHeight / 2,
    };
    return node;
  });

  return { nodes, edges };
};

export const MapTab: React.FC<Props> = ({ repo }) => {
  const { initialNodes, initialEdges } = useMemo(() => {
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const validPaths = new Set(repo.files.map(f => f.path));

    repo.files.forEach((f) => {
      nodes.push({
        id: f.path,
        data: { label: f.path.split('/').pop() || f.path },
        position: { x: 0, y: 0 },
        style: {
          background: f.is_entry_point ? 'var(--orange)' : 'var(--panel)',
          color: f.is_entry_point ? '#1B1409' : 'var(--text)',
          border: '1px solid var(--line)',
          borderRadius: '6px',
          fontFamily: 'var(--font-mono)',
          fontSize: '12px',
        },
      });

      // Simple heuristic: if an import matches another file path, link them
      f.imports.forEach(imp => {
        // e.g. from utils.validators import ... -> utils/validators.py
        const possiblePath = imp.module.replace(/\./g, '/') + '.py';
        if (validPaths.has(possiblePath)) {
          edges.push({
            id: `e-${f.path}-${possiblePath}`,
            source: f.path,
            target: possiblePath,
            animated: true,
            style: { stroke: 'var(--text-faint)' },
          });
        } else {
          // Check if exactly imp.module matches
          if (validPaths.has(imp.module)) {
            edges.push({
              id: `e-${f.path}-${imp.module}`,
              source: f.path,
              target: imp.module,
              animated: true,
              style: { stroke: 'var(--text-faint)' },
            });
          }
        }
      });
    });

    return getLayoutedElements(nodes, edges);
  }, [repo]);

  const [nodes, _setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, _setEdges, onEdgesChange] = useEdgesState(initialEdges);

  return (
    <div className="map-layout" style={{ height: '500px', display: 'flex' }}>
      <div className="box map-canvas" style={{ flex: 1, minHeight: '500px' }}>
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          attributionPosition="bottom-right"
        >
          <Background color="var(--line-strong)" gap={16} />
          <Controls />
        </ReactFlow>
      </div>
    </div>
  );
};
