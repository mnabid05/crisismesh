# Operations runbook

## Service-level objectives

- Operations API availability: 99.9% monthly.
- Incident list latency: p95 below 300 ms.
- Accepted-event propagation to SSE: p95 below 15 seconds.
- Source freshness: NWS below 10 minutes, EONET below 20 minutes, USGS below 10 minutes.

## First response

1. Confirm dashboard mode and source-health lag.
2. Check Kubernetes rollout and pod readiness.
3. Query API `/healthz`, `/readyz`, then `/metrics`.
4. Check Postgres connections and NATS `/varz`.
5. Identify whether the failure is source-specific, internal, or presentation-only.

## Common incidents

### A source is stale

- Inspect ingestor structured logs by `source`.
- Confirm upstream availability, TLS, rate limits, and the configured NWS User-Agent.
- Do not erase older incidents solely because polling failed.
- Mark the source degraded if lag exceeds its freshness objective.

### Allocation requests return 502

- Check intelligence `/healthz` and request/error metrics.
- Confirm the API service DNS and NetworkPolicy permit port 8090.
- Preserve incidents; disable the allocation action if the failure persists.
- Operators may use documented manual procedures until recovery.

### Database unavailable

- Production should fail readiness instead of accepting non-persistent writes.
- Check connection saturation, storage, and recent migrations.
- Restore from the latest point-in-time recovery position if corruption is confirmed.
- Reconcile NATS events against authoritative database rows after recovery.

### Elevated latency

- Compare API request rate/error counters with Postgres query latency.
- Check HPA capacity, CPU throttling, and connection pool saturation.
- Run the k6 read profile against staging before changing production limits.

## Rollback

`deploy.yml` uses atomic Helm upgrades. A failed readiness deadline rolls back automatically. For a manual rollback:

```bash
helm history crisismesh -n crisismesh
helm rollback crisismesh <REVISION> -n crisismesh --wait
```

Database migrations must be backwards-compatible for at least one application release.

## Disaster recovery exercise

Quarterly: restore Postgres into an isolated namespace, replay a fixture event set, verify incident counts and allocations, then record actual recovery time and recovery-point loss.

