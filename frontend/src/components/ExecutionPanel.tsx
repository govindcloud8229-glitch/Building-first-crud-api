import React, { useState } from 'react';
import {
  XCircle,
  Clock,
  ChevronDown,
  ChevronUp,
  Activity,
  Sparkles,
} from 'lucide-react';
import type { WorkflowRunResult, StepExecution } from '../types/workflow';

interface ExecutionPanelProps {
  runResult: WorkflowRunResult | null;
  isRunning: boolean;
  onClose?: () => void;
}

export const ExecutionPanel: React.FC<ExecutionPanelProps> = ({
  runResult,
  isRunning,
}) => {
  const [expandedStep, setExpandedStep] = useState<number | null>(null);
  const [isCollapsed, setIsCollapsed] = useState(false);

  if (!runResult && !isRunning) {
    return null;
  }

  const toggleExpand = (stepNum: number) => {
    setExpandedStep(expandedStep === stepNum ? null : stepNum);
  };

  return (
    <div className="absolute bottom-6 right-6 z-20 w-[420px] max-h-[500px] bg-slate-900/95 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col text-slate-100 backdrop-blur-xl transition-all duration-300">
      {/* Panel Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800">
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 rounded-lg bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <Activity className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
              Workflow Execution
              {isRunning && (
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500"></span>
                </span>
              )}
            </h3>
            {runResult && (
              <p className="text-[11px] text-slate-400 font-mono">
                Run ID: {runResult.run_id}
              </p>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {runResult && (
            <span
              className={`text-[10px] font-bold uppercase px-2 py-0.5 rounded-full border ${
                runResult.status === 'completed'
                  ? 'bg-emerald-950 text-emerald-400 border-emerald-700'
                  : runResult.status === 'failed'
                  ? 'bg-rose-950 text-rose-400 border-rose-700'
                  : 'bg-blue-950 text-blue-400 border-blue-700'
              }`}
            >
              {runResult.status}
            </span>
          )}
          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
          >
            {isCollapsed ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {!isCollapsed && (
        <>
          {/* Metadata Summary */}
          {runResult && (
            <div className="grid grid-cols-3 gap-2 px-4 py-2.5 bg-slate-950/60 border-b border-slate-800/80 text-[11px]">
              <div>
                <span className="text-slate-400 block">Total Steps</span>
                <span className="font-bold text-slate-200">{runResult.steps.length}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Start Node</span>
                <span className="font-mono text-indigo-400 truncate block">{runResult.start_node_id}</span>
              </div>
              <div>
                <span className="text-slate-400 block">Status</span>
                <span className="font-semibold text-slate-200 capitalize">{runResult.status}</span>
              </div>
            </div>
          )}

          {/* Error Banner */}
          {runResult?.error && (
            <div className="mx-4 my-2.5 p-3 rounded-lg bg-rose-950/50 border border-rose-800/60 text-xs text-rose-300 flex items-start gap-2">
              <XCircle className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-bold block">Execution Error:</span>
                <span className="font-mono text-[11px] leading-relaxed">{runResult.error}</span>
              </div>
            </div>
          )}

          {/* Step Timeline */}
          <div className="p-4 overflow-y-auto space-y-2.5 max-h-[300px]">
            {runResult?.steps && runResult.steps.length > 0 ? (
              runResult.steps.map((step: StepExecution) => (
                <div
                  key={step.step_number}
                  className="rounded-xl bg-slate-950/80 border border-slate-800 overflow-hidden transition-all text-xs"
                >
                  <div
                    onClick={() => toggleExpand(step.step_number)}
                    className="flex items-center justify-between p-3 cursor-pointer hover:bg-slate-900/60 transition-colors"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="w-5 h-5 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-[10px] font-bold text-slate-300 shrink-0">
                        {step.step_number}
                      </span>
                      <div className="truncate">
                        <span className="font-semibold text-slate-200 block truncate">
                          {step.node_label}
                        </span>
                        <span className="text-[10px] text-slate-400 font-mono">
                          ID: {step.node_id}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      {step.status === 'completed' && step.decision && (
                        <span
                          className={`font-black px-2 py-0.5 rounded-full text-[10px] border ${
                            step.decision === 'YES'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-600'
                              : 'bg-rose-950 text-rose-300 border-rose-600'
                          }`}
                        >
                          {step.decision}
                        </span>
                      )}
                      {step.status === 'failed' && (
                        <span className="text-red-400 flex items-center gap-1 font-bold text-[10px]">
                          <XCircle className="w-3.5 h-3.5" /> Error
                        </span>
                      )}
                      {expandedStep === step.step_number ? (
                        <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                      ) : (
                        <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                      )}
                    </div>
                  </div>

                  {/* Expanded Step Details */}
                  {expandedStep === step.step_number && (
                    <div className="p-3 bg-slate-900/90 border-t border-slate-800/80 space-y-2 text-[11px]">
                      <div>
                        <span className="text-slate-400 block font-semibold">Evaluated Prompt:</span>
                        <p className="text-slate-300 font-mono mt-0.5 bg-slate-950 p-2 rounded border border-slate-800/70">
                          {step.prompt}
                        </p>
                      </div>

                      {step.raw_response && (
                        <div>
                          <span className="text-slate-400 block font-semibold">Raw LLM Output:</span>
                          <p className="text-slate-300 font-mono mt-0.5 bg-slate-950 p-2 rounded border border-slate-800/70 truncate">
                            {step.raw_response}
                          </p>
                        </div>
                      )}

                      {step.error && (
                        <div>
                          <span className="text-rose-400 block font-semibold">Error:</span>
                          <p className="text-rose-300 font-mono mt-0.5 bg-rose-950/40 p-2 rounded border border-rose-900/60">
                            {step.error}
                          </p>
                        </div>
                      )}

                      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3" /> {new Date(step.timestamp).toLocaleTimeString()}
                        </span>
                        <span className="flex items-center gap-1 text-indigo-400 font-medium">
                          <Sparkles className="w-3 h-3" /> Inngest Step Verified
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              ))
            ) : isRunning ? (
              <div className="text-center py-8 text-slate-400 space-y-2">
                <div className="inline-block animate-spin text-indigo-400">
                  <Activity className="w-6 h-6" />
                </div>
                <p className="text-xs">Orchestrating Inngest workflow steps...</p>
              </div>
            ) : (
              <div className="text-center py-6 text-slate-400 text-xs">
                No execution steps recorded yet. Click <strong>Run Workflow</strong> to execute.
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
