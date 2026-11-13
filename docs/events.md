# Event Contracts (`libs/events`)

The `libs/events` library provides versioned event contracts and schemas shared across Faultline services.

## Architecture Principles
1. **No Business Logic**: Only Pydantic models, event envelope structures, and topic constants live here.
2. **Discriminated Unions**: Event variations are modeled as discriminated unions on `event_type`, enabling single-model additions for new event types.
3. **Immutability & Tenant Isolation**: Every event envelope includes `event_id`, `workspace_id`, `project_id`, `schema_version`, and `occurred_at`.

---

## Issue Events (`issue-events`)

- **Topic**: `issue-events` (constant `TOPIC_ISSUE_EVENTS`)
- **Key**: `issue_id` (stringified UUID, ensuring all occurrences and lifecycle transitions of an issue partition to the same Kafka partition).

### Envelope: `IssueCreatedEvent`
```json
{
  "event_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "event_type": "issue.created",
  "schema_version": 1,
  "occurred_at": "2026-11-13T09:00:00Z",
  "workspace_id": "11111111-1111-1111-1111-111111111111",
  "project_id": "22222222-2222-2222-2222-222222222222",
  "payload": {
    "issue_id": "33333333-3333-3333-3333-333333333333",
    "title": "ValueError: invalid literal for int() with base 10: 'foo'",
    "level": "error",
    "environment": "production",
    "release": "v1.0.0",
    "first_seen": "2026-11-13T09:00:00Z"
  }
}
```

---

## How to Add a New Issue Event Type

Follow this checklist whenever adding a new event type to the `issue-events` stream (e.g. `issue.regressed`, `issue.reopened`, `issue.occurrence_counted`):

1. **Define the Payload Model (`libs/events/src/faultline_events/envelope.py`)**:
   Create a new Pydantic payload model:
   ```python
   class IssueRegressedPayload(BaseModel):
       issue_id: UUID
       title: str
       resolved_in_release: str | None
       regressed_in_release: str | None
       regressed_at: datetime
   ```

2. **Define the Typed Event Envelope**:
   ```python
   class IssueRegressedEvent(BaseModel):
       event_id: UUID
       event_type: Literal["issue.regressed"] = "issue.regressed"
       schema_version: int = 1
       occurred_at: datetime
       workspace_id: UUID
       project_id: UUID
       payload: IssueRegressedPayload
   ```

3. **Update the Discriminated Union (`IssueEvent`)**:
   Add the new event class to `IssueEvent`:
   ```python
   IssueEvent = Annotated[
       Union[IssueCreatedEvent, IssueRegressedEvent],
       Field(discriminator="event_type"),
   ]
   ```
   Export the new types in `libs/events/src/faultline_events/__init__.py`.

4. **Register Consumer Handler (`services/alerting/app/alerts/consumer_handler.py`)**:
   Register a handler for the new `event_type`:
   ```python
   async def handle_issue_regressed_event(data: dict[str, Any], service: AlertEvaluationService) -> None:
       event = IssueRegressedEvent.model_validate(data)
       await service.handle_issue_regressed(event)

   registry.register("issue.regressed", handle_issue_regressed_event)
   ```

5. **(Optional) Add Rule Matcher & Evaluation (`services/alerting/app/alerts/matcher.py`)**:
   If the event triggers alerts, implement a `RuleMatcher` (e.g. `RegressionMatcher`), register it in `MATCHER_REGISTRY`, and add the evaluation logic in `AlertEvaluationService`.
