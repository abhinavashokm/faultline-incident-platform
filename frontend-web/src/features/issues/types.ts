export type IssueStatus = "unresolved" | "resolved" | "ignored";
export type IssueLevel = "error" | "warning" | "info" | "fatal";

export interface IssueListItem {
  id: string;
  title: string;
  exceptionType: string;
  culprit: string;
  status: IssueStatus;
  level: IssueLevel;
  occurrenceCount: number;
  affectedUsersCount: number;
  environment: string;
  firstSeen: string;
  lastSeen: string;
  firstRelease: string;
  lastRelease: string;
  commitSha: string;
}

export interface StackFrame {
  file: string;
  line: number;
  function: string;
  inApp: boolean;
  contextLines?: {
    line: number;
    code: string;
    isError?: boolean;
  }[];
}

export interface Breadcrumb {
  timestamp: string;
  category: "http" | "db" | "log" | "auth" | "navigation";
  message: string;
  level?: "info" | "warning" | "error";
  data?: Record<string, unknown>;
}

export interface EventDetail {
  id: string;
  issueId: string;
  occurredAt: string;
  receivedAt: string;
  level: IssueLevel;
  exceptionType: string;
  message: string;
  environment: string;
  release: string;
  fingerprint: string;
  stackFrames: StackFrame[];
  breadcrumbs: Breadcrumb[];
  tags: Record<string, string>;
  user?: {
    id: string;
    ipAddress: string;
    email?: string;
  };
  request?: {
    method: string;
    url: string;
    statusCode?: number;
    headers?: Record<string, string>;
  };
}

export interface InvestigationResult {
  id: string;
  status: "completed" | "in_progress" | "queued" | "failed";
  confidence: number; // e.g. 98%
  likelyCause: string;
  recommendation: string;
  mitigationPlan: string;
  createdAt: string;
}

export interface IssueDetail extends IssueListItem {
  fingerprint: string;
  eventsTimeline: { time: string; count: number }[];
  latestEvent: EventDetail;
  totalEvents: number;
  investigation?: InvestigationResult;
}

export interface IssueFilterParams {
  status?: IssueStatus;
  environment?: string;
  timeRange?: "1h" | "24h" | "7d" | "14d" | "30d";
  search?: string;
  cursor?: string;
  limit?: number;
}

export interface IssueListResponse {
  items: IssueListItem[];
  totalCount: number;
  nextCursor?: string;
  hasMore: boolean;
}

