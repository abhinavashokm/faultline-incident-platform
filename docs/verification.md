# Verification

The checks below describe expected behavior and point to existing tests. Their results are pending a fresh run. Load and real worker restart results are pending as well.

| Behavior | Expected result | Existing check |
|---|---|---|
| Duplicate error delivery | Replaying the same event ID stores one occurrence and increments the issue count once. | [Processing storage tests](../services/processing/tests/integration/test_storage.py) |
| Offset handling and redelivery | Successful processing commits the offset. A transient failure leaves it uncommitted, and a permanent message failure is skipped so the next record can be handled. | [Processing consumer unit tests](../services/processing/tests/unit/test_consumer.py) |
| Cross-workspace issue isolation | Lists exclude other workspaces' issues. Reading or patching another workspace's issue returns `404`, and the patch leaves the issue unchanged. | [Processing issue API tests](../services/processing/tests/api/test_issues_api.py) |
| Alerting isolation | Channel and rule access is workspace-scoped. Evaluation uses rules from the event's workspace and records that workspace on queued deliveries. | [Alerting tenant isolation tests](../services/alerting/tests/api/test_tenant_isolation.py) |

## Run the targeted Processing tests

From `services/processing`, use a Python 3.12 virtual environment:

```bash
python -m pip install -e ../../libs/faultline-auth -e ../../libs/events -e '.[dev]'
python -m pytest tests/unit/test_consumer.py
```

Set `PROCESSING_TEST_DATABASE_URL` to a dedicated PostgreSQL test database. Apply the Processing migrations to that database before running the storage and API checks.

```bash
PROCESSING_DATABASE_URL="$PROCESSING_TEST_DATABASE_URL" alembic upgrade head
python -m pytest -rs tests/integration/test_storage.py tests/api/test_issues_api.py
```

The fixtures can skip database-backed tests when the database is unreachable. Check the skip reasons in the output.

## Verify a real worker restart

In a disposable local Compose stack, feed a valid error event through the SDK while the error worker is stopped. Start the worker again and verify that the issue appears with one occurrence. To verify the commit gap specifically, interrupt the worker after its database commit and before its Kafka offset commit, then restart it with the same consumer group. Check that the record is redelivered and the issue still has one occurrence. The consumer unit tests simulate error handling. This separate check needs a running broker and database.

## Record a load test

Record the commit, hardware, deployment configuration, workload, duration, and offered event rate. Report accepted events per second, HTTP failure rate, p95 ingest latency, and the end-to-end delay from submission to issue visibility. Record consumer lag during the run and how long the backlog takes to drain.
