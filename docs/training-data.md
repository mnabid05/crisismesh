# Training data and prediction target

## Intended prediction

CrisisMesh v2 estimates the likelihood that an **already observed incident** will require a higher
operational response within 6, 24, or 72 hours. It does not predict whether an earthquake, storm,
flood, or wildfire will occur. The horizons support prioritization and staffing decisions; official
warnings and evacuation instructions always take precedence.

## Historical outcome sources

### NOAA Storm Events

- Source: <https://www.ncei.noaa.gov/stormevents/>
- Bulk files: <https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/>
- Format guide: <https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/Storm-Data-Bulk-csv-Format.pdf>

The records document significant U.S. weather events and include event type, timing, magnitude,
injuries, deaths, crop damage, property damage, and coordinates. CrisisMesh derives impact labels
from those recorded outcomes. Collection practices and periods of record have changed over time,
so the training manifest records the accessed files and the model uses chronological splits.

### USGS earthquake catalog

- Source and API: <https://earthquake.usgs.gov/fdsnws/event/1/>
- Real-time feeds: <https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php>

The FDSN event service provides magnitude, depth, significance, tsunami flags, alert levels, felt
reports, and instrumental intensity where available. CrisisMesh queries bounded time windows and
derives impact labels using documented catalog fields. Missing felt or alert data is treated as
missing evidence, not evidence of no impact.

## Live environmental context

- NASA POWER daily meteorology: <https://power.larc.nasa.gov/docs/services/api/temporal/daily/point/>
- Open-Meteo forecast API: <https://open-meteo.com/en/docs>
- NASA EONET event API: <https://eonet.gsfc.nasa.gov/docs/v3>
- NOAA/NWS alerts API: <https://www.weather.gov/documentation/services-web-api>

NASA POWER and Open-Meteo provide runtime context. They influence a bounded environmental
adjustment and uncertainty estimate; they are not represented as fully aligned historical labels in
the first v2 artifact. This separation avoids pretending that unrelated present-day API responses
are historical training observations.

## Label policy

Outcome labels are reproducible rules based on reported harm and damage. They are proxy labels for
operational escalation, not ground truth for an emergency manager's decision. The collector keeps
the source event identifier, event time, source file or query, collection time, and content digest.
Raw archives and personally identifying narratives are not committed.

## Known limitations

- NOAA Storm Events is U.S.-focused and contains reporting and collection bias.
- USGS impact fields are incomplete for many earthquakes and global reporting varies.
- Rare catastrophic events remain underrepresented.
- Exposure estimates in the live UI are approximate until a population-grid integration is added.
- Probabilities should be recalibrated before use in a new geography or operational organization.

