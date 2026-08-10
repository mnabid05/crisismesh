# Contributing

## Development rules

- Never present scenario records as live emergency information.
- Keep provider attribution and source links intact.
- Add a fixture-based test for every new source adapter.
- Keep scoring explainable; opaque model output cannot authorize dispatch.
- Use Conventional Commits with a service scope, for example `feat(ingestor): add FIRMS adapter`.
- Keep migrations backwards-compatible with the previous application release.

## Pull-request checklist

- [ ] Unit/contract tests cover behavior changes.
- [ ] Public API changes update `docs/openapi.yaml`.
- [ ] New configuration is documented in `.env.example` and the relevant deployment guide.
- [ ] Logs and screenshots contain no credentials or personal data.
- [ ] UI changes work at 375 px and 1440 px widths.
- [ ] Operational and safety failure modes are described.
