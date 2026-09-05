import React, { useState, useEffect } from 'react';
import { X, Save, Trash2, Flag, Sparkles } from 'lucide-react';
import type { DecisionNodeData } from '../types/workflow';

interface NodeEditorProps {
  nodeId: string | null;
  nodeData: DecisionNodeData | null;
  onSave: (id: string, label: string, prompt: string, isStart: boolean) => void;
  onDelete: (id: string) => void;
  onClose: () => void;
}

export const NodeEditor: React.FC<NodeEditorProps> = ({
  nodeId,
  nodeData,
  onSave,
  onDelete,
  onClose,
}) => {
  const [label, setLabel] = useState('');
  const [prompt, setPrompt] = useState('');
  const [isStart, setIsStart] = useState(false);

  useEffect(() => {
    if (nodeData) {
      setLabel(nodeData.label || '');
      setPrompt(nodeData.prompt || '');
      setIsStart(Boolean(nodeData.is_start));
    }
  }, [nodeData]);

  if (!nodeId || !nodeData) return null;

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    onSave(nodeId, label.trim() || 'Decision Node', prompt.trim(), isStart);
  };

  return (
    <div className="absolute top-20 right-6 z-20 w-96 bg-slate-900/95 border border-slate-700/80 rounded-2xl shadow-2xl p-5 text-slate-100 backdrop-blur-xl animate-in slide-in-from-right duration-200">
      <div className="flex items-center justify-between pb-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
            <Sparkles className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100">Edit Decision Node</h3>
            <p className="text-[11px] text-slate-400 font-mono">ID: {nodeId}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <form onSubmit={handleSave} className="space-y-4 mt-4">
        {/* Node Label */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            Node Label / Name
          </label>
          <input
            type="text"
            value={label}
            onChange={(e) => setLabel(e.target.value)}
            placeholder="e.g. Is this a billing issue?"
            className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          />
        </div>

        {/* AI Decision Prompt */}
        <div>
          <label className="block text-xs font-semibold text-slate-300 mb-1">
            AI Decision Prompt (Must evaluate to YES or NO)
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            placeholder="Enter the question or statement for the LLM to evaluate as YES or NO..."
            rows={4}
            required
            className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 font-mono leading-relaxed"
          />
          <p className="text-[11px] text-slate-400 mt-1">
            The LLM will strictly evaluate this prompt against the input context and return ONLY <strong>YES</strong> or <strong>NO</strong>.
          </p>
        </div>

        {/* Start Node Checkbox */}
        <div className="flex items-center gap-2 p-2.5 bg-slate-950/60 border border-slate-800/80 rounded-lg">
          <input
            type="checkbox"
            id="start-node-check"
            checked={isStart}
            onChange={(e) => setIsStart(e.target.checked)}
            className="w-4 h-4 text-emerald-500 bg-slate-900 border-slate-700 rounded focus:ring-emerald-400"
          />
          <label htmlFor="start-node-check" className="flex items-center gap-1.5 text-xs text-slate-200 cursor-pointer font-medium">
            <Flag className="w-3.5 h-3.5 text-emerald-400" /> Designate as Starting Node
          </label>
        </div>

        {/* Actions */}
        <div className="flex items-center justify-between pt-2 gap-2">
          <button
            type="button"
            onClick={() => onDelete(nodeId)}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold text-rose-400 hover:bg-rose-950/40 border border-rose-900/50 rounded-lg transition-colors cursor-pointer"
          >
            <Trash2 className="w-3.5 h-3.5" /> Delete
          </button>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onClose}
              className="px-3 py-2 text-xs font-semibold text-slate-400 hover:bg-slate-800 rounded-lg transition-colors cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="flex items-center gap-1.5 px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-500 rounded-lg shadow-lg shadow-indigo-600/30 transition-all cursor-pointer"
            >
              <Save className="w-3.5 h-3.5" /> Save Changes
            </button>
          </div>
        </div>
      </form>
    </div>
  );
};
