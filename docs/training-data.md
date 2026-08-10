# Training data and six-hour demand target

## Intended prediction

CrisisMesh v3 estimates normalized resource-demand pressure for an **already observed incident**
during one six-hour immediate-response window. It covers shelter beds, medical teams, rescue teams,
potable water, prepared meals, and evacuation seats. It does not predict whether a disaster will
occur, verify a field request, or authorize dispatch.

The model output is one input to a transparent planning pipeline:

1. A 21-feature neural network estimates pressure for six resource categories.
2. Disclosed category factors convert pressure and affected population into quantity ranges.
3. Unit-tagged resource inventory is subtracted to expose estimated shortfalls.
4. Shortfall ratio, capability fit, availability, and Haversine distance rank staging proposals.
5. A human operator must confirm every proposal with incident command and field assessments.

## Historical evidence sources

### NOAA Storm Events

- Source: <https://www.ncei.noaa.gov/stormevents/>
- Bulk files: <https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/>
- Format guide: <https://www.ncei.noaa.gov/pub/data/swdi/stormevents/csvfiles/Storm-Data-Bulk-csv-Format.pdf>

The records document significant U.S. weather events and include event type, timing, magnitude,
injuries, deaths, crop damage, property damage, and coordinates. Collection practices and periods
of record have changed over time, so the manifest records the accessed files and uses chronological
splits.

### USGS earthquake catalog

- Source and API: <https://earthquake.usgs.gov/fdsnws/event/1/>
- PAGER background: <https://earthquake.usgs.gov/data/pager/background.php>
- Real-time feeds: <https://earthquake.usgs.gov/earthquakes/feed/v1.0/geojson.php>

The FDSN event service provides magnitude, depth, significance, tsunami flags, alert levels, felt
reports, and instrumental intensity where available. Missing fields are treated as missing
evidence—not evidence of no impact.

## Resource taxonomy

The six categories align with immediate mass-care and emergency-assistance functions described in
FEMA Emergency Support Function #6. FEMA guidance supplies the taxonomy, not supervised usage
labels. The repository's factors are explicit engineering assumptions and can be replaced by a
jurisdiction's approved planning standards.

- FEMA ESF #6: <https://www.fema.gov/sites/default/files/2020-07/fema_ESF_6_Mass-Care.pdf>
- FEMA National Shelter System: <https://gis.fema.gov/arcgis/rest/services/NSS/FEMA_NSS/FeatureServer>

## Proxy-label policy

NOAA and USGS do not provide verified six-hour counts for beds, teams, liters, meals, or seats.
CrisisMesh therefore derives **planning-proxy pressure labels** from recorded impact, normalized
severity, and a versioned hazard-to-resource profile. These targets are reproducible and useful for
testing an end-to-end decision-support workflow, but they are not ground truth for resource use.

The v3 artifact reports error against those proxies. Its held-out macro MAE of 0.0243 means the
average absolute error on a normalized 0–1 proxy target was 0.0243; it does not establish real-world
dispatch accuracy. The dataset is split chronologically into 12,950 training, 2,775 validation,
and 2,775 held-out test records.

## Live environmental context

- NASA POWER daily meteorology: <https://power.larc.nasa.gov/docs/services/api/temporal/daily/point/>
- Open-Meteo forecast API: <https://open-meteo.com/en/docs>
- NASA EONET event API: <https://eonet.gsfc.nasa.gov/docs/v3>
- NOAA/NWS alerts API: <https://www.weather.gov/documentation/services-web-api>

NASA POWER and Open-Meteo provide runtime context through a bounded environmental adjustment and
uncertainty estimate. They are not represented as fully aligned historical labels. This separation
avoids presenting unrelated present-day API responses as historical training observations.

## Known limitations

- Proxy pressure is not observed demand, utilization, fulfillment, or dispatch data.
- NOAA Storm Events is U.S.-focused and contains reporting and collection bias.
- USGS impact fields are incomplete for many earthquakes; global reporting varies.
- Rare catastrophic events remain underrepresented.
- Live affected-population estimates are coarse until a population-grid integration is added.
- Local access constraints, vulnerable populations, road status, and mutual-aid agreements can
  dominate actual needs.
- The model must be recalibrated and validated with an emergency-management partner before any
  operational use.
