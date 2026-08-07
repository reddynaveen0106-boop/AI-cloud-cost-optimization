import { fetchWithAuth } from './api';
import { AuthResponse, RegionsResponse, AnalyzeResponse, AnalysisHistoryResponse } from '../types';
import { setStoredToken, setStoredUser, removeStoredToken } from '../utils/jwt';

export async function signupUser(email: string, password: string): Promise<AuthResponse> {
  const data = await fetchWithAuth<AuthResponse>('/api/auth/signup', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    setStoredToken(data.access_token);
    setStoredUser(data.user);
  }
  return data;
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  const data = await fetchWithAuth<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ email, password }),
  });
  if (data.access_token) {
    setStoredToken(data.access_token);
    setStoredUser(data.user);
  }
  return data;
}

export function logoutUser(): void {
  removeStoredToken();
}

export async function getRegions(): Promise<RegionsResponse> {
  return fetchWithAuth<RegionsResponse>('/api/regions');
}

export async function runAnalysis(region: string, analysisId: string): Promise<AnalyzeResponse> {
  return fetchWithAuth<AnalyzeResponse>('/api/analyze', {
    method: 'POST',
    body: JSON.stringify({ region, analysis_id: analysisId }),
  });
}

export async function getHistory(): Promise<AnalysisHistoryResponse> {
  return fetchWithAuth<AnalysisHistoryResponse>('/api/history');
}
