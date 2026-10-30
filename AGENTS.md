# Faultline: Rules for AI Coding Agents

Faultline is a monorepo for an error tracking and incident response platform with six services:

- `control-plane`
- `ingestion`
- `processing`
- `alerting`
- `incident`
- `investigation`

## Before Starting

Before designing or implementing anything, read:

- `.local/project-context.md` for the project architecture, decisions, and conventions.
- `.local/api/` for the relevant API contracts and specifications.
- `.local/db/` for database schemas and related database documentation.

Treat the documented schema as the source of truth. Never modify the schema or introduce schema changes without asking first.

If required context files are missing or ambiguous, inspect the available files and ask for clarification rather than inventing architectural decisions.

## Architecture

- Python 3.12, FastAPI, SQLAlchemy 2.0 async with asyncpg, Alembic, and aiokafka.
- Follow the layers: router/consumer → service → repository → models. Dependencies must point in one direction.
- Routers and consumers stay thin. Services own business rules and transaction boundaries.
- Repositories contain database queries only. They never commit transactions.
- Each service owns its database schema and Alembic migrations.
- Never create tables from application code. Do not use `create_all`.
- Never read or write another service's database.
- Services must never import another service's code.
- Shared packages are `libs/faultline-auth`, `libs/proto`, and `libs/events`. Use each package only for its intended shared responsibilities.
- Configuration comes from environment variables through `pydantic-settings`. Never hardcode service hosts, credentials, or environment-specific configuration.

## Kafka and Reliability

- Assume at-least-once delivery. Commit a Kafka offset only after the corresponding database transaction commits successfully.
- Consumer writes must be idempotent. Use event identifiers and appropriate database constraints or `ON CONFLICT DO NOTHING` where applicable.
- Permanent message failures must raise `PermanentError`. Log the failure and skip the message according to the existing consumer pattern. Dead-letter queue support is planned for later.
- Transient failures must propagate without committing the offset so the message can be redelivered.
- Follow existing retry, transaction, and consumer lifecycle patterns. Do not introduce a different reliability mechanism without asking.

## Conventions and Scope

- Use type hints throughout. Keep functions small and use logging rather than `print`.
- Follow the existing codebase's naming, formatting, error-handling, and testing conventions.
- Do not add dependencies, features, or files outside the requested task.
- Do not modify unrelated services or modules.
- Never run Docker, Alembic, or database commands. Tell me which commands I need to run.
- Do not claim tests or commands passed unless you actually ran them and observed the result.
- Finish coding tasks with a list of all files created or changed and a brief explanation of the changes.

## Authentication and Authorization

- `libs/faultline-auth` is the shared package for authentication logic, including local JWT verification. Do not duplicate JWT verification logic across services.
- Services verify JWTs locally. Never call the Control Plane on every request just to authenticate a token.
- Authentication establishes who the caller is. Each service is responsible for authorization, including workspace access, roles, and resource ownership.
- The active tenant is identified by `workspace_id` in the verified JWT. Derive the active workspace from this claim for ordinary authenticated requests.
- Never derive the active tenant from a request body, query parameter, or backend URL path.
- Backend API routes must not use workspace IDs or workspace slugs as tenant selectors. Scope tenant-owned database queries and writes using the authenticated workspace.
- Frontend browser URLs may contain workspace slugs for navigation, such as `/acme-inc/projects`. These slugs do not establish authorization and must not override the verified token's active workspace.
- Workspace switching uses the established `POST /api/v1/auth/switch-workspace` contract. The request may contain a target `workspace_id` in its body because it specifies which workspace the caller wants to switch to. The Control Plane must verify the caller's membership before issuing a token scoped to that workspace.
- Never assume a user belongs to exactly one workspace. Use `workspace_members` to represent membership and support users belonging to multiple workspaces.
- Every tenant-owned resource access must enforce workspace isolation. Never trust client-supplied workspace IDs or resource ownership to authorize access.
- Scope database reads, updates, and deletes to the authenticated workspace. Ensure that resource IDs cannot be used to access another workspace's data.
- If a workspace or resource is outside the caller's authorized scope, return `404` as required by the project contract rather than revealing that it exists.
- Follow the documented token claims and authorization patterns. Do not invent new claims, roles, or authorization rules.

## API and Service Boundaries

- Follow the API contract documented in `.local/api/` and `.local/project-context.md`. Do not invent routes, request fields, response fields, or status codes.
- Keep each service responsible for its own domain logic and data.
- Use shared event contracts from `libs/events` and shared protocol definitions from `libs/proto` where applicable.
- Do not bypass service boundaries by accessing another service's database or importing its implementation.
- Before adding an endpoint or event, check the existing contract and implementation for consistency.
- If the documented contract conflicts with existing code, flag the discrepancy instead of silently changing the intended design.

## Database and Migrations

- Treat the schema documentation in `.local/db/` as the authoritative database reference, following the source-of-truth designation in `.local/project-context.md`.
- Do not modify schema documentation, add tables or columns, change constraints, or create migrations without asking first.
- Do not generate or apply migrations. Tell me which commands to run when database changes are required and approved.
- Never use `create_all` or other application-startup mechanisms to create or alter tables.
- Keep database operations within the owning service and follow existing transaction patterns.

## Completion Checklist

Before finishing a task:

1. Confirm the changes follow `.local/project-context.md` and the relevant API and database documentation.
2. Check tenant isolation and authorization for every affected endpoint or consumer.
3. Check transaction boundaries, idempotency, and error handling where applicable.
4. Avoid unrelated changes and unrequested dependencies.
5. Report files created or changed, what was implemented, and any checks not run or commands the user must run.