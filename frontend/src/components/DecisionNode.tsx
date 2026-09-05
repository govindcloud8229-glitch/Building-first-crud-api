import React, { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import type { NodeProps } from '@xyflow/react';
import { CheckCircle2, XCircle, Loader2, PlayCircle, Edit3, Trash2, Flag } from 'lucide-react';
import type { DecisionNodeData } from '../types/workflow';

export const DecisionNode: React.FC<NodeProps> = memo(({ id, data, selected }) => {
  const nodeData = data as unknown as DecisionNodeData;
  const status = nodeData.status || 'pending';
  const isStart = Boolean(nodeData.is_start);

  const getStatusBorder = () => {
    switch (status) {
      case 'executing':
        return 'border-blue-500 shadow-[0_0_20px_rgba(59,130,246,0.6)] ring-2 ring-blue-400';
      case 'completed':
        return nodeData.decision === 'YES'
          ? 'border-emerald-500 shadow-[0_0_15px_rgba(34,197,94,0.4)]'
          : 'border-rose-500 shadow-[0_0_15px_rgba(244,63,94,0.4)]';
      case 'failed':
        return 'border-red-600 shadow-[0_0_20px_rgba(239,68,68,0.7)] ring-2 ring-red-500';
      default:
        return selected ? 'border-indigo-400 shadow-[0_0_12px_rgba(99,102,241,0.5)]' : 'border-slate-700 hover:border-slate-500';
    }
  };

  return (
    <div
      className={`relative min-w-[280px] max-w-[320px] rounded-xl bg-slate-900/95 border-2 text-slate-100 p-3.5 backdrop-blur-md transition-all duration-200 ${getStatusBorder()}`}
    >
      {/* Target handle on top */}
      <Handle
        type="target"
        position={Position.Top}
        className="!bg-indigo-400 !w-3 !h-3 hover:!scale-125 transition-transform"
      />

      {/* Header */}
      <div className="flex items-center justify-between pb-2 border-b border-slate-800 gap-2">
        <div className="flex items-center gap-1.5 min-w-0">
          {isStart ? (
            <span className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider bg-emerald-950 text-emerald-400 border border-emerald-700/60 px-1.5 py-0.5 rounded">
              <Flag className="w-2.5 h-2.5" /> Start
            </span>
          ) : (
            <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 bg-slate-800 px-1.5 py-0.5 rounded">
              Node
            </span>
          )}
          <span className="font-semibold text-xs text-slate-200 truncate" title={nodeData.label}>
            {nodeData.label || 'Decision Step'}
          </span>
        </div>

        {/* Status Indicator */}
        <div className="flex items-center gap-1">
          {status === 'executing' && (
            <span className="flex items-center gap-1 text-xs text-blue-400 font-medium animate-pulse">
              <Loader2 className="w-3.5 h-3.5 animate-spin" /> Running
            </span>
          )}
          {status === 'completed' && (
            <span className={`flex items-center gap-1 text-xs font-bold px-1.5 py-0.5 rounded ${
              nodeData.decision === 'YES' ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-700' : 'bg-rose-950/80 text-rose-400 border border-rose-700'
            }`}>
              <CheckCircle2 className="w-3 h-3" /> {nodeData.decision}
            </span>
          )}
          {status === 'failed' && (
            <span className="flex items-center gap-1 text-xs font-bold text-red-400 bg-red-950/80 border border-red-800 px-1.5 py-0.5 rounded">
              <XCircle className="w-3 h-3" /> Failed
            </span>
          )}
        </div>
      </div>

      {/* Prompt Body */}
      <div className="my-2.5 bg-slate-950/70 border border-slate-800/80 rounded-lg p-2.5 text-xs text-slate-300 leading-relaxed font-mono">
        <p className="line-clamp-3 italic">{nodeData.prompt || 'No prompt configured.'}</p>
      </div>

      {/* Quick Action Controls */}
      <div className="flex items-center justify-between pt-1 text-[11px] text-slate-400">
        <button
          onClick={(e) => {
            e.stopPropagation();
            if (nodeData.onEdit) nodeData.onEdit(id);
          }}
          className="flex items-center gap-1 hover:text-indigo-400 transition-colors cursor-pointer"
        >
          <Edit3 className="w-3 h-3" /> Edit
        </button>

        {!isStart && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              if (nodeData.onSetStart) nodeData.onSetStart(id);
            }}
            className="flex items-center gap-1 hover:text-emerald-400 transition-colors cursor-pointer"
          >
            <PlayCircle className="w-3 h-3" /> Set Start
          </button>
        )}

        <button
          onClick={(e) => {
            e.stopPropagation();
            if (nodeData.onDelete) nodeData.onDelete(id);
          }}
          className="flex items-center gap-1 hover:text-rose-400 transition-colors cursor-pointer ml-auto"
        >
          <Trash2 className="w-3 h-3" />
        </button>
      </div>

      {/* YES / NO Outgoing Handles */}
      <div className="flex justify-between items-center mt-3 pt-2 border-t border-slate-800/70 text-[10px] font-bold">
        {/* YES Handle - Left */}
        <div className="flex items-center gap-1 text-emerald-400 pl-1">
          <span className="bg-emerald-950/80 border border-emerald-700/60 px-2 py-0.5 rounded-full">
            YES
          </span>
          <Handle
            type="source"
            position={Position.Bottom}
            id="yes"
            style={{ left: '25%' }}
            className="!bg-emerald-500 !w-3.5 !h-3.5 hover:!scale-125 !border-slate-950 transition-transform cursor-crosshair"
          />
        </div>

        {/* NO Handle - Right */}
        <div className="flex items-center gap-1 text-rose-400 pr-1">
          <span className="bg-rose-950/80 border border-rose-700/60 px-2 py-0.5 rounded-full">
            NO
          </span>
          <Handle
            type="source"
            position={Position.Bottom}
            id="no"
            style={{ left: '75%' }}
            className="!bg-rose-500 !w-3.5 !h-3.5 hover:!scale-125 !border-slate-950 transition-transform cursor-crosshair"
          />
        </div>
      </div>
    </div>
  );
});

DecisionNode.displayName = 'DecisionNode';
