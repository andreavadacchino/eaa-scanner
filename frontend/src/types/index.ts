// Core types for the EAA Scanner application

export interface ScanConfiguration {
  url: string
  company_name: string
  email: string
  scanners: ScannerConfig
  methodology: MethodologyConfig
  crawler: CrawlerConfig
}

export interface ScannerConfig {
  wave: boolean
  pa11y: boolean
  axe: boolean
  lighthouse: boolean
}

export interface MethodologyConfig {
  sample_methodology: 'manual' | 'wcag_em' | 'smart' | 'comprehensive'
  analysis_depth: 'quick' | 'standard' | 'thorough' | 'comprehensive'
  max_pages: number
  include_pdfs: boolean
  smart_selection: boolean
}

export interface CrawlerConfig {
  max_pages: number
  max_depth: number
  follow_external: boolean
  timeout_ms: number
  use_playwright: boolean
  excluded_patterns?: string[]
  allowed_domains?: string[]
}

// Discovery Phase Types
export interface DiscoveryStatus {
  status: 'idle' | 'discovering' | 'completed' | 'error'
  progress: number
  current_url?: string
  discovered_count: number
  total_estimated?: number
  error_message?: string
  start_time?: Date
  estimated_completion?: Date
}

export interface DiscoveredPage {
  url: string
  title: string
  depth: number
  page_type: PageType
  category: PageCategory
  template_group?: string
  priority: Priority
  metadata: PageMetadata
  selected: boolean
  accessibility_hints: AccessibilityHint[]
}

export enum PageType {
  HOME = 'home',
  CATEGORY = 'category',
  PRODUCT = 'product',
  CONTENT = 'content',
  FORM = 'form',
  MEDIA = 'media',
  DOCUMENT = 'document',
  OTHER = 'other'
}

export enum PageCategory {
  CRITICAL = 'critical',
  IMPORTANT = 'important', 
  REPRESENTATIVE = 'representative',
  OPTIONAL = 'optional'
}

export enum Priority {
  HIGH = 'high',
  MEDIUM = 'medium',
  LOW = 'low'
}

export interface PageMetadata {
  word_count: number
  form_count: number
  image_count: number
  link_count: number
  heading_structure: string[]
  has_media: boolean
  has_interactive_elements: boolean
  estimated_complexity: number
}

export interface AccessibilityHint {
  type: 'info' | 'warning' | 'potential_issue'
  message: string
  wcag_reference?: string
}

// Scanning Phase Types
export interface ScanProgress {
  scan_id: string
  status: 'idle' | 'starting' | 'scanning' | 'processing' | 'completed' | 'error'
  overall_progress: number
  current_phase: ScanPhase
  pages_total: number
  pages_completed: number
  page_progress: PageScanProgress[]
  scanner_status: ScannerStatus
  start_time?: Date
  estimated_completion?: Date
  error_message?: string
}

export enum ScanPhase {
  INITIALIZING = 'initializing',
  SCANNING_PAGES = 'scanning_pages', 
  PROCESSING_RESULTS = 'processing_results',
  GENERATING_REPORT = 'generating_report',
  FINALIZING = 'finalizing'
}

export interface PageScanProgress {
  url: string
  status: 'queued' | 'scanning' | 'completed' | 'error'
  progress: number
  scanner_results: { [scanner: string]: 'pending' | 'running' | 'completed' | 'error' }
  issues_found?: number
  error_message?: string
}

export interface ScannerStatus {
  wave: ScannerProgress
  pa11y: ScannerProgress
  axe: ScannerProgress
  lighthouse: ScannerProgress
}

export interface ScannerProgress {
  status: 'idle' | 'running' | 'completed' | 'error'
  progress: number
  pages_processed: number
  issues_found: number
  error_message?: string
}

// Results Types
export interface ScanResults {
  scan_id: string
  configuration: ScanConfiguration
  summary: ScanSummary
  pages: PageResult[]
  issues: Issue[]
  compliance: ComplianceAssessment
  report_urls: ReportUrls
  metadata: ScanMetadata
}

export interface ScanSummary {
  total_pages: number
  total_issues: number
  issues_by_severity: { [severity: string]: number }
  issues_by_wcag: { [criterion: string]: number }
  compliance_score: number
  compliance_level: 'conforme' | 'parzialmente_conforme' | 'non_conforme'
  scan_duration: number
}

export interface PageResult {
  url: string
  title: string
  issues: Issue[]
  scanner_results: { [scanner: string]: any }
  compliance_score: number
  scan_duration: number
}

export interface Issue {
  id: string
  code: string
  title: string
  description: string
  severity: 'Critical' | 'High' | 'Medium' | 'Low'
  wcag_criterion: string
  wcag_level: 'A' | 'AA' | 'AAA'
  source_scanner: string
  page_url: string
  selector?: string
  context?: string
  recommendation: string
  help_url?: string
}

export interface ComplianceAssessment {
  overall_level: 'conforme' | 'parzialmente_conforme' | 'non_conforme'
  wcag_aa_score: number
  eaa_compliance: boolean
  critical_issues: number
  blocking_issues: Issue[]
  requirements_status: { [requirement: string]: 'met' | 'partially_met' | 'not_met' }
}

export interface ReportUrls {
  html: string
  pdf?: string
  json: string
  csv?: string
}

export interface ScanMetadata {
  timestamp: Date
  duration: number
  version: string
  methodology_used: string
  scanners_used: string[]
  pages_selected: number
  total_discovered: number
}

// WebSocket Events
export interface WebSocketEvent {
  type: string
  data: any
  timestamp: Date
}

export interface DiscoveryUpdateEvent {
  type: 'discovery_update'
  data: {
    status: DiscoveryStatus
    discovered_pages?: DiscoveredPage[]
    new_page?: DiscoveredPage
  }
}

export interface ScanUpdateEvent {
  type: 'scan_update'
  data: {
    scan_id: string
    progress: ScanProgress
  }
}

export interface ScanCompleteEvent {
  type: 'scan_complete'
  data: {
    scan_id: string
    results: ScanResults
  }
}

// UI State Types
export interface WorkflowStep {
  id: number
  name: string
  title: string
  description: string
  status: 'pending' | 'active' | 'completed' | 'error'
  optional?: boolean
}

export interface UIState {
  current_step: number
  is_loading: boolean
  error_message?: string
  sidebar_open: boolean
  theme: 'light' | 'dark'
}

// Selection Strategy Types
export interface SelectionStrategy {
  id: string
  name: string
  description: string
  max_pages: number
  criteria: SelectionCriterion[]
}

export interface SelectionCriterion {
  type: 'page_type' | 'priority' | 'template' | 'complexity' | 'user_flow'
  weight: number
  filter: any
}

// Smart Selection Types
export interface SmartSelectionConfig {
  strategy: 'wcag_em' | 'risk_based' | 'coverage_optimal' | 'user_journey'
  max_pages: number
  include_critical: boolean
  balance_templates: boolean
  prioritize_complex: boolean
}

export interface SmartSelectionResult {
  selected_pages: DiscoveredPage[]
  rationale: SelectionRationale[]
  coverage_analysis: CoverageAnalysis
  estimated_scan_time: number
}

export interface SelectionRationale {
  page_url: string
  reason: string
  score: number
  criteria_matched: string[]
}

export interface CoverageAnalysis {
  page_types_covered: PageType[]
  template_groups_covered: string[]
  complexity_distribution: { [level: string]: number }
  user_flows_covered: string[]
  estimated_wcag_coverage: number
}