export interface Report {
  id: string;
  url: string;
  company_name: string;
  email: string;
  scan_type: 'simulate' | 'real' | 'unknown';
  status: 'pending' | 'in_progress' | 'completed' | 'failed';
  progress: number;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  output_path: string | null;
  html_report_path: string | null;
  pdf_report_path: string | null;
  score: number;
  compliance_level: 'conforme' | 'parzialmente_conforme' | 'non_conforme' | 'unknown';
  critical_issues: number;
  high_issues: number;
  medium_issues: number;
  low_issues: number;
}

export interface ReportsListResponse {
  reports: Report[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export interface ReportFilters {
  status?: string;
  order_by?: 'created_at' | 'completed_at' | 'company_name' | 'url';
  order_dir?: 'asc' | 'desc';
}