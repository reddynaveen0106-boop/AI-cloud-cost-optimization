import React, { useState, useEffect } from 'react';
import { Play, Globe, AlertCircle, RefreshCw, Sparkles, Cpu, Layers } from 'lucide-react';
import { getRegions, runAnalysis } from '../services/auth';
import { RegionItem, AnalyzeResponse } from '../types';
import { ProgressTracker } from '../components/ProgressTracker';
import { AnalysisWebSocketService } from '../services/websocket';
import { Report } from './Report';

export const Dashboard: React.FC = () => {
  const [regions, setRegions] = useState<RegionItem[]>([]);
  const [selectedRegion, setSelectedRegion] = useState<string>('us-east-1');
  const [isLoadingRegions, setIsLoadingRegions] = useState<boolean>(true);
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [error, setError] = useState<string>('');

  // WebSocket progress state
  const [currentStage, setCurrentStage] = useState<string>('');
  const [progressPercent, setProgressPercent] = useState<number>(0);
  const [activeAnalysisId, setActiveAnalysisId] = useState<string | null>(null);

  // Analysis completion result state
  const [analysisResult, setAnalysisResult] = useState<AnalyzeResponse | null>(null);

  useEffect(() => {
    fetchRegions();
  }, []);

  const fetchRegions = async () => {
    setIsLoadingRegions(true);
    setError('');
    try {
      const res = await getRegions();
      setRegions(res.regions || []);
      if (res.regions && res.regions.length > 0) {
        setSelectedRegion(res.regions[0].region_name);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load AWS regions.');
    } finally {
      setIsLoadingRegions(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!selectedRegion) return;

    setError('');
    setIsAnalyzing(true);
    setAnalysisResult(null);
    setProgressPercent(0);
    setCurrentStage('Initializing AWS Region scanner...');

    const analysisId = `scan-${Date.now()}`;
    setActiveAnalysisId(analysisId);

    // Initialize WebSocket listener
    const wsService = new AnalysisWebSocketService(analysisId);
    wsService.connect(
      (data) => {
        setCurrentStage(data.stage);
        setProgressPercent(data.progress_percent);
      },
      (err) => {
        console.error('WebSocket connection error:', err);
      }
    );

    try {
      const result = await runAnalysis(selectedRegion, analysisId);
      setAnalysisResult(result);
    } catch (err: any) {
      setError(err.message || 'Error occurred while running cost analysis.');
    } finally {
      setIsAnalyzing(false);
      wsService.disconnect();
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">
      {/* Top Banner / Hero */}
      <div className="bg-gradient-to-r from-slate-900 via-[#111827] to-cyan-950/40 border border-gray-800 rounded-3xl p-6 sm:p-8 relative overflow-hidden">
        <div className="max-w-3xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/30 mb-4">
            <Sparkles className="w-3.5 h-3.5" />
            <span>AI Cloud Cost Optimization Engine</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold text-white tracking-tight">
            AWS Infrastructure Cost Detective
          </h1>
          <p className="text-slate-400 text-sm sm:text-base mt-2 leading-relaxed">
            Select an AWS region below to initiate deep resource discovery, automated Cost Explorer integration, and AI-driven cost reduction recommendations.
          </p>
        </div>
      </div>

      {error && (
        <div className="p-4 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm flex items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
          <button
            onClick={fetchRegions}
            className="px-3 py-1 bg-rose-500/20 hover:bg-rose-500/30 rounded-lg text-xs font-medium transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* Region Selection & Trigger Controls */}
      <div className="bg-[#111827] border border-gray-800 rounded-3xl p-6 sm:p-8 shadow-xl">
        <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <Globe className="w-5 h-5 text-cyan-400" />
          Target AWS Region
        </h2>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-4">
          <div className="relative flex-1">
            <select
              value={selectedRegion}
              onChange={(e) => setSelectedRegion(e.target.value)}
              disabled={isLoadingRegions || isAnalyzing}
              className="w-full bg-slate-900 border border-gray-800 text-white rounded-xl px-4 py-3.5 text-sm appearance-none focus:outline-none focus:border-cyan-500 font-mono disabled:opacity-50"
            >
              {isLoadingRegions ? (
                <option>Loading AWS regions...</option>
              ) : (
                regions.map((r) => (
                  <option key={r.region_name} value={r.region_name}>
                    {r.region_name} ({r.opt_in_status || 'available'})
                  </option>
                ))
              )}
            </select>
            <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none text-slate-400">
              ▼
            </div>
          </div>

          <button
            onClick={handleRunAnalysis}
            disabled={isAnalyzing || isLoadingRegions}
            className="py-3.5 px-8 rounded-xl bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-sm shadow-lg shadow-cyan-500/25 flex items-center justify-center gap-2 transition-all hover:scale-[1.02] active:scale-[0.98] disabled:opacity-50 disabled:pointer-events-none"
          >
            {isAnalyzing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Running Scan...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-current" />
                <span>Run Analysis</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live WebSocket Progress Section */}
      {isAnalyzing && (
        <ProgressTracker
          currentStage={currentStage}
          progressPercent={progressPercent}
        />
      )}

      {/* Render Analysis Report when complete */}
      {analysisResult && (
        <Report data={analysisResult} />
      )}
    </div>
  );
};
