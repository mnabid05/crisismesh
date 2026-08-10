# Vercel deployment

CrisisMesh can deploy as one Vercel project with two independently built services:

- `/` — Next.js command center from `apps/web`.
- `/intelligence` — FastAPI neural service from `services/intelligence/app/main.py`.

The root `vercel.json` selects the Services framework, configures the route prefixes, includes the neural model artifact, and bounds the Python function to 1 GiB and 30 seconds.

## First deployment

1. Link the repository as a monorepo with `vercel link --repo`.
2. Confirm the project Framework Preset is **Services**.
3. Set `NWS_USER_AGENT` to an application name and monitored contact address.
4. Create a preview with `vercel deploy`.
5. Verify `/`, `/intelligence/healthz`, and `/intelligence/v1/model`.
6. Promote the verified artifact with `vercel promote <preview-url>`.

Vercel automatically supplies `INTELLIGENCE_URL` and `NEXT_PUBLIC_INTELLIGENCE_URL` for service-to-service and browser routing. Do not hardcode a deployment hostname.

## Runtime behavior

The command center first attempts the full Go operations API. If it is unavailable, the server-rendered live-fusion path loads NASA EONET, NOAA/NWS, and USGS concurrently. The six highest-priority signals are sent to the Python service, which adds cached Open-Meteo and NASA POWER features before neural inference.

Provider calls use bounded timeouts. A failed provider is reported as delayed and does not suppress healthy sources. If all live sources fail, the interface falls back to a prominently labeled embedded scenario.

## Required policy checks

- Replace the example NWS contact address before sustained polling.
- Review Open-Meteo licensing for the intended usage tier.
- Respect NASA POWER's grid-cell request guidance; do not reduce or disable the cache.
- Keep the model disclosure visible and never present its output as an official warning.

## Rollback

Use `vercel rollback` for the most recent production deployment or `vercel rollback <deployment-url>` for a specific artifact. Tagged container releases remain available in GitHub Container Registry for self-hosted rollback.
