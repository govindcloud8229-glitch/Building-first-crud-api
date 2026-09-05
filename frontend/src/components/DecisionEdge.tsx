import React, { memo } from 'react';
import {
  BaseEdge,
  EdgeLabelRenderer,
  getBezierPath,
} from '@xyflow/react';
import type { EdgeProps } from '@xyflow/react';
import type { DecisionEdgeData } from '../types/workflow';

export const DecisionEdge: React.FC<EdgeProps> = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
  markerEnd,
}) => {
  const edgeData = data as unknown as DecisionEdgeData | undefined;
  const decision = edgeData?.decision || 'YES';
  const isActive = Boolean(edgeData?.isActive);

  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });

  const isYes = decision === 'YES';
  const strokeColor = isYes ? '#22c55e' : '#f43f5e';
  const activeClass = isActive ? (isYes ? 'edge-active-yes' : 'edge-active-no') : '';

  return (
    <>
      <BaseEdge
        id={id}
        path={edgePath}
        markerEnd={markerEnd}
        className={activeClass}
        style={{
          stroke: strokeColor,
          strokeWidth: isActive ? 3.5 : selected ? 2.5 : 2,
          strokeDasharray: isActive ? '6 3' : 'none',
          opacity: isActive ? 1 : 0.75,
          transition: 'all 0.3s ease',
        }}
      />
      <EdgeLabelRenderer>
        <div
          style={{
            position: 'absolute',
            transform: `translate(-50%, -50%) translate(${labelX}px,${labelY}px)`,
            pointerEvents: 'all',
          }}
          className="nodrag nopan"
        >
          <span
            className={`text-[10px] font-black uppercase tracking-wider px-2 py-0.5 rounded-full border shadow-sm transition-transform hover:scale-110 ${
              isYes
                ? 'bg-emerald-950 text-emerald-300 border-emerald-600/80 shadow-emerald-950/50'
                : 'bg-rose-950 text-rose-300 border-rose-600/80 shadow-rose-950/50'
            } ${isActive ? 'scale-110 ring-2 ring-offset-1 ring-offset-slate-900 ' + (isYes ? 'ring-emerald-400' : 'ring-rose-400') : ''}`}
          >
            {decision}
          </span>
        </div>
      </EdgeLabelRenderer>
    </>
  );
});

DecisionEdge.displayName = 'DecisionEdge';
