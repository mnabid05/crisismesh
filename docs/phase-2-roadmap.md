# Phase 2: predictive response roadmap

This 75-step execution ledger turns CrisisMesh from a live incident dashboard into a
prediction-centered decision-support product. A checked item means the change is implemented or
the decision is documented in the repository; it does not imply that experimental forecasts have
official authority.

## Scope and evidence

- [x] 1. Preserve the Phase 1 production deployment as a rollback point.
- [x] 2. Create an isolated Phase 2 branch from the merged default branch.
- [x] 3. Audit the v1 single-output neural model and its synthetic training limits.
- [x] 4. Define a minimal white and light-blue visual direction.
- [x] 5. Frame predictions as operational escalation likelihood, not disaster occurrence forecasts.
- [x] 6. Select 6-hour, 24-hour, and 72-hour decision horizons.
- [x] 7. Select NOAA Storm Events as the weather-impact outcome source.
- [x] 8. Select the USGS catalog as the earthquake outcome source.
- [x] 9. Retain NASA POWER as a climate-context feature provider.
- [x] 10. Retain Open-Meteo as a best-match forecast feature provider.
- [x] 11. Select official FEMA, NWS, USGS, and Red Cross preparedness resources.
- [x] 12. Record provenance, data bias, target construction, and safety boundaries.

## Training data and feature engineering

- [ ] 13. Add a deterministic training-data manifest format.
- [ ] 14. Resolve versioned NOAA bulk files from the official index.
- [ ] 15. Stream and parse compressed NOAA records without staging large datasets in git.
- [ ] 16. Parse NOAA damage suffixes into normalized dollar estimates.
- [ ] 17. Map NOAA event types to the CrisisMesh hazard taxonomy.
- [ ] 18. Derive transparent NOAA impact labels from injuries, deaths, and damage.
- [ ] 19. Query the USGS FDSN catalog in bounded yearly windows.
- [ ] 20. Parse USGS magnitude, depth, significance, alert, felt, and tsunami fields.
- [ ] 21. Derive transparent USGS impact labels.
- [ ] 22. Deduplicate provider records by stable event identifier.
- [ ] 23. Reject malformed coordinates and impossible timestamps.
- [ ] 24. Build chronological train, validation, and test splits.
- [ ] 25. Prevent future records from leaking into earlier splits.
- [ ] 26. Balance hazard families without erasing real class prevalence.
- [ ] 27. Add feature normalization metadata to the model artifact.
- [ ] 28. Track provider record counts and collection timestamps.
- [ ] 29. Track source URLs and SHA-256 digests in the dataset manifest.
- [ ] 30. Keep raw training archives out of source control.

## Prediction model

- [ ] 31. Upgrade the network from one output to three forecast horizons.
- [ ] 32. Add a second hidden layer for non-linear hazard interactions.
- [ ] 33. Use deterministic initialization and shuffling.
- [ ] 34. Train with a temporally ordered validation split.
- [ ] 35. Add early stopping on validation Brier score.
- [ ] 36. Calibrate each horizon against validation outcomes.
- [ ] 37. Enforce non-decreasing cumulative horizon probabilities.
- [ ] 38. Add hazard-aware live environmental adjustments.
- [ ] 39. Cap environmental adjustments to prevent provider spikes from dominating.
- [ ] 40. Estimate uncertainty from provider coverage and feature distance.
- [ ] 41. Return lower and upper probability bounds.
- [ ] 42. Return named top drivers per horizon.
- [ ] 43. Return trajectory direction and confidence labels.
- [ ] 44. Publish held-out Brier score and discrimination metrics.
- [ ] 45. Keep the v1 scoring endpoint backward compatible.
- [ ] 46. Publish an updated model card and intended-use statement.

## Provider and API reliability

- [ ] 47. Introduce a shared provider error contract.
- [ ] 48. Introduce bounded retries for transient upstream failures.
- [ ] 49. Respect provider-specific request timeouts.
- [ ] 50. Add TTL caching keyed by request and rounded coordinate cell.
- [ ] 51. Add request provenance and observation timestamps.
- [ ] 52. Consolidate TypeScript provider fetch behavior.
- [ ] 53. Preserve partial results when one provider fails.
- [ ] 54. Distinguish healthy, delayed, stale, and unavailable sources.
- [ ] 55. Expose provider coverage in every prediction.
- [ ] 56. Add a v2 multi-horizon prediction endpoint.
- [ ] 57. Add a prediction-model metadata endpoint.
- [ ] 58. Add a provider-health endpoint.

## Product and visual system

- [ ] 59. Replace the dark command shell with a white and light-blue application frame.
- [ ] 60. Add clear Overview, Predictions, Incidents, Sources, and Resources navigation.
- [ ] 61. Lead with a multi-horizon prediction summary.
- [ ] 62. Add a readable trajectory visualization with uncertainty ranges.
- [ ] 63. Separate current incident facts from model-generated predictions.
- [ ] 64. Add plain-language model confidence and freshness labels.
- [ ] 65. Simplify the incident list and filters.
- [ ] 66. Restyle the map for the light visual system.
- [ ] 67. Add a dedicated source-health and provenance view.
- [ ] 68. Add a dedicated natural-disaster resource library.
- [ ] 69. Link every resource to an official or established response organization.
- [ ] 70. Add prominent emergency and official-guidance disclaimers.
- [ ] 71. Verify keyboard navigation, focus states, contrast, and reduced motion.

## Delivery

- [ ] 72. Expand Python model, dataset, endpoint, and provider tests.
- [ ] 73. Run TypeScript, React, Go, workflow, container, and Helm quality gates.
- [ ] 74. Verify desktop and mobile prediction flows in a real browser.
- [ ] 75. Publish, pass GitHub CI, deploy, and smoke-test the public production release.

