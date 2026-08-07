import React, { useState, useEffect } from 'react';
import { History as HistoryIcon, Globe, Calendar, Database, ShieldAlert, DollarSign, ChevronRight, ArrowLeft, Loader2 } from 'lucide-react';
import { getHistory } from '../services/auth';
import { AnalysisHistoryItem, AnalyzeResponse } from '../types';
import { Report } from './Report';

export const History: React.FC = () => {
  const [historyItems, setHistoryItems] = useState<AnalysisHistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string>('');
  const [selectedReport, setSelectedReport] = useState<AnalyzeResponse | null>(null);

  useEffect(() => {
    fetchHistoryData();
  }, []);

  const fetchHistoryData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const res = await getHistory();
      setHistoryItems(res.history || []);
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve analysis history.');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (isoString: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  if (selectedReport) {
    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        <button
          onClick={() => setSelectedReport(null)}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-slate-900 border border-gray-800 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-sm font-medium"
        >
          <ArrowLeft className="w-4 h-4" />
          <span>Back to History</span>
        </button>

        <Report data={selectedReport} />
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-extrabold text-white tracking-tight flex items-center gap-3">
            <HistoryIcon className="w-8 h-8 text-cyan-400" />
            Analysis History
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Review previous AWS cloud cost scans and historical optimization recommendations
          </p>
        </div>

        <button
          onClick={fetchHistoryData}
          disabled={isLoading}
          className="self-start sm:self-auto px-4 py-2 rounded-xl bg-slate-900 border border-gray-800 text-slate-300 hover:text-white hover:bg-slate-800 transition-colors text-xs font-mono flex items-center gap-2"
        >
          {isLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
          <span>Refresh History</span>
        </button>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="py-20 flex flex-col items-center justify-center text-slate-400">
          <Loader2 className="w-8 h-8 animate-spin text-cyan-400 mb-3" />
          <span className="text-sm font-medium">Loading history records...</span>
        </div>
      ) : historyItems.length === 0 ? (
        <div className="bg-[#111827] border border-gray-800 rounded-3xl p-12 text-center">
          <Database className="w-12 h-12 text-slate-600 mx-auto mb-4" />
          <h3 className="text-lg font-bold text-white mb-1">No Analysis History</h3>
          <p className="text-slate-400 text-xs max-w-sm mx-auto">
            You haven't executed any AWS region scans yet. Head to the Dashboard to run your first cost analysis.
          </p>
        </div>
      ) : (
        <div className="bg-[#111827] border border-gray-800 rounded-3xl overflow-hidden shadow-xl">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm text-slate-300">
              <thead className="bg-slate-900/90 text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-gray-800">
                <tr>
                  <th className="px-6 py-4">AWS Region</th>
                  <th className="px-6 py-4">Analysis Date</th>
                  <th className="px-6 py-4">Resources Scanned</th>
                  <th className="px-6 py-4">Issues Found</th>
                  <th className="px-6 py-4">Est. Monthly Savings</th>
                  <th className="px-6 py-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-800/80">
                {historyItems.map((item) => (
                  <tr
                    key={item.id}
                    onClick={() => item.analysis_result && setSelectedReport(item.analysis_result)}
                    className="hover:bg-slate-900/50 cursor-pointer transition-colors group"
                  >
                    <td className="px-6 py-4 font-mono font-medium text-white flex items-center gap-2">
                      <Globe className="w-4 h-4 text-cyan-400" />
                      {item.region}
                    </td>

                    <td className="px-6 py-4 text-xs font-mono text-slate-400">
                      <div className="flex items-center gap-2">
                        <Calendar className="w-3.5 h-3.5 text-slate-500" />
                        {formatDate(item.created_at)}
                      </div>
                    </td>

                    <td className="px-6 py-4 font-mono">
                      {item.resources_scanned} resources
                    </td>

                    <td className="px-6 py-4 font-mono">
                      <span className={`px-2.5 py-1 rounded-md text-xs font-semibold ${
                        item.issues_found > 0
                          ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                          : 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                      }`}>
                        {item.issues_found} issues
                      </span>
                    </td>

                    <td className="px-6 py-4 font-mono font-bold text-emerald-400">
                      {item.estimated_monthly_savings}
                    </td>

                    <td className="px-6 py-4 text-right">
                      <span className="inline-flex items-center gap-1 text-xs text-cyan-400 font-semibold group-hover:translate-x-1 transition-transform">
                        View Report
                        <ChevronRight className="w-4 h-4" />
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};
