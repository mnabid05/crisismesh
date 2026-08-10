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

- [x] 13. Add a deterministic training-data manifest format.
- [x] 14. Resolve versioned NOAA bulk files from the official index.
- [x] 15. Stream and parse compressed NOAA records without staging large datasets in git.
- [x] 16. Parse NOAA damage suffixes into normalized dollar estimates.
- [x] 17. Map NOAA event types to the CrisisMesh hazard taxonomy.
- [x] 18. Derive transparent NOAA impact labels from injuries, deaths, and damage.
- [x] 19. Query the USGS FDSN catalog in bounded yearly windows.
- [x] 20. Parse USGS magnitude, depth, significance, alert, felt, and tsunami fields.
- [x] 21. Derive transparent USGS impact labels.
- [x] 22. Deduplicate provider records by stable event identifier.
- [x] 23. Reject malformed coordinates and impossible timestamps.
- [x] 24. Build chronological train, validation, and test splits.
- [x] 25. Prevent future records from leaking into earlier splits.
- [x] 26. Balance hazard families without erasing real class prevalence.
- [x] 27. Add feature normalization metadata to the model artifact.
- [x] 28. Track provider record counts and collection timestamps.
- [x] 29. Track source URLs and SHA-256 digests in the dataset manifest.
- [x] 30. Keep raw training archives out of source control.

## Prediction model

- [x] 31. Upgrade the network from one output to three forecast horizons.
- [x] 32. Add a second hidden layer for non-linear hazard interactions.
- [x] 33. Use deterministic initialization and shuffling.
- [x] 34. Train with a temporally ordered validation split.
- [x] 35. Add early stopping on validation Brier score.
- [x] 36. Calibrate each horizon against validation outcomes.
- [x] 37. Enforce non-decreasing cumulative horizon probabilities.
- [x] 38. Add hazard-aware live environmental adjustments.
- [x] 39. Cap environmental adjustments to prevent provider spikes from dominating.
- [x] 40. Estimate uncertainty from provider coverage and feature distance.
- [x] 41. Return lower and upper probability bounds.
- [x] 42. Return named top drivers per horizon.
- [x] 43. Return trajectory direction and confidence labels.
- [x] 44. Publish held-out Brier score and discrimination metrics.
- [x] 45. Keep the v1 scoring endpoint backward compatible.
- [x] 46. Publish an updated model card and intended-use statement.

## Provider and API reliability

- [x] 47. Introduce a shared provider error contract.
- [x] 48. Introduce bounded retries for transient upstream failures.
- [x] 49. Respect provider-specific request timeouts.
- [x] 50. Add TTL caching keyed by request and rounded coordinate cell.
- [x] 51. Add request provenance and observation timestamps.
- [x] 52. Consolidate TypeScript provider fetch behavior.
- [x] 53. Preserve partial results when one provider fails.
- [x] 54. Distinguish healthy, delayed, stale, and unavailable sources.
- [x] 55. Expose provider coverage in every prediction.
- [x] 56. Add a v2 multi-horizon prediction endpoint.
- [x] 57. Add a prediction-model metadata endpoint.
- [x] 58. Add a provider-health endpoint.

## Product and visual system

- [x] 59. Replace the dark command shell with a white and light-blue application frame.
- [x] 60. Add clear Overview, Predictions, Incidents, Sources, and Resources navigation.
- [x] 61. Lead with a multi-horizon prediction summary.
- [x] 62. Add a readable trajectory visualization with uncertainty ranges.
- [x] 63. Separate current incident facts from model-generated predictions.
- [x] 64. Add plain-language model confidence and freshness labels.
- [x] 65. Simplify the incident list and filters.
- [x] 66. Restyle the map for the light visual system.
- [x] 67. Add a dedicated source-health and provenance view.
- [x] 68. Add a dedicated natural-disaster resource library.
- [x] 69. Link every resource to an official or established response organization.
- [x] 70. Add prominent emergency and official-guidance disclaimers.
- [x] 71. Verify keyboard navigation, focus states, contrast, and reduced motion.

## Delivery

- [x] 72. Expand Python model, dataset, endpoint, and provider tests.
- [x] 73. Run TypeScript, React, Go, workflow, container, and Helm quality gates.
- [x] 74. Verify desktop and mobile prediction flows in a real browser.
- [ ] 75. Publish, pass GitHub CI, deploy, and smoke-test the public production release.
