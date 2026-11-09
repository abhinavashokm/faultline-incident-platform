export type IssueStatus = "unresolved" | "resolved" | "ignored";
export type IssueLevel = "error" | "warning" | "info" | "fatal";
export type EventLevel = "error" | "warning" | "fatal";
export type EventType = "error" | "message";

export interface IssueListItem {
  id: string;
  title: string;
  exceptionType?: string | null;
  culprit?: string | null;
  status: IssueStatus;
  level: IssueLevel;
  occurrenceCount: number;
  affectedUsersCount: number;
  environment?: string | null;
  firstSeen: string;
  lastSeen: string;
  firstRelease?: string | null;
  lastRelease?: string | null;
  commitSha?: string | null;
}

export interface StackFrame {
  file: string;
  line?: number | null;
  function: string;
  inApp: boolean;
  contextLines?: {
    line: number;
    code: string;
    isError?: boolean;
  }[];
}

export interface EventListItem {
  id: string;
  issueId: string;
  occurredAt: string;
  receivedAt: string;
  level: EventLevel;
  exceptionType?: string | null;
  message?: string | null;
  environment?: string | null;
  release?: string | null;
  eventType: EventType;
}

export interface EventDetail extends EventListItem {
  fingerprint: string;
  stackFrames?: StackFrame[] | null;
  service?: string | null;
  routeTemplate?: string | null;
  httpMethod?: string | null;
  statusCode?: number | null;
  userHash?: string | null;
  context?: Record<string, unknown> | null;
}

export interface EventPaginationMeta {
  limit: number;
  hasMore: boolean;
  nextCursor?: string | null;
}

export interface EventListResponse {
  items: EventListItem[];
  meta: EventPaginationMeta;
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
  fingerprintVersion: number;
  resolvedAt?: string | null;
  resolvedInRelease?: string | null;
  createdAt: string;
  updatedAt: string;
  latestEvent?: EventDetail;
  totalEvents?: number;
}

export interface IssueFilterParams {
  status?: IssueStatus;
  environment?: string;
  timeRange?: "1h" | "24h" | "7d" | "14d" | "30d";
  search?: string;
  cursor?: string;
  limit?: number;
}

export interface PaginationMeta {
  limit: number;
  hasMore: boolean;
  nextCursor?: string | null;
}

export interface IssueListResponse {
  items: IssueListItem[];
  meta: PaginationMeta;
}

