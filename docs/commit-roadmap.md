# Delivery roadmap — 75 meaningful commits

This is the intended next development sequence, not a script for manufacturing history. Each commit should compile or deliberately document a reviewable design change, include tests when behavior changes, and be authored when the work actually happens.

## Foundation — 1–10

1. `docs: capture product charter and safety boundary`
2. `chore: establish polyglot monorepo layout`
3. `chore: add shared environment contract`
4. `docs: record service boundary ADR`
5. `feat(api): define normalized incident model`
6. `feat(api): add in-memory incident repository`
7. `test(api): cover priority filtering and lookup`
8. `feat(web): add server-rendered command shell`
9. `feat(web): add embedded scenario fallback`
10. `ci: add language-specific validation jobs`

## Live ingestion — 11–22

11. `feat(ingestor): add bounded HTTP client`
12. `feat(ingestor): normalize NASA EONET events`
13. `test(ingestor): cover EONET point geometry`
14. `feat(ingestor): normalize NWS CAP alerts`
15. `test(ingestor): cover polygon centroids`
16. `feat(ingestor): normalize USGS earthquakes`
17. `test(ingestor): cover magnitude severity mapping`
18. `feat(ingestor): poll sources concurrently`
19. `feat(ingestor): isolate partial source failures`
20. `feat(api): add idempotent incident upsert`
21. `feat(api): publish incident update events`
22. `test(contract): validate provider fixtures against schema`

## Persistence and streaming — 23–33

23. `feat(db): create PostGIS incident schema`
24. `feat(db): add spatial and priority indexes`
25. `feat(db): create resource inventory schema`
26. `feat(db): create immutable allocation records`
27. `feat(api): implement Postgres incident repository`
28. `test(api): add repository integration suite`
29. `feat(api): add NATS event broker`
30. `feat(api): expose SSE incident stream`
31. `test(api): cover stream subscription cleanup`
32. `feat(api): add source freshness summary`
33. `perf(api): bound queries and connection pools`

## Intelligence — 34–44

34. `feat(intelligence): define transport-independent models`
35. `feat(intelligence): implement explainable risk model`
36. `test(intelligence): bound and explain risk outputs`
37. `feat(intelligence): implement haversine distance`
38. `feat(intelligence): rank resource capabilities`
39. `feat(intelligence): account for capacity and availability`
40. `feat(intelligence): return recommendation rationale`
41. `test(intelligence): verify deterministic ranking`
42. `feat(api): orchestrate allocation requests`
43. `feat(api): persist recommended response packages`
44. `docs: document model limitations and approval rule`

## Operator experience — 45–57

45. `feat(web): add operational summary metrics`
46. `feat(web): render geographic incident field`
47. `feat(web): add risk-coded incident markers`
48. `feat(web): add hazard-layer filtering`
49. `feat(web): build priority incident queue`
50. `feat(web): build explainable incident detail`
51. `feat(web): render resource readiness`
52. `feat(web): connect live SSE updates`
53. `feat(web): add allocation action and states`
54. `feat(web): expose source-health lag`
55. `fix(web): preserve narrow-screen map usability`
56. `feat(web): support reduced-motion preferences`
57. `test(web): add critical command-flow browser test`

## Platform engineering — 58–68

58. `build: add hardened multi-stage containers`
59. `build: compose PostGIS NATS and observability locally`
60. `feat(helm): package stateless workloads and services`
61. `feat(helm): add health probes and resource limits`
62. `feat(helm): add horizontal autoscaling`
63. `feat(helm): add disruption budgets`
64. `security(helm): enforce non-root restricted containers`
65. `security(helm): add default-deny network policy`
66. `observability: expose API and intelligence metrics`
67. `observability: add Grafana operations dashboard`
68. `test(perf): add read-path SLO load profile`

## Delivery and proof — 69–75

69. `security: add CodeQL and filesystem scanning`
70. `release: publish provenance and SBOM-enabled images`
71. `deploy: add protected atomic Helm workflow`
72. `docs: publish on-call and rollback runbook`
73. `docs: publish system threat model`
74. `test: run pod-failure recovery exercise`
75. `docs: publish benchmark results and demo narrative`

## Resume proof to collect

- A public deployment or recorded incident replay.
- CI run demonstrating all language and Helm checks.
- k6 output with p50/p95/p99 and error rate.
- Grafana screenshot during a controlled load test.
- A short architecture decision explaining why Go, Python, PostGIS, NATS, and Kubernetes each solve a real constraint.
- An issue/PR trail showing tradeoffs, review, and iteration rather than commit-count optimization.

