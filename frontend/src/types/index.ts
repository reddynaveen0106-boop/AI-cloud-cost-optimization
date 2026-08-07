export interface User {
  id: number;
  email: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: {
    id: number;
    email: string;
  };
}

export interface RegionItem {
  region_name: string;
  endpoint: string;
  opt_in_status?: string;
}

export interface RegionsResponse {
  regions: RegionItem[];
  count: number;
}

export interface AIIssueItem {
  resource_name: string;
  resource_type: string;
  severity: 'HIGH' | 'MEDIUM' | 'LOW';
  category: string;
  description: string;
  estimated_monthly_savings: number;
  confidence_score: number;
  fix_commands: string[];
}

export interface AIAnalysisResult {
  metadata: {
    model: string;
    analysis_timestamp: string;
    analysis_duration_ms: number;
  };
  executive_summary: string;
  total_estimated_monthly_savings: number;
  issues: AIIssueItem[];
  best_practices: string[];
}

export interface ResourceItem {
  resource_name: string;
  resource_type: string;
  aws_service: string;
  region: string;
  availability_zone: string;
  status: string;
  instance_type_sku?: string;
  tags: Record<string, string>;
  recommendation: string;
}

export interface ScanSummary {
  total_resources: number;
  ec2: number;
  ebs: number;
  rds: number;
  lambda_functions: number;
  s3: number;
  elb: number;
  nat_gateway: number;
  [key: string]: number;
}

export interface CostByServiceItem {
  service_name: string;
  amount: number;
  unit: string;
}

export interface CostAnalysis {
  total_monthly_cost: number;
  currency: string;
  period_start?: string;
  period_end?: string;
  cost_by_service: CostByServiceItem[];
  note?: string;
}

export interface AnalyzeResponse {
  analysis_id: string;
  caller_identity: {
    account_id: string;
    user_id: string;
    arn: string;
  };
  region: string;
  execution_time_seconds: number;
  summary: ScanSummary;
  cost_analysis: CostAnalysis;
  ai_analysis: AIAnalysisResult;
  resources: ResourceItem[];
}

export interface AnalysisHistoryItem {
  id: string;
  user_id?: number;
  region: string;
  resources_scanned: number;
  issues_found: number;
  estimated_monthly_savings: string;
  analysis_result: AnalyzeResponse;
  status: string;
  created_at: string;
}

export interface AnalysisHistoryResponse {
  history: AnalysisHistoryItem[];
  count: number;
}

export interface ProgressUpdate {
  analysis_id: string;
  stage: string;
  progress_percent: number;
  timestamp: string;
}
