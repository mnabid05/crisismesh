package store

import (
	"context"
	"encoding/json"
	"fmt"
	"time"

	"github.com/crisismesh/crisismesh/services/api/internal/domain"
	"github.com/jackc/pgx/v5"
	"github.com/jackc/pgx/v5/pgxpool"
)

type Postgres struct{ pool *pgxpool.Pool }

func OpenPostgres(ctx context.Context, databaseURL string) (*Postgres, error) {
	pool, err := pgxpool.New(ctx, databaseURL)
	if err != nil {
		return nil, fmt.Errorf("parse database config: %w", err)
	}
	if err := pool.Ping(ctx); err != nil {
		pool.Close()
		return nil, fmt.Errorf("ping database: %w", err)
	}
	return &Postgres{pool: pool}, nil
}

func (p *Postgres) ListIncidents(ctx context.Context, filter domain.IncidentFilter) ([]domain.Incident, error) {
	limit := filter.Limit
	if limit <= 0 || limit > 500 {
		limit = 100
	}
	rows, err := p.pool.Query(ctx, `
		SELECT id, external_id, title, kind, severity, status, source, source_url,
		 description, ST_Y(location::geometry), ST_X(location::geometry), started_at,
		 updated_at, risk_score, confidence, affected_population, regions, metadata
		FROM incidents
		WHERE ($1 = '' OR kind = $1) AND ($2 = '' OR severity = $2) AND ($3 = '' OR status = $3)
		ORDER BY risk_score DESC, updated_at DESC LIMIT $4`, filter.Kind, filter.Severity, filter.Status, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]domain.Incident, 0)
	for rows.Next() {
		item, err := scanIncident(rows)
		if err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (p *Postgres) GetIncident(ctx context.Context, id string) (domain.Incident, error) {
	row := p.pool.QueryRow(ctx, `
		SELECT id, external_id, title, kind, severity, status, source, source_url,
		 description, ST_Y(location::geometry), ST_X(location::geometry), started_at,
		 updated_at, risk_score, confidence, affected_population, regions, metadata
		FROM incidents WHERE id = $1`, id)
	item, err := scanIncident(row)
	if err == pgx.ErrNoRows {
		return domain.Incident{}, ErrNotFound
	}
	return item, err
}

type rowScanner interface{ Scan(...any) error }

func scanIncident(row rowScanner) (domain.Incident, error) {
	var item domain.Incident
	var metadata []byte
	err := row.Scan(&item.ID, &item.ExternalID, &item.Title, &item.Kind, &item.Severity,
		&item.Status, &item.Source, &item.SourceURL, &item.Description, &item.Latitude,
		&item.Longitude, &item.StartedAt, &item.UpdatedAt, &item.RiskScore, &item.Confidence,
		&item.AffectedPopulation, &item.Regions, &metadata)
	if len(metadata) > 0 {
		_ = json.Unmarshal(metadata, &item.Metadata)
	}
	return item, err
}

func (p *Postgres) UpsertIncident(ctx context.Context, item domain.Incident) error {
	metadata, _ := json.Marshal(item.Metadata)
	_, err := p.pool.Exec(ctx, `
		INSERT INTO incidents (id, external_id, title, kind, severity, status, source, source_url,
		 description, location, started_at, updated_at, risk_score, confidence, affected_population, regions, metadata)
		VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,ST_SetSRID(ST_MakePoint($11,$10),4326)::geography,$12,$13,$14,$15,$16,$17,$18)
		ON CONFLICT (id) DO UPDATE SET title=EXCLUDED.title, kind=EXCLUDED.kind,
		 severity=EXCLUDED.severity, status=EXCLUDED.status, source=EXCLUDED.source,
		 source_url=EXCLUDED.source_url, description=EXCLUDED.description, location=EXCLUDED.location,
		 updated_at=EXCLUDED.updated_at, risk_score=EXCLUDED.risk_score, confidence=EXCLUDED.confidence,
		 affected_population=EXCLUDED.affected_population, regions=EXCLUDED.regions, metadata=EXCLUDED.metadata`,
		item.ID, item.ExternalID, item.Title, item.Kind, item.Severity, item.Status, item.Source,
		item.SourceURL, item.Description, item.Latitude, item.Longitude, item.StartedAt, item.UpdatedAt,
		item.RiskScore, item.Confidence, item.AffectedPopulation, item.Regions, metadata)
	return err
}

func (p *Postgres) ListResources(ctx context.Context) ([]domain.Resource, error) {
	rows, err := p.pool.Query(ctx, `SELECT id, name, kind, status, quantity, available,
		ST_Y(location::geometry), ST_X(location::geometry), capabilities FROM resources ORDER BY name`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]domain.Resource, 0)
	for rows.Next() {
		var item domain.Resource
		if err := rows.Scan(&item.ID, &item.Name, &item.Kind, &item.Status, &item.Quantity,
			&item.Available, &item.Latitude, &item.Longitude, &item.Capabilities); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (p *Postgres) SaveAllocations(ctx context.Context, items []domain.Allocation) error {
	batch := &pgx.Batch{}
	for _, item := range items {
		batch.Queue(`INSERT INTO allocations (id, incident_id, resource_id, units, eta_seconds,
			distance_km, suitability, rationale, status, created_at) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)`,
			item.ID, item.IncidentID, item.ResourceID, item.Units, item.ETASeconds, item.DistanceKM,
			item.Suitability, item.Rationale, item.Status, item.CreatedAt)
	}
	results := p.pool.SendBatch(ctx, batch)
	defer results.Close()
	for range items {
		if _, err := results.Exec(); err != nil {
			return err
		}
	}
	return nil
}

func (p *Postgres) ListAllocations(ctx context.Context, incidentID string) ([]domain.Allocation, error) {
	rows, err := p.pool.Query(ctx, `SELECT id, incident_id, resource_id, units, eta_seconds,
		distance_km, suitability, rationale, status, created_at FROM allocations
		WHERE ($1 = '' OR incident_id = $1) ORDER BY created_at DESC`, incidentID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	items := make([]domain.Allocation, 0)
	for rows.Next() {
		var item domain.Allocation
		if err := rows.Scan(&item.ID, &item.IncidentID, &item.ResourceID, &item.Units,
			&item.ETASeconds, &item.DistanceKM, &item.Suitability, &item.Rationale,
			&item.Status, &item.CreatedAt); err != nil {
			return nil, err
		}
		items = append(items, item)
	}
	return items, rows.Err()
}

func (p *Postgres) Summary(ctx context.Context) (domain.Summary, error) {
	incidents, err := p.ListIncidents(ctx, domain.IncidentFilter{Limit: 500})
	if err != nil {
		return domain.Summary{}, err
	}
	resources, err := p.ListResources(ctx)
	if err != nil {
		return domain.Summary{}, err
	}
	allocations, err := p.ListAllocations(ctx, "")
	if err != nil {
		return domain.Summary{}, err
	}
	s := domain.Summary{ByKind: map[string]int{}, GeneratedAt: time.Now().UTC()}
	for _, item := range incidents {
		if item.Status != "active" {
			continue
		}
		s.ActiveIncidents++
		s.AffectedPopulation += item.AffectedPopulation
		s.MeanRiskScore += item.RiskScore
		s.ByKind[item.Kind]++
		if item.Severity == "critical" {
			s.CriticalIncidents++
		}
	}
	if s.ActiveIncidents > 0 {
		s.MeanRiskScore /= float64(s.ActiveIncidents)
	}
	for _, item := range resources {
		s.ResourcesAvailable += item.Available
	}
	for _, item := range allocations {
		if item.Status != "completed" {
			s.OpenDeployments++
		}
	}
	s.Sources = sourceHealth(incidents, s.GeneratedAt)
	return s, nil
}

func (p *Postgres) Close() { p.pool.Close() }
