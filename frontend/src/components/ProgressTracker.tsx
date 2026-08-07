import React from 'react';
import { Loader2, CheckCircle2, ShieldCheck, Globe, Database, Brain, Save } from 'lucide-react';
import { ProgressUpdate } from '../types';

interface ProgressTrackerProps {
  currentStage: string;
  progressPercent: number;
}

const STAGES = [
  { name: 'Verifying AWS credentials...', icon: ShieldCheck, match: 'credentials' },
  { name: 'Fetching AWS regions...', icon: Globe, match: 'regions' },
  { name: 'Scanning AWS resources...', icon: Database, match: 'scanning' },
  { name: 'Analyzing cloud costs with AI...', icon: Brain, match: 'ai' },
  { name: 'Storing analysis results...', icon: Save, match: 'storing' },
  { name: 'Analysis complete.', icon: CheckCircle2, match: 'complete' },
];

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({ currentStage, progressPercent }) => {
  return (
    <div className="bg-[#111827] border border-cyan-500/20 rounded-2xl p-6 shadow-2xl shadow-cyan-950/20 my-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center text-cyan-400 border border-cyan-500/30">
            <Loader2 className="w-5 h-5 animate-spin" />
          </div>
          <div>
            <h3 className="text-base font-semibold text-white">Analysis in Progress</h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">{currentStage || 'Initializing analysis pipeline...'}</p>
          </div>
        </div>
        <span className="text-2xl font-bold font-mono text-cyan-400">
          {progressPercent}%
        </span>
      </div>

      {/* Main Progress Bar */}
      <div className="w-full bg-slate-900 rounded-full h-3 overflow-hidden border border-gray-800 p-0.5 mb-6">
        <div
          className="bg-gradient-to-r from-cyan-500 via-sky-400 to-blue-500 h-full rounded-full transition-all duration-500 ease-out shadow-lg shadow-cyan-500/50"
          style={{ width: `${Math.max(5, progressPercent)}%` }}
        />
      </div>

      {/* Stage Steps Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-gray-800/80">
        {STAGES.map((stage, idx) => {
          const IconComponent = stage.icon;
          const isDone = progressPercent >= (idx + 1) * 16.6 || (idx === STAGES.length - 1 && progressPercent === 100);
          const isCurrent = currentStage.toLowerCase().includes(stage.match) || (!isDone && (idx === 0 || progressPercent >= idx * 16.6));

          return (
            <div
              key={stage.name}
              className={`flex items-center gap-3 p-3 rounded-xl border transition-all ${
                isDone
                  ? 'bg-cyan-950/20 border-cyan-500/30 text-cyan-300'
                  : isCurrent
                  ? 'bg-slate-900 border-cyan-400/50 text-white animate-pulse'
                  : 'bg-slate-900/40 border-gray-800/50 text-slate-500'
              }`}
            >
              <div
                className={`w-7 h-7 rounded-lg flex items-center justify-center text-xs font-mono ${
                  isDone
                    ? 'bg-cyan-500/20 text-cyan-400'
                    : isCurrent
                    ? 'bg-cyan-500 text-gray-950 font-bold'
                    : 'bg-gray-800 text-slate-500'
                }`}
              >
                {isDone ? <CheckCircle2 className="w-4 h-4" /> : <IconComponent className="w-4 h-4" />}
              </div>
              <span className="text-xs font-medium tracking-wide">{stage.name}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};
