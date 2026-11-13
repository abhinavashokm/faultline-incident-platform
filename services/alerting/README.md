# Faultline Alerting & Notification Service

The Alerting & Notification Service manages alert rules, alert states, and notification delivery channels.
It operates as a unified service with two distinct internal modules/roles:
- **`ROLE=alerts`**: Evaluates alert rules from Kafka events (`issue-events`, `regression-events`) and manages alert states.
- **`ROLE=delivery`**: Reliably dispatches queued notifications to external channels (Slack, Webhooks) via an internal outbox pattern.
- **HTTP API**: Serves endpoints for alert rules, alerts, notification channels, and delivery history.
