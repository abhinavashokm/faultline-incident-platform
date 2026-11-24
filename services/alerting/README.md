# Faultline Alerting & Notification Service

The Alerting & Notification Service manages alert rules, alert states, and notification delivery channels.
It operates as a unified service with two distinct internal modules/roles:
- **`ROLE=alerts`**: Evaluates alert rules from Kafka events (`issue-events`, `regression-events`) and manages alert states.
- **`ROLE=delivery`**: Reliably dispatches queued notifications to external channels (Slack, Webhooks) via an internal outbox pattern.
- **HTTP API**: Serves endpoints for alert rules, alerts, notification channels, and delivery history.

### Test a notification channel

Send an authenticated `POST /api/v1/projects/{project_id}/notification-channels/{channel_id}/test`
with an empty request body. The endpoint sends a sample using the saved webhook or email
settings, including for disabled channels. It returns `204` when the receiver accepts
the request, `404` for a channel outside the active workspace or project, `409` for
an unsupported channel type, or `502` on delivery failure. Test sends do not create an
alert or a delivery history entry.

Webhook tests and regular webhook alerts use the same sender. Configure the same
`ALERTING_WEBHOOK_ENCRYPTION_KEY` in the API and delivery worker. The sender POSTs JSON
to a public HTTPS destination with a five-second deadline and does not follow redirects.
The `X-Faultline-Signature` header contains `sha256=<hex digest>`, computed as HMAC-SHA256
over the exact request body using the signing secret returned at channel creation.
`X-Faultline-Delivery-Id` identifies the outbound delivery. Test requests use
`event_type: "notification.test"` with `project_id`, `channel_id`, and `message` fields.
