import React from 'react';
import { Workflow } from 'lucide-react';

interface HeaderProps {
  backendConnected: boolean;
  nodeCount: number;
  edgeCount: number;
}

export const Header: React.FC<HeaderProps> = ({
  backendConnected,
  nodeCount,
  edgeCount,
}) => {
  return (
    <header className="absolute top-4 left-6 z-10 flex items-center gap-3 bg-slate-900/90 border border-slate-700/80 rounded-2xl px-4 py-2.5 shadow-2xl backdrop-blur-xl text-slate-100">
      <div className="p-2 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-600 text-white shadow-md shadow-indigo-500/20">
        <Workflow className="w-5 h-5" />
      </div>

      <div>
        <div className="flex items-center gap-2">
          <h1 className="text-sm font-black tracking-tight text-white">
            AI Decision Flow
          </h1>
          <span className="text-[10px] font-bold uppercase tracking-wider bg-indigo-950 text-indigo-300 border border-indigo-700/60 px-1.5 py-0.5 rounded">
            BE-09
          </span>
        </div>
        <p className="text-[11px] text-slate-400 font-medium">
          React Flow + Inngest Orchestration
        </p>
      </div>

      <div className="h-6 w-px bg-slate-800 mx-1" />

      {/* Backend & Inngest Status */}
      <div className="flex items-center gap-2 text-[11px]">
        <div className="flex items-center gap-1.5">
          <span className={`w-2 h-2 rounded-full ${backendConnected ? 'bg-emerald-400 animate-pulse' : 'bg-rose-500'}`} />
          <span className="text-slate-300 font-medium">
            {backendConnected ? 'FastAPI & Inngest' : 'Offline'}
          </span>
        </div>

        <span className="text-slate-600">•</span>

        <span className="text-slate-400">
          <strong className="text-slate-200">{nodeCount}</strong> nodes, <strong className="text-slate-200">{edgeCount}</strong> edges
        </span>
      </div>
    </header>
  );
};
