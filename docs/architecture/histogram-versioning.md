# Histogram versioning

## What is the histogram and where is it used?
Our performance metrics include **request latency** (how long requests take).
Sending every single latency value would be too much data, so the SDK groups them into buckets and sends only the counts.

Example: with buckets [50, 100, 250, 500, 1000, inf] ms, the counts [40, 30, 15, 10, 4, 1] mean:
- 40 requests took up to 50 ms
- 30 took 50-100 ms
- 15 took 100-250 ms
- 10 took 250-500 ms
- 4 took 500-1000 ms
- 1 took over 1000 ms

This list of counts is the `latency_histogram` field in the performance metrics.

Three parts handle it:
- **SDK:** measures latencies and counts them into buckets.
- **Ingestion service:** receives the counts, validates them, and publishes them to the `performance-metrics` topic.
- **Processing service:** reads them from Kafka, stores them in the DB, and uses them to calculate things like p50/p95/p99.

## Why versioning is needed
The counts are just numbers. They only mean something if everyone knows the bucket boundaries.
If the SDK uses one set of boundaries and the processor assumes another, the percentiles come out wrong and nothing shows an error.
So the boundaries must be identical everywhere, and they must be tracked by version.

## Decision
- Bucket boundaries are immutable, versioned constants.
  - v1 (upper bounds in ms): [50, 100, 250, 500, 1000, inf]
- The SDK sends counts as a list plus `histogram_version`.
- Each component (SDK, ingestion, processor) keeps its own copy of the constants.
- A contract test in each one asserts that v1 matches the list above.
- Ingestion rejects unknown versions and wrong-length lists.
- The processor sends unknown versions to `performance-metrics-dlq` instead of guessing.
- Every DB row stores `histogram_version`. Rows with different versions are never merged.
- Existing versions are never edited or removed. New boundaries mean a new version.

## Consequences
- Old SDK versions stay in use for a long time, so old versions must be supported indefinitely.
- Copies can drift apart, so the contract tests are required.
- Adding a new version means deploying in this order: processor, then ingestion, then SDK.