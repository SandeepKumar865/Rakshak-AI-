// Types aligned directly with Rakshak AI FastAPI Backend JSON structures

export type FraudCategory =
  | 'OTP_FRAUD'
  | 'OLX_SCAM'
  | 'JOB_SCAM'
  | 'LOAN_FRAUD'
  | 'GENERAL_FRAUD';

export type CaseStatus =
  | 'New'
  | 'Under Review'
  | 'Investigating'
  | 'Resolved'
  | 'Closed';

export type CasePriority =
  | 'Critical'
  | 'High'
  | 'Medium'
  | 'Low';

export interface BankDetails {
  bank_name: string | null;
  bank_branch: string | null;
  account_number: string | null;
}

export interface SuspectDetails {
  names: string[];
  phone_numbers: string[];
  upi_ids: string[];
  emails: string[];
  bank_accounts: string[];
  telegram_handles: string[];
  websites_or_apps: string[];
  impersonated_entities: string[];
}

export interface LLMAnalysis {
  incident_summary: string;
  fraud_category: FraudCategory | string;
  fraud_category_label: string;
  victim_name: string | null;
  incident_date: string | null;
  incident_time: string | null;
  financial_loss: string | null;
  transaction_reference: string | null;
  payment_method: string | null;
  bank_details?: BankDetails;
  suspect_details?: SuspectDetails;
  missing_information?: string[];
  follow_up_question?: string;
  formal_complaint_draft?: string;
  language_detected?: string;
}

export interface CaseSummary {
  id: string;
  report_id: string;
  call_sid: string;
  caller_phone: string;
  name: string;
  language: 'hi' | 'en' | string;
  scenario: FraudCategory | string;
  scenario_label: string;
  scenario_label_hi: string;
  incident_date: string;
  incident_time: string;
  financial_loss: string;
  financial_loss_numeric: number;
  priority: CasePriority;
  status: CaseStatus;
  created_at: string;
  has_pdf: boolean;
  pdf_filename: string | null;
  pdf_download_url: string | null;
  has_analysis: boolean;
  story_snippet?: string;
}

export interface CaseDetail {
  id: string;
  report_id?: string;
  call_sid?: string;
  caller_phone?: string;
  caller_phone_masked?: string;
  name?: string;
  language?: 'hi' | 'en' | string;
  scenario?: FraudCategory | string;
  scenario_label?: string;
  scenario_label_hi?: string;
  story?: string;
  follow_up_question?: string;
  details?: string;
  financial_loss?: string;
  financial_loss_numeric?: number;
  incident_date?: string;
  incident_time?: string;
  priority: CasePriority;
  status: CaseStatus;
  created_at?: string;
  started_at?: string;
  completed_at?: string;
  updated_at?: string;
  bank_details?: BankDetails;
  suspect_details?: SuspectDetails;
  missing_information?: string[];
  formal_complaint_draft?: string;
  llm_analysis?: LLMAnalysis;
  pdf_filename?: string | null;
  pdf_download_url?: string | null;
}

export interface KPIStats {
  total_complaints: number;
  today_complaints: number;
  pending_unreviewed: number;
  high_priority_cases: number;
  total_reported_loss: number;
  reports_generated: number;
}

export interface CategoryBreakdown {
  name: string;
  count: number;
}

export interface PriorityBreakdown {
  priority: CasePriority;
  count: number;
}

export interface StatusBreakdown {
  status: CaseStatus;
  count: number;
}

export interface LanguageBreakdown {
  language: string;
  count: number;
}

export interface TimelineDataPoint {
  date: string;
  count: number;
  loss: number;
}

export interface DashboardStats {
  status: string;
  kpis: KPIStats;
  breakdowns: {
    categories: CategoryBreakdown[];
    priorities: PriorityBreakdown[];
    statuses: StatusBreakdown[];
    languages: LanguageBreakdown[];
    timeline: TimelineDataPoint[];
  };
  last_updated: string;
}

export interface ReportItem {
  filename: string;
  size_kb: number;
  created_at: string;
  download_url: string;
  report_id?: string | null;
  citizen_name?: string | null;
}

export interface ReportsResponse {
  status: string;
  total_reports: number;
  reports: ReportItem[];
}

export interface HealthStatus {
  status: 'healthy' | 'unhealthy' | 'unavailable';
  service: string;
  active_sessions: number;
  reports_generated: number;
  server_time: string;
  api_connected: boolean;
  latency_ms?: number;
}

export type OfficerRole =
  | 'Cyber Crime Officer'
  | 'Investigating Officer (IO)'
  | 'Superintendent of Police';

export interface OfficerUser {
  badge_number: string;
  name: string;
  role: OfficerRole | string;
  unit: string;
  station: string;
  session_token: string;
  login_time: string;
}

export type CallStatusType = 'initiated' | 'ringing' | 'in-progress' | 'completed' | 'failed';

export interface CallRecord {
  call_sid: string;
  destination: string;
  language: 'hi' | 'en' | string;
  status: CallStatusType;
  stage?: string;
  officer_badge?: string;
  is_twilio_dispatched?: boolean;
  notes?: string;
  report_id?: string | null;
  created_at: string;
  updated_at?: string;
}

export interface ReportDeliveryPayload {
  channel: 'sms' | 'whatsapp';
  phone_number: string;
}

