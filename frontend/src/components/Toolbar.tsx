import React, { useState, useRef } from 'react';
import {
  Plus,
  Play,
  RotateCcw,
  Download,
  Upload,
  BookOpen,
  Loader2,
  FileText,
} from 'lucide-react';
import type { WorkflowTemplate, WorkflowExportJSON } from '../types/workflow';

interface ToolbarProps {
  onAddNode: () => void;
  onRunWorkflow: (context: string) => void;
  onResetWorkflow: () => void;
  onExportJSON: () => void;
  onImportJSON: (data: WorkflowExportJSON) => void;
  onLoadTemplate: (template: WorkflowTemplate) => void;
  templates: WorkflowTemplate[];
  isRunning: boolean;
  inputContext: string;
  setInputContext: (val: string) => void;
}

export const Toolbar: React.FC<ToolbarProps> = ({
  onAddNode,
  onRunWorkflow,
  onResetWorkflow,
  onExportJSON,
  onImportJSON,
  onLoadTemplate,
  templates,
  isRunning,
  inputContext,
  setInputContext,
}) => {
  const [showTemplates, setShowTemplates] = useState(false);
  const [showContextModal, setShowContextModal] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const json = JSON.parse(event.target?.result as string);
        if (json.nodes && Array.isArray(json.nodes)) {
          onImportJSON(json);
        } else {
          alert('Invalid workflow JSON format: must contain a "nodes" array.');
        }
      } catch (err) {
        alert('Failed to parse JSON file: ' + String(err));
      }
    };
    reader.readAsText(file);
    if (e.target) e.target.value = '';
  };

  return (
    <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 flex items-center gap-2 bg-slate-900/90 border border-slate-700/80 rounded-2xl p-2 shadow-2xl backdrop-blur-xl text-slate-100">
      {/* Hidden file input for import */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept=".json"
        className="hidden"
      />

      {/* Add Decision Node */}
      <button
        onClick={onAddNode}
        className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition-all cursor-pointer shadow-sm hover:scale-105"
        title="Add new decision node"
      >
        <Plus className="w-3.5 h-3.5 text-indigo-400" /> Add Node
      </button>

      {/* Templates Dropdown */}
      <div className="relative">
        <button
          onClick={() => setShowTemplates(!showTemplates)}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-semibold bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-xl transition-all cursor-pointer shadow-sm"
        >
          <BookOpen className="w-3.5 h-3.5 text-amber-400" /> Templates
        </button>

        {showTemplates && (
          <div className="absolute top-12 left-0 w-64 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl p-2 space-y-1 z-30 animate-in fade-in zoom-in-95 duration-150">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-400 px-2 py-1 block">
              Workflow Presets
            </span>
            {templates.map((tpl) => (
              <button
                key={tpl.id}
                onClick={() => {
                  onLoadTemplate(tpl);
                  setShowTemplates(false);
                }}
                className="w-full text-left px-2.5 py-2 rounded-lg hover:bg-slate-800 text-xs transition-colors block cursor-pointer group"
              >
                <div className="font-semibold text-slate-200 group-hover:text-indigo-400">
                  {tpl.name}
                </div>
                <div className="text-[10px] text-slate-400 line-clamp-1">
                  {tpl.description}
                </div>
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="h-5 w-px bg-slate-800 mx-1" />

      {/* Input Context Button */}
      <button
        onClick={() => setShowContextModal(!showContextModal)}
        className={`flex items-center gap-1.5 px-3 py-2 text-xs font-semibold border rounded-xl transition-all cursor-pointer ${
          inputContext.trim()
            ? 'bg-indigo-950/60 text-indigo-300 border-indigo-700/80 shadow-indigo-950/50'
            : 'bg-slate-800 hover:bg-slate-700 border-slate-700 text-slate-300'
        }`}
        title="Set test customer message / context"
      >
        <FileText className="w-3.5 h-3.5 text-indigo-400" /> Context {inputContext.trim() && '✓'}
      </button>

      {/* Run Workflow */}
      <button
        onClick={() => onRunWorkflow(inputContext)}
        disabled={isRunning}
        className="flex items-center gap-2 px-5 py-2 text-xs font-bold text-white bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 rounded-xl shadow-lg shadow-emerald-600/30 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed hover:scale-105"
      >
        {isRunning ? (
          <>
            <Loader2 className="w-3.5 h-3.5 animate-spin" /> Running Inngest...
          </>
        ) : (
          <>
            <Play className="w-3.5 h-3.5 fill-current" /> Run Workflow
          </>
        )}
      </button>

      <div className="h-5 w-px bg-slate-800 mx-1" />

      {/* Export JSON */}
      <button
        onClick={onExportJSON}
        className="p-2 text-xs text-slate-300 hover:text-indigo-400 hover:bg-slate-800 rounded-xl transition-colors cursor-pointer"
        title="Export workflow as JSON"
      >
        <Download className="w-3.5 h-3.5" />
      </button>

      {/* Import JSON */}
      <button
        onClick={() => fileInputRef.current?.click()}
        className="p-2 text-xs text-slate-300 hover:text-indigo-400 hover:bg-slate-800 rounded-xl transition-colors cursor-pointer"
        title="Import workflow from JSON"
      >
        <Upload className="w-3.5 h-3.5" />
      </button>

      {/* Reset Canvas */}
      <button
        onClick={onResetWorkflow}
        className="p-2 text-xs text-slate-400 hover:text-rose-400 hover:bg-slate-800 rounded-xl transition-colors cursor-pointer"
        title="Reset canvas"
      >
        <RotateCcw className="w-3.5 h-3.5" />
      </button>

      {/* Context Input Modal */}
      {showContextModal && (
        <div className="absolute top-14 left-1/2 -translate-x-1/2 w-96 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl p-4 text-slate-100 z-30 animate-in fade-in zoom-in-95 duration-150">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800 mb-3">
            <span className="text-xs font-bold text-slate-200 flex items-center gap-1.5">
              <FileText className="w-3.5 h-3.5 text-indigo-400" /> Evaluation Context / Customer Message
            </span>
            <button
              onClick={() => setShowContextModal(false)}
              className="text-slate-400 hover:text-slate-200 text-xs cursor-pointer"
            >
              ✕
            </button>
          </div>
          <textarea
            value={inputContext}
            onChange={(e) => setInputContext(e.target.value)}
            placeholder="e.g. I was double charged $49 for my annual subscription renewal and I need an immediate refund."
            rows={3}
            className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 font-mono"
          />
          <div className="flex justify-between items-center mt-2 pt-2 border-t border-slate-800/80">
            <button
              onClick={() => setInputContext('')}
              className="text-[11px] text-slate-400 hover:text-rose-400"
            >
              Clear Context
            </button>
            <button
              onClick={() => setShowContextModal(false)}
              className="px-3 py-1.5 text-xs font-bold bg-indigo-600 hover:bg-indigo-500 rounded-lg transition-colors cursor-pointer text-white"
            >
              Apply Context
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
