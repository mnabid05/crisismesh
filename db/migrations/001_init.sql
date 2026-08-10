CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS incidents (
  id text PRIMARY KEY,
  external_id text NOT NULL DEFAULT '',
  title text NOT NULL,
  kind text NOT NULL,
  severity text NOT NULL CHECK (severity IN ('low','moderate','high','critical')),
  status text NOT NULL CHECK (status IN ('active','monitoring','contained','closed')),
  source text NOT NULL,
  source_url text NOT NULL DEFAULT '',
  description text NOT NULL DEFAULT '',
  location geography(Point,4326) NOT NULL,
  started_at timestamptz NOT NULL,
  updated_at timestamptz NOT NULL,
  risk_score numeric(5,2) NOT NULL DEFAULT 0 CHECK (risk_score BETWEEN 0 AND 100),
  confidence numeric(4,3) NOT NULL DEFAULT 0 CHECK (confidence BETWEEN 0 AND 1),
  affected_population integer NOT NULL DEFAULT 0 CHECK (affected_population >= 0),
  regions text[] NOT NULL DEFAULT '{}',
  metadata jsonb NOT NULL DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS incidents_location_gix ON incidents USING gist(location);
CREATE INDEX IF NOT EXISTS incidents_priority_idx ON incidents(status, severity, risk_score DESC);
CREATE UNIQUE INDEX IF NOT EXISTS incidents_source_external_idx ON incidents(source, external_id) WHERE external_id <> '';

CREATE TABLE IF NOT EXISTS resources (
  id text PRIMARY KEY,
  name text NOT NULL,
  kind text NOT NULL,
  status text NOT NULL CHECK (status IN ('ready','partial','deployed','offline')),
  quantity integer NOT NULL CHECK (quantity >= 0),
  available integer NOT NULL CHECK (available BETWEEN 0 AND quantity),
  location geography(Point,4326) NOT NULL,
  capabilities text[] NOT NULL DEFAULT '{}',
  demand_category text NOT NULL DEFAULT '',
  unit text NOT NULL DEFAULT 'units',
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS resources_location_gix ON resources USING gist(location);

CREATE TABLE IF NOT EXISTS allocations (
  id text PRIMARY KEY,
  incident_id text NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
  resource_id text NOT NULL REFERENCES resources(id),
  units integer NOT NULL CHECK (units > 0),
  eta_seconds integer NOT NULL CHECK (eta_seconds >= 0),
  distance_km numeric(10,2) NOT NULL CHECK (distance_km >= 0),
  suitability numeric(5,4) NOT NULL CHECK (suitability BETWEEN 0 AND 1),
  rationale text NOT NULL,
  status text NOT NULL CHECK (status IN ('proposed','approved','dispatched','completed','cancelled')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS allocations_incident_idx ON allocations(incident_id, created_at DESC);

INSERT INTO resources (id,name,kind,status,quantity,available,location,capabilities,demand_category,unit) VALUES
('res-usar-01','Urban Search & Rescue 01','rescue','ready',42,32,ST_SetSRID(ST_MakePoint(-84.39,33.75),4326)::geography,ARRAY['medical','swift-water','structural'],'rescue_teams','teams'),
('res-med-07','Mobile Medical Unit 07','medical','ready',18,12,ST_SetSRID(ST_MakePoint(-97.74,30.27),4326)::geography,ARRAY['triage','critical-care','medical'],'medical_teams','teams'),
('res-air-03','Regional Evacuation Fleet','transport','partial',640,420,ST_SetSRID(ST_MakePoint(-80.0,32.9),4326)::geography,ARRAY['evacuation','accessible-transport','cargo'],'transport_seats','seats'),
('res-shelter-12','Shelter Support 12','shelter','ready',600,480,ST_SetSRID(ST_MakePoint(-81.38,28.54),4326)::geography,ARRAY['cots','meals','accessibility','shelter'],'shelter_beds','beds'),
('res-volunteer-04','Community Volunteer Network','volunteer','ready',230,186,ST_SetSRID(ST_MakePoint(-95.37,29.76),4326)::geography,ARRAY['wellness-checks','distribution','translation'],'','people'),
('res-supply-09','Regional Meal Cache 09','supplies','ready',150000,112000,ST_SetSRID(ST_MakePoint(-80.84,35.22),4326)::geography,ARRAY['meals','distribution'],'meals','meals'),
('res-water-05','Potable Water Cache 05','supplies','ready',180000,126000,ST_SetSRID(ST_MakePoint(-92.29,34.75),4326)::geography,ARRAY['water','distribution'],'water_liters','liters')
ON CONFLICT (id) DO NOTHING;

INSERT INTO incidents (id,title,kind,severity,status,source,description,location,started_at,updated_at,risk_score,confidence,affected_population,regions) VALUES
('cm-atlantic-07','Atlantic tropical cyclone watch','storm','critical','active','NASA EONET','Rapidly organizing tropical system with coastal flood potential.',ST_SetSRID(ST_MakePoint(-74.2,26.7),4326)::geography,now()-interval '9 hours',now()-interval '3 minutes',91,.88,184000,ARRAY['Broward County','Miami-Dade']),
('cm-cascadia-14','Cascadia wildfire complex','wildfire','high','active','NASA EONET','Multiple active fire perimeters with smoke affecting two counties.',ST_SetSRID(ST_MakePoint(-121.6,44.4),4326)::geography,now()-interval '31 hours',now()-interval '7 minutes',78,.93,42600,ARRAY['Deschutes County','Jefferson County']),
('cm-gulf-22','Flash flood emergency','flood','high','active','NOAA / NWS','Training thunderstorms producing life-threatening flash flooding.',ST_SetSRID(ST_MakePoint(-95.4,29.8),4326)::geography,now()-interval '4 hours',now()-interval '1 minute',84,.96,73000,ARRAY['Harris County']),
('cm-sierra-03','M4.8 regional earthquake','earthquake','moderate','monitoring','USGS','Shallow earthquake with light-to-moderate reported shaking.',ST_SetSRID(ST_MakePoint(-118.8,37.5),4326)::geography,now()-interval '2 hours',now()-interval '11 minutes',53,.99,12800,ARRAY['Mono County'])
ON CONFLICT (id) DO NOTHING;
