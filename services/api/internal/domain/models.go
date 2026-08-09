package domain

import "time"

type Incident struct {
	ID                 string         `json:"id"`
	ExternalID         string         `json:"externalId,omitempty"`
	Title              string         `json:"title"`
	Kind               string         `json:"kind"`
	Severity           string         `json:"severity"`
	Status             string         `json:"status"`
	Source             string         `json:"source"`
	SourceURL          string         `json:"sourceUrl,omitempty"`
	Description        string         `json:"description"`
	Latitude           float64        `json:"latitude"`
	Longitude          float64        `json:"longitude"`
	StartedAt          time.Time      `json:"startedAt"`
	UpdatedAt          time.Time      `json:"updatedAt"`
	RiskScore          float64        `json:"riskScore"`
	Confidence         float64        `json:"confidence"`
	AffectedPopulation int            `json:"affectedPopulation"`
	Regions            []string       `json:"regions"`
	Metadata           map[string]any `json:"metadata,omitempty"`
}

type Resource struct {
	ID           string   `json:"id"`
	Name         string   `json:"name"`
	Kind         string   `json:"kind"`
	Status       string   `json:"status"`
	Quantity     int      `json:"quantity"`
	Available    int      `json:"available"`
	Latitude     float64  `json:"latitude"`
	Longitude    float64  `json:"longitude"`
	Capabilities []string `json:"capabilities"`
}

type AllocationRequest struct {
	IncidentID  string   `json:"incidentId"`
	ResourceIDs []string `json:"resourceIds,omitempty"`
}

type Allocation struct {
	ID          string    `json:"id"`
	IncidentID  string    `json:"incidentId"`
	ResourceID  string    `json:"resourceId"`
	Units       int       `json:"units"`
	ETASeconds  int       `json:"etaSeconds"`
	DistanceKM  float64   `json:"distanceKm"`
	Suitability float64   `json:"suitability"`
	Rationale   string    `json:"rationale"`
	Status      string    `json:"status"`
	CreatedAt   time.Time `json:"createdAt"`
}

type Summary struct {
	ActiveIncidents    int            `json:"activeIncidents"`
	CriticalIncidents  int            `json:"criticalIncidents"`
	AffectedPopulation int            `json:"affectedPopulation"`
	ResourcesAvailable int            `json:"resourcesAvailable"`
	OpenDeployments    int            `json:"openDeployments"`
	MeanRiskScore      float64        `json:"meanRiskScore"`
	ByKind             map[string]int `json:"byKind"`
	Sources            []SourceHealth `json:"sources"`
	GeneratedAt        time.Time      `json:"generatedAt"`
}

type SourceHealth struct {
	Name       string    `json:"name"`
	Status     string    `json:"status"`
	LastSync   time.Time `json:"lastSync"`
	LagSeconds int       `json:"lagSeconds"`
}

type IncidentFilter struct {
	Kind     string
	Severity string
	Status   string
	Limit    int
}
