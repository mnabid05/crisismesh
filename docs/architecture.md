# Architecture

## Design principles

1. **Decision support, not automatic authority.** Algorithms may rank risk and resources, but an operator approves dispatch.
2. **Degrade visibly.** A failed source cannot silently disappear; source lag and scenario mode are explicit UI states.
3. **Normalize at the boundary.** Provider-specific payloads become one versioned incident contract before entering the platform.
4. **Scale the hot paths independently.** Ingestion, read APIs, scoring, and presentation do not need the same replica counts.
5. **Keep the demo honest.** Embedded records are marked as scenario data and never presented as live alerts.

## Service boundaries

### Ingestor — Go

The ingestor polls NASA EONET, NOAA/NWS, and USGS concurrently. Each adapter supplies a stable internal `Incident`, skips unusable geometry, applies provider attribution, and publishes through the operations API. HTTP clients have bounded timeouts and the scheduler continues when one source fails.

### Operations API — Go

The API owns incident and resource lifecycle, validation, persistence, write authentication, source summaries, SSE connections, and calls to the intelligence service. PostGIS is optional during development but required in production. NATS fans events across API replicas; a local broker keeps unit tests and single-process development simple.

### Intelligence — Python

The intelligence service is intentionally deterministic and explainable. Its risk model exposes contributing signals. Its allocator ranks available assets by capability coverage, great-circle distance, and capacity. The standard-library server minimizes supply-chain and cold-start overhead; the scoring modules are transport-independent.

### Command center — TypeScript / Next.js

The server component loads independent API resources in parallel. A single client boundary owns filters, selection, SSE, and allocation mutations. Standalone output permits non-Vercel deployment. The interface works without the back end using a clearly labeled embedded scenario.

## Data model

- `incidents`: provider identity, normalized hazard, PostGIS point, risk, confidence, population estimate, regions, metadata.
- `resources`: inventory, availability, capabilities, and staging point.
- `allocations`: immutable recommendation record with distance, ETA, suitability, rationale, and approval status.

Spatial indexes support proximity searches. Priority indexes support the main incident list. Source/external-ID uniqueness prevents duplicate provider events.

## Consistency and failure behavior

- Ingest uses idempotent upsert semantics.
- An intelligence timeout does not discard an incident; the API retains supplied/default risk and reports the degradation.
- NATS is used after persistence. Consumers therefore treat events as invalidation/update hints and retrieve authoritative state from the API.
- SSE is best-effort. Browsers reconnect automatically, and the dashboard begins from a server-rendered snapshot.
- Kubernetes readiness removes unhealthy replicas before liveness restarts them.

## Scaling path

| Pressure | Response |
|---|---|
| More source events | Add ingestor partitions by provider/region and use JetStream durable consumers |
| More dashboard users | Scale stateless API/web replicas; keep reads behind cache/CDN where safe |
| More spatial queries | Add PostGIS read replicas and bounded regional queries |
| More allocation work | Queue allocation requests and autoscale intelligence workers by lag |
| Regional outage | Deploy per-region API clusters with replicated event streams and DNS failover |

## Deliberate limitations

- Population exposure is provider/operator supplied; the MVP does not intersect official census rasters.
- The simplified frontend map avoids a commercial token. A production iteration should use MapLibre with hosted vector tiles.
- Authentication is an API-key boundary for machine writes. Human multi-tenant OIDC/RBAC is part of the roadmap.
- No recommendation causes real dispatch; that requires agency integration, policy, auditing, and formal validation.

