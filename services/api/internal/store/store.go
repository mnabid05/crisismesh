package store

import (
	"context"
	"errors"
	"sort"
	"strings"
	"sync"
	"time"

	"github.com/crisismesh/crisismesh/services/api/internal/domain"
)

var ErrNotFound = errors.New("not found")

type Store interface {
	ListIncidents(context.Context, domain.IncidentFilter) ([]domain.Incident, error)
	GetIncident(context.Context, string) (domain.Incident, error)
	UpsertIncident(context.Context, domain.Incident) error
	ListResources(context.Context) ([]domain.Resource, error)
	SaveAllocations(context.Context, []domain.Allocation) error
	ListAllocations(context.Context, string) ([]domain.Allocation, error)
	Summary(context.Context) (domain.Summary, error)
	Close()
}

type Memory struct {
	mu          sync.RWMutex
	incidents   map[string]domain.Incident
	resources   map[string]domain.Resource
	allocations []domain.Allocation
}

func NewMemory() *Memory {
	now := time.Now().UTC()
	incidents := seedIncidents(now)
	resources := seedResources()
	m := &Memory{incidents: map[string]domain.Incident{}, resources: map[string]domain.Resource{}}
	for _, incident := range incidents {
		m.incidents[incident.ID] = incident
	}
	for _, resource := range resources {
		m.resources[resource.ID] = resource
	}
	return m
}

func (m *Memory) ListIncidents(_ context.Context, filter domain.IncidentFilter) ([]domain.Incident, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]domain.Incident, 0, len(m.incidents))
	for _, item := range m.incidents {
		if filter.Kind != "" && !strings.EqualFold(filter.Kind, item.Kind) {
			continue
		}
		if filter.Severity != "" && !strings.EqualFold(filter.Severity, item.Severity) {
			continue
		}
		if filter.Status != "" && !strings.EqualFold(filter.Status, item.Status) {
			continue
		}
		items = append(items, item)
	}
	sort.Slice(items, func(i, j int) bool {
		if items[i].RiskScore == items[j].RiskScore {
			return items[i].UpdatedAt.After(items[j].UpdatedAt)
		}
		return items[i].RiskScore > items[j].RiskScore
	})
	if filter.Limit > 0 && len(items) > filter.Limit {
		items = items[:filter.Limit]
	}
	return items, nil
}

func (m *Memory) GetIncident(_ context.Context, id string) (domain.Incident, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	item, ok := m.incidents[id]
	if !ok {
		return domain.Incident{}, ErrNotFound
	}
	return item, nil
}

func (m *Memory) UpsertIncident(_ context.Context, item domain.Incident) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.incidents[item.ID] = item
	return nil
}

func (m *Memory) ListResources(_ context.Context) ([]domain.Resource, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]domain.Resource, 0, len(m.resources))
	for _, item := range m.resources {
		items = append(items, item)
	}
	sort.Slice(items, func(i, j int) bool { return items[i].Name < items[j].Name })
	return items, nil
}

func (m *Memory) SaveAllocations(_ context.Context, items []domain.Allocation) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.allocations = append(m.allocations, items...)
	return nil
}

func (m *Memory) ListAllocations(_ context.Context, incidentID string) ([]domain.Allocation, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	items := make([]domain.Allocation, 0)
	for _, item := range m.allocations {
		if incidentID == "" || item.IncidentID == incidentID {
			items = append(items, item)
		}
	}
	return items, nil
}

func (m *Memory) Summary(ctx context.Context) (domain.Summary, error) {
	incidents, _ := m.ListIncidents(ctx, domain.IncidentFilter{})
	resources, _ := m.ListResources(ctx)
	allocations, _ := m.ListAllocations(ctx, "")
	summary := domain.Summary{ByKind: map[string]int{}, GeneratedAt: time.Now().UTC()}
	for _, item := range incidents {
		if item.Status != "active" {
			continue
		}
		summary.ActiveIncidents++
		if item.Severity == "critical" {
			summary.CriticalIncidents++
		}
		summary.AffectedPopulation += item.AffectedPopulation
		summary.MeanRiskScore += item.RiskScore
		summary.ByKind[item.Kind]++
	}
	if summary.ActiveIncidents > 0 {
		summary.MeanRiskScore /= float64(summary.ActiveIncidents)
	}
	for _, item := range resources {
		summary.ResourcesAvailable += item.Available
	}
	for _, item := range allocations {
		if item.Status != "completed" {
			summary.OpenDeployments++
		}
	}
	summary.Sources = sourceHealth(incidents, summary.GeneratedAt)
	return summary, nil
}

func sourceHealth(incidents []domain.Incident, now time.Time) []domain.SourceHealth {
	providers := []string{"NASA EONET", "NOAA / NWS", "USGS"}
	latest := make(map[string]time.Time, len(providers))
	for _, item := range incidents {
		if item.UpdatedAt.After(latest[item.Source]) {
			latest[item.Source] = item.UpdatedAt
		}
	}
	result := make([]domain.SourceHealth, 0, len(providers))
	for _, provider := range providers {
		lastSync := latest[provider]
		lag := int(now.Sub(lastSync).Seconds())
		status := "operational"
		if lastSync.IsZero() || lag > 3600 {
			status = "stale"
		} else if lag > 600 {
			status = "delayed"
		}
		result = append(result, domain.SourceHealth{Name: provider, Status: status, LastSync: lastSync, LagSeconds: max(0, lag)})
	}
	return result
}

func (m *Memory) Close() {}

func seedIncidents(now time.Time) []domain.Incident {
	return []domain.Incident{
		{ID: "cm-atlantic-07", Title: "Atlantic tropical cyclone watch", Kind: "storm", Severity: "critical", Status: "active", Source: "NASA EONET", Description: "Rapidly organizing tropical system with coastal flood potential.", Latitude: 26.7, Longitude: -74.2, StartedAt: now.Add(-9 * time.Hour), UpdatedAt: now.Add(-3 * time.Minute), RiskScore: 91, Confidence: .88, AffectedPopulation: 184000, Regions: []string{"Broward County", "Miami-Dade"}},
		{ID: "cm-cascadia-14", Title: "Cascadia wildfire complex", Kind: "wildfire", Severity: "high", Status: "active", Source: "NASA EONET", Description: "Multiple active fire perimeters with smoke affecting two counties.", Latitude: 44.4, Longitude: -121.6, StartedAt: now.Add(-31 * time.Hour), UpdatedAt: now.Add(-7 * time.Minute), RiskScore: 78, Confidence: .93, AffectedPopulation: 42600, Regions: []string{"Deschutes County", "Jefferson County"}},
		{ID: "cm-gulf-22", Title: "Flash flood emergency", Kind: "flood", Severity: "high", Status: "active", Source: "NOAA / NWS", Description: "Training thunderstorms producing life-threatening flash flooding.", Latitude: 29.8, Longitude: -95.4, StartedAt: now.Add(-4 * time.Hour), UpdatedAt: now.Add(-1 * time.Minute), RiskScore: 84, Confidence: .96, AffectedPopulation: 73000, Regions: []string{"Harris County"}},
		{ID: "cm-sierra-03", Title: "M4.8 regional earthquake", Kind: "earthquake", Severity: "moderate", Status: "monitoring", Source: "USGS", Description: "Shallow earthquake with light-to-moderate reported shaking.", Latitude: 37.5, Longitude: -118.8, StartedAt: now.Add(-2 * time.Hour), UpdatedAt: now.Add(-11 * time.Minute), RiskScore: 53, Confidence: .99, AffectedPopulation: 12800, Regions: []string{"Mono County"}},
		{ID: "cm-plains-19", Title: "Severe convective outbreak", Kind: "storm", Severity: "moderate", Status: "active", Source: "NOAA / NWS", Description: "Damaging wind and isolated tornado risk across the central plains.", Latitude: 38.7, Longitude: -97.2, StartedAt: now.Add(-6 * time.Hour), UpdatedAt: now.Add(-8 * time.Minute), RiskScore: 66, Confidence: .81, AffectedPopulation: 97500, Regions: []string{"Saline County", "McPherson County"}},
	}
}

func seedResources() []domain.Resource {
	return []domain.Resource{
		{ID: "res-usar-01", Name: "Urban Search & Rescue 01", Kind: "rescue", Status: "ready", Quantity: 42, Available: 32, Latitude: 33.75, Longitude: -84.39, Capabilities: []string{"medical", "swift-water", "structural"}, DemandCategory: "rescue_teams", Unit: "teams"},
		{ID: "res-med-07", Name: "Mobile Medical Unit 07", Kind: "medical", Status: "ready", Quantity: 18, Available: 12, Latitude: 30.27, Longitude: -97.74, Capabilities: []string{"triage", "critical-care"}, DemandCategory: "medical_teams", Unit: "teams"},
		{ID: "res-air-03", Name: "Regional Evacuation Fleet", Kind: "transport", Status: "partial", Quantity: 640, Available: 420, Latitude: 32.9, Longitude: -80.0, Capabilities: []string{"evacuation", "accessible-transport", "cargo"}, DemandCategory: "transport_seats", Unit: "seats"},
		{ID: "res-shelter-12", Name: "Shelter Support 12", Kind: "shelter", Status: "ready", Quantity: 600, Available: 480, Latitude: 28.54, Longitude: -81.38, Capabilities: []string{"cots", "meals", "accessibility"}, DemandCategory: "shelter_beds", Unit: "beds"},
		{ID: "res-volunteer-04", Name: "Community Volunteer Network", Kind: "volunteer", Status: "ready", Quantity: 230, Available: 186, Latitude: 29.76, Longitude: -95.37, Capabilities: []string{"wellness-checks", "distribution", "translation"}, Unit: "people"},
		{ID: "res-supply-09", Name: "Regional Meal Cache 09", Kind: "supplies", Status: "ready", Quantity: 150000, Available: 112000, Latitude: 35.22, Longitude: -80.84, Capabilities: []string{"meals", "distribution"}, DemandCategory: "meals", Unit: "meals"},
		{ID: "res-water-05", Name: "Potable Water Cache 05", Kind: "supplies", Status: "ready", Quantity: 180000, Available: 126000, Latitude: 34.75, Longitude: -92.29, Capabilities: []string{"water", "distribution"}, DemandCategory: "water_liters", Unit: "liters"},
	}
}
