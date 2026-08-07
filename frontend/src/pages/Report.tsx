import React, { useState, useEffect } from 'react';
import { Copy, Check, ShieldAlert, DollarSign, Cpu, CheckCircle2, Terminal, ChevronRight, FileText, BarChart3 } from 'lucide-react';
import { AnalyzeResponse, AIIssueItem } from '../types';

interface ReportProps {
  data: AnalyzeResponse;
  onBackToDashboard?: () => void;
}

export const Report: React.FC<ReportProps> = ({ data, onBackToDashboard }) => {
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedIndex(id);
    setTimeout(() => setCopiedIndex(null), 2000);
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toUpperCase()) {
      case 'HIGH':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center gap-1.5 w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500 animate-pulse" />
            HIGH
          </span>
        );
      case 'MEDIUM':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30 flex items-center gap-1.5 w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            MEDIUM
          </span>
        );
      case 'LOW':
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 flex items-center gap-1.5 w-fit">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            LOW
          </span>
        );
      default:
        return (
          <span className="px-3 py-1 rounded-full text-xs font-semibold bg-gray-500/10 text-gray-400 border border-gray-500/30">
            {severity}
          </span>
        );
    }
  };

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Header Info */}
      <div className="bg-[#111827] border border-gray-800 rounded-3xl p-6 sm:p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-cyan-500/5 rounded-full blur-3xl pointer-events-none" />

        <div className="flex flex-col md:flex-row md:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className="px-3 py-1 rounded-md text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                {data.region}
              </span>
              <span className="text-xs text-slate-400 font-mono">
                ID: {data.analysis_id}
              </span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
              AWS Cloud Cost Analysis Report
            </h1>
            <p className="text-xs text-slate-400 mt-1">
              Account: <span className="font-mono text-slate-300">{data.caller_identity?.account_id}</span> | Execution time: {data.execution_time_seconds}s
            </p>
          </div>

            <div className="bg-slate-900/90 border border-cyan-500/30 rounded-2xl p-5 flex items-center gap-4 min-w-[240px] shadow-lg shadow-cyan-950/30">
            <div className="w-12 h-12 rounded-xl bg-gradient-to-tr from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 text-white shrink-0">
              <DollarSign className="w-7 h-7" />
            </div>
            <div>
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-400 block">
                Estimated Monthly Savings
              </span>
              <span className="text-2xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-teal-300 font-mono">
                ${data.ai_analysis?.total_estimated_monthly_savings?.toFixed(2) ?? '0.00'}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Metric Summary Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-[#111827] border border-gray-800 rounded-2xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-cyan-500/10 text-cyan-400 flex items-center justify-center border border-cyan-500/20">
            <Cpu className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-medium block">Total Resources Scanned</span>
            <span className="text-xl font-bold font-mono text-white">{data.summary?.total_resources ?? 0}</span>
          </div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-2xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-rose-500/10 text-rose-400 flex items-center justify-center border border-rose-500/20">
            <ShieldAlert className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-medium block">Issues Found</span>
            <span className="text-xl font-bold font-mono text-rose-400">{data.ai_analysis?.issues?.length ?? 0}</span>
          </div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-2xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
            <DollarSign className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-medium block">Est. Monthly Savings</span>
            <span className="text-xl font-bold font-mono text-emerald-400">${data.ai_analysis?.total_estimated_monthly_savings?.toFixed(2) ?? '0.00'}</span>
          </div>
        </div>

        <div className="bg-[#111827] border border-gray-800 rounded-2xl p-5 flex items-center gap-4">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
            <BarChart3 className="w-5 h-5" />
          </div>
          <div>
            <span className="text-xs text-slate-400 font-medium block">Analysis Duration</span>
            <span className="text-xl font-bold font-mono text-purple-300">{data.execution_time_seconds}s</span>
          </div>
        </div>
      </div>


      {/* Executive Summary */}
      <div className="bg-[#111827] border border-gray-800 rounded-3xl p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="w-8 h-8 rounded-lg bg-cyan-500/10 text-cyan-400 flex items-center justify-center">
            <FileText className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-white">Executive Summary</h2>
        </div>
        <p className="text-slate-300 text-sm leading-relaxed bg-slate-900/50 p-5 rounded-2xl border border-gray-800/80 font-normal">
          {data.ai_analysis?.executive_summary}
        </p>
      </div>

      {/* Issues Found & Cost Optimization Recommendations */}
      <div className="bg-[#111827] border border-gray-800 rounded-3xl p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-400 flex items-center justify-center">
              <ShieldAlert className="w-5 h-5" />
            </div>
            <h2 className="text-xl font-bold text-white">Issues Found & Recommendations</h2>
          </div>
          <span className="text-xs font-mono text-slate-400 bg-slate-900 px-3 py-1.5 rounded-lg border border-gray-800">
            Total Issues: {data.ai_analysis?.issues?.length || 0}
          </span>
        </div>

        {data.ai_analysis?.issues && data.ai_analysis.issues.length > 0 ? (
          <div className="space-y-6">
            {data.ai_analysis.issues.map((issue: AIIssueItem, idx: number) => (
              <div
                key={idx}
                className="bg-slate-900/60 border border-gray-800 rounded-2xl p-6 hover:border-gray-700 transition-colors"
              >
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    {getSeverityBadge(issue.severity)}
                    <span className="font-bold text-white text-base">
                      {issue.resource_name}
                    </span>
                    <span className="text-xs text-slate-400 font-mono bg-slate-800 px-2.5 py-0.5 rounded">
                      {issue.resource_type}
                    </span>
                  </div>

                  <div className="text-sm font-mono text-emerald-400 font-semibold bg-emerald-500/10 border border-emerald-500/20 px-3 py-1 rounded-lg w-fit">
                    +${issue.estimated_monthly_savings}/mo savings
                  </div>
                </div>

                <p className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-1">
                  Category: <span className="text-slate-300 font-normal">{issue.category}</span> (Confidence: {issue.confidence_score}%)
                </p>

                <p className="text-slate-300 text-sm mb-4 leading-relaxed">
                  {issue.description}
                </p>

                {/* Copyable AWS CLI Fix Commands */}
                {issue.fix_commands && issue.fix_commands.length > 0 && (
                  <div className="mt-4">
                    <span className="text-xs font-semibold text-cyan-400 uppercase tracking-wider block mb-2 flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5" />
                      AWS CLI Fix Commands
                    </span>
                    <div className="space-y-2">
                      {issue.fix_commands.map((cmd: string, cmdIdx: number) => {
                        const copyId = `cmd-${idx}-${cmdIdx}`;
                        const isCopied = copiedIndex === copyId;

                        return (
                          <div
                            key={cmdIdx}
                            className="bg-[#0b0f17] border border-gray-800 rounded-xl p-3.5 flex items-center justify-between gap-3 font-mono text-xs text-cyan-300 group"
                          >
                            <span className="break-all select-all">{cmd}</span>
                            <button
                              onClick={() => handleCopy(cmd, copyId)}
                              className="shrink-0 text-slate-400 hover:text-white p-1.5 rounded-lg hover:bg-slate-800 transition-colors flex items-center gap-1"
                              title="Copy command"
                            >
                              {isCopied ? (
                                <>
                                  <Check className="w-4 h-4 text-emerald-400" />
                                  <span className="text-[10px] text-emerald-400 font-sans">Copied!</span>
                                </>
                              ) : (
                                <>
                                  <Copy className="w-4 h-4" />
                                  <span className="text-[10px] text-slate-400 font-sans group-hover:text-white">Copy</span>
                                </>
                              )}
                            </button>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        ) : (
          <div className="text-center py-8 text-slate-400 text-sm bg-slate-900/30 rounded-2xl border border-gray-800">
            No cost anomalies or issue alerts identified for this region scan.
          </div>
        )}
      </div>

      {/* Best Practices */}
      <div className="bg-[#111827] border border-gray-800 rounded-3xl p-6 sm:p-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-400 flex items-center justify-center">
            <CheckCircle2 className="w-5 h-5" />
          </div>
          <h2 className="text-xl font-bold text-white">Cost Optimization Best Practices</h2>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {data.ai_analysis?.best_practices?.map((practice: string, idx: number) => (
            <div
              key={idx}
              className="bg-slate-900/50 border border-gray-800 rounded-2xl p-4 flex items-start gap-3"
            >
              <div className="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center shrink-0 mt-0.5 text-xs font-bold font-mono">
                ✓
              </div>
              <p className="text-sm text-slate-300 leading-relaxed">{practice}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
