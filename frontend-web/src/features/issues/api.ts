import { delay, ApiError } from "@/lib/api-client";
import {
  IssueListItem,
  IssueDetail,
  IssueListResponse,
  IssueFilterParams,
  IssueStatus,
  EventDetail,
  InvestigationResult,
} from "./types";

// In-memory mock issues list
let mockIssuesData: IssueListItem[] = [
  {
    id: "77777777-7777-4777-8777-777777777777",
    title: "DatabaseConnectionError: pool timeout after 5000ms",
    exceptionType: "DatabaseConnectionError",
    culprit: "services/processing/db/pool.py:142 in acquire_connection",
    status: "unresolved",
    level: "fatal",
    occurrenceCount: 4218,
    affectedUsersCount: 382,
    environment: "production",
    firstSeen: "2026-10-30T06:12:00Z",
    lastSeen: "2026-10-31T09:42:00Z",
    firstRelease: "v1.8.0",
    lastRelease: "v1.8.0",
    commitSha: "42b56e9",
  },
  {
    id: "88888888-8888-4888-8888-888888888888",
    title: "KafkaConsumerCommitError: offset commit failed after transaction commit",
    exceptionType: "KafkaConsumerCommitError",
    culprit: "services/processing/consumer/worker.py:215 in commit_offset",
    status: "unresolved",
    level: "error",
    occurrenceCount: 894,
    affectedUsersCount: 42,
    environment: "production",
    firstSeen: "2026-10-29T14:20:00Z",
    lastSeen: "2026-10-31T08:15:00Z",
    firstRelease: "v1.7.4",
    lastRelease: "v1.8.0",
    commitSha: "8c924ce",
  },
  {
    id: "99999999-9999-4999-8999-999999999999",
    title: "TokenVerificationError: Signature has expired for workspace JWT",
    exceptionType: "TokenVerificationError",
    culprit: "libs/faultline_auth/jwt.py:84 in verify_claims",
    status: "unresolved",
    level: "warning",
    occurrenceCount: 320,
    affectedUsersCount: 28,
    environment: "staging",
    firstSeen: "2026-10-28T09:00:00Z",
    lastSeen: "2026-10-31T07:30:00Z",
    firstRelease: "v1.8.0",
    lastRelease: "v1.8.0",
    commitSha: "618c0d7",
  },
  {
    id: "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    title: "ZeroDivisionError: float division by zero in SLO calculation",
    exceptionType: "ZeroDivisionError",
    culprit: "services/processing/metrics/aggregator.py:53 in compute_slo",
    status: "resolved",
    level: "error",
    occurrenceCount: 154,
    affectedUsersCount: 12,
    environment: "production",
    firstSeen: "2026-10-27T11:40:00Z",
    lastSeen: "2026-10-30T16:00:00Z",
    firstRelease: "v1.6.2",
    lastRelease: "v1.7.0",
    commitSha: "b391174",
  },
  {
    id: "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
    title: "RateLimitExceeded: 429 Too Many Requests on ingestion endpoint",
    exceptionType: "RateLimitExceeded",
    culprit: "services/ingestion/router/ingest.py:91 in rate_limit_check",
    status: "ignored",
    level: "info",
    occurrenceCount: 12480,
    affectedUsersCount: 890,
    environment: "production",
    firstSeen: "2026-10-25T08:00:00Z",
    lastSeen: "2026-10-31T09:00:00Z",
    firstRelease: "v1.5.0",
    lastRelease: "v1.8.0",
    commitSha: "414c313",
  },
];

// Mock event details with stack trace and breadcrumbs
const mockDetailedEvents: Record<string, EventDetail> = {
  "77777777-7777-4777-8777-777777777777": {
    id: "evt_28eb06ca-8db8-4696-9e05-dcfc73536fa9",
    issueId: "77777777-7777-4777-8777-777777777777",
    occurredAt: "2026-10-31T09:42:00Z",
    receivedAt: "2026-10-31T09:42:01Z",
    level: "fatal",
    exceptionType: "DatabaseConnectionError",
    message: "Connection pool exhausted after 5000ms timeout. Max connections (20) reached.",
    environment: "production",
    release: "v1.8.0",
    fingerprint: "9f2c4e1b7a3d5c6e8f0a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60",
    stackFrames: [
      {
        file: "/usr/local/lib/python3.12/site-packages/starlette/routing.py",
        line: 677,
        function: "__call__",
        inApp: false,
        contextLines: [
          { line: 675, code: "            response = await func(request)" },
          { line: 676, code: "        except Exception as exc:" },
          { line: 677, code: "            raise exc" },
        ],
      },
      {
        file: "/usr/local/lib/python3.12/site-packages/fastapi/routing.py",
        line: 274,
        function: "run_endpoint_function",
        inApp: false,
        contextLines: [
          { line: 272, code: "    if is_coroutine:" },
          { line: 273, code: "        return await dependant.call(**values)" },
          { line: 274, code: "    return await run_in_threadpool(dependant.call, **values)" },
        ],
      },
      {
        file: "services/processing/router/issues.py",
        line: 88,
        function: "get_issue_list",
        inApp: true,
        contextLines: [
          { line: 86, code: "    service = get_processing_service()" },
          { line: 87, code: "    workspace_id = auth.workspace_id" },
          { line: 88, code: "    return await service.fetch_issues(workspace_id=workspace_id)" },
        ],
      },
      {
        file: "services/processing/service/errors.py",
        line: 114,
        function: "fetch_issues",
        inApp: true,
        contextLines: [
          { line: 112, code: "    async with self.repo.transaction() as session:" },
          { line: 113, code: "        stmt = select(Issue).where(Issue.workspace_id == workspace_id)" },
          { line: 114, code: "        result = await session.execute(stmt)" },
        ],
      },
      {
        file: "services/processing/db/pool.py",
        line: 142,
        function: "acquire_connection",
        inApp: true,
        contextLines: [
          { line: 140, code: "    async with async_timeout(self._timeout_seconds):" },
          { line: 141, code: "        if self._pool.empty() and self._active >= self._max_size:" },
          { line: 142, code: "            raise DatabaseConnectionError('pool timeout after 5000ms')", isError: true },
          { line: 143, code: "        conn = await self._pool.acquire()" },
        ],
      },
      {
        file: "/usr/local/lib/python3.12/site-packages/asyncpg/pool.py",
        line: 198,
        function: "acquire",
        inApp: false,
        contextLines: [
          { line: 196, code: "    if self._queue.full():" },
          { line: 197, code: "        raise exceptions.TooManyConnectionsError()" },
          { line: 198, code: "    return await ch._acquire(timeout)" },
        ],
      },
    ],
    // TODO(mock): Contextual breadcrumbs telemetry planned in SDK spec; providing mock history
    breadcrumbs: [
      {
        timestamp: "09:41:55.120",
        category: "auth",
        message: "JWT signature verified locally (workspace_id: ws_4409ef12)",
        level: "info",
      },
      {
        timestamp: "09:41:55.240",
        category: "http",
        message: "POST /api/v1/projects/proj_9a82f1b4/issues/query [status: 200]",
        level: "info",
      },
      {
        timestamp: "09:41:57.400",
        category: "db",
        message: "Acquiring DB transaction connection (active_conn: 19/20)",
        level: "info",
      },
      {
        timestamp: "09:41:59.850",
        category: "db",
        message: "DB connection wait exceeding 2000ms threshold (pool queue depth: 8)",
        level: "warning",
      },
      {
        timestamp: "09:42:00.120",
        category: "db",
        message: "TimeoutError: pool timeout after 5000ms",
        level: "error",
      },
    ],
    tags: {
      "runtime.version": "CPython 3.12.3",
      "os.name": "Linux 6.8.0-cloud",
      "server.name": "worker-proc-useast-7f9b",
      "cluster": "us-east-k8s-prod",
      "release": "v1.8.0",
      "commit": "42b56e9",
      "handled": "no",
      "mechanism": "asgi.exception_handler",
    },
    user: {
      id: "usr_elena_vance",
      ipAddress: "192.0.2.45",
      email: "elena@acme-cloud.io",
    },
    request: {
      method: "POST",
      url: "https://api.acme-cloud.io/api/v1/projects/proj_9a82f1b4/issues/query",
      statusCode: 500,
      headers: {
        "host": "api.acme-cloud.io",
        "user-agent": "Faultline-Agent/1.0",
        "x-request-id": "req_8f192bfa9102",
      },
    },
  },
};

// TODO(mock): Investigation / AI Service integration pending; using mock root cause synthesis
const mockInvestigation: InvestigationResult = {
  id: "inv_9b82fa7e",
  status: "completed",
  confidence: 96,
  likelyCause:
    "Commit 42b56e9 introduced an unhandled exception branch in worker.py that bypasses the async context manager release block, preventing asyncpg connections from returning to the pool.",
  recommendation:
    "Refactor `db_pool.acquire()` to always guarantee `conn.release()` inside a try/finally or `async with db_pool.acquire() as conn:` block in `services/processing/db/pool.py:140`.",
  mitigationPlan:
    "Increase connection pool ceiling `DB_POOL_MAX_SIZE=50` temporarily or roll back to release `v1.7.4` while the fix is verified in staging.",
  createdAt: "2026-10-31T09:44:00Z",
};

export async function listIssuesApi(
  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  _workspaceSlug: string,
  filters: IssueFilterParams = {}
): Promise<IssueListResponse> {
  await delay(400);

  let filtered = [...mockIssuesData];

  if (filters.status) {
    filtered = filtered.filter((i) => i.status === filters.status);
  }

  if (filters.environment && filters.environment !== "all") {
    filtered = filtered.filter((i) => i.environment.toLowerCase() === filters.environment?.toLowerCase());
  }

  if (filters.search) {
    const q = filters.search.toLowerCase();
    filtered = filtered.filter(
      (i) =>
        i.title.toLowerCase().includes(q) ||
        i.culprit.toLowerCase().includes(q) ||
        i.exceptionType.toLowerCase().includes(q) ||
        i.commitSha.toLowerCase().includes(q)
    );
  }

  const limit = filters.limit || 25;
  const items = filtered.slice(0, limit);

  return {
    items,
    totalCount: filtered.length,
    hasMore: filtered.length > limit,
  };
}

export async function getIssueDetailApi(
  _workspaceSlug: string,
  issueId: string
): Promise<IssueDetail> {
  await delay(450);

  const found = mockIssuesData.find((i) => i.id === issueId);
  if (!found) {
    throw new ApiError(404, `Issue with ID ${issueId} not found`);
  }

  const eventDetail =
    mockDetailedEvents[issueId] || {
      ...mockDetailedEvents["77777777-7777-4777-8777-777777777777"],
      id: "evt_" + Math.random().toString(36).substring(2, 10),
      issueId,
      exceptionType: found.exceptionType,
      message: found.title,
      environment: found.environment,
      release: found.lastRelease,
    };

  return {
    ...found,
    fingerprint: eventDetail.fingerprint,
    totalEvents: found.occurrenceCount,
    latestEvent: eventDetail,
    investigation: issueId === "77777777-7777-4777-8777-777777777777" ? mockInvestigation : undefined,
    eventsTimeline: [
      { time: "09:00", count: 420 },
      { time: "09:10", count: 680 },
      { time: "09:20", count: 1120 },
      { time: "09:30", count: 950 },
      { time: "09:40", count: 1240 },
      { time: "09:50", count: 808 },
    ],
  };
}

export async function updateIssueStatusApi(
  issueId: string,
  status: IssueStatus
): Promise<{ success: boolean; issue: IssueListItem }> {
  await delay(350);

  const issue = mockIssuesData.find((i) => i.id === issueId);
  if (!issue) {
    throw new ApiError(404, `Issue with ID ${issueId} not found`);
  }

  issue.status = status;
  return { success: true, issue };
}

export async function bulkUpdateIssueStatusApi(
  issueIds: string[],
  status: IssueStatus
): Promise<{ success: boolean; updatedCount: number }> {
  await delay(450);

  let updatedCount = 0;
  mockIssuesData = mockIssuesData.map((issue) => {
    if (issueIds.includes(issue.id)) {
      updatedCount++;
      return { ...issue, status };
    }
    return issue;
  });

  return { success: true, updatedCount };
}

