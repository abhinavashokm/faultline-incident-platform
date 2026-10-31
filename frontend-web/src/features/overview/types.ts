export interface MetricCardData {
  id: string;
  label: string;
  value: string;
  rawNumber: number;
  change: string;
  isPositive: boolean;
  statusVariant: "default" | "error" | "warning" | "success" | "info" | "ai" | "neutral";
  sparkline: number[];
}

export interface TimeSeriesPoint {
  time: string;
  events: number;
  errors: number;
}

export interface IssueItem {
  id: string;
  title: string;
  culprit: string;
  project: string;
  environment: string;
  eventsCount: number;
  usersAffected: number;
  status: "unresolved" | "resolved" | "ignored";
  severity: "critical" | "warning" | "info";
  commitSha: string;
  lastSeen: string;
}

export interface ServiceHealthItem {
  id: string;
  name: string;
  platform: string;
  status: "healthy" | "degraded" | "outage";
  errorRate: string;
  p99Latency: string;
  activeIncidents: number;
  slo: string;
}

export interface OverviewDashboardData {
  metrics: MetricCardData[];
  timeSeries: TimeSeriesPoint[];
  recentIssues: IssueItem[];
  services: ServiceHealthItem[];
}
