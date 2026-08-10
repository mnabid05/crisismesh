# Threat model

## Protected assets

- Integrity and freshness of incident records.
- Resource locations and availability.
- Allocation recommendations and approval history.
- Provider credentials, database connection strings, and write API keys.
- Availability during high-interest public emergencies.

## Primary threats and controls

| Threat | Control in this repository | Next production control |
|---|---|---|
| Forged ingestion event | API key on writes, schema validation, source attribution | mTLS workload identity and signed provider adapters |
| Oversized/malformed payload | 1 MiB limit, strict Go decoder, bounded Python body | WAF schema/rate policy |
| Compromised container | Non-root users and small multi-stage runtime images | Signed images and enforced runtime restrictions |
| Lateral movement | Private Compose network and explicit service ports | Per-service identities and managed egress controls |
| Secret disclosure | Runtime environment variables and protected GitHub environments | Managed secret store with cloud KMS rotation |
| Dependency compromise | CodeQL, Trivy, SBOM and build provenance | Cosign verification and dependency review |
| Bad algorithmic recommendation | Explainable signals, operator approval, no dispatch integration | Formal model validation and protected approval workflow |
| Upstream misinformation | Multi-source attribution and source-health visibility | Cross-source corroboration and analyst verification |
| Event flood / denial of service | Timeouts, size limits, caching, and constrained queries | API gateway rate limiting and regional edge protection |

## Privacy posture

The MVP stores hazard and organizational resource data, not individual survivor records. Adding personal data requires a new data-flow review, retention policy, encryption design, role model, and jurisdiction-specific compliance assessment.
