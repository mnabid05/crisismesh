package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"strconv"
	"strings"
	"sync"
	"syscall"
	"time"
)

const (
	eonetURL = "https://eonet.gsfc.nasa.gov/api/v3/events?status=open&days=30&limit=100"
	nwsURL   = "https://api.weather.gov/alerts/active?status=actual&message_type=alert"
	usgsURL  = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
)

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

type Ingestor struct {
	client                    *http.Client
	apiURL, apiKey, userAgent string
	logger                    *slog.Logger
}

func main() {
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	interval := durationEnv("INGEST_INTERVAL", 5*time.Minute)
	ingestor := &Ingestor{client: &http.Client{Timeout: 20 * time.Second}, apiURL: env("API_URL", "http://localhost:8080"), apiKey: os.Getenv("CRISISMESH_API_KEY"), userAgent: env("NWS_USER_AGENT", "CrisisMesh/0.1 portfolio@example.com"), logger: logger}
	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()
	ingestor.sync(ctx)
	if strings.EqualFold(os.Getenv("RUN_ONCE"), "true") {
		return
	}
	ticker := time.NewTicker(interval)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			ingestor.sync(ctx)
		}
	}
}

func (i *Ingestor) sync(ctx context.Context) {
	type result struct {
		source string
		items  []Incident
		err    error
	}
	results := make(chan result, 3)
	var wg sync.WaitGroup
	loaders := []struct {
		name string
		fn   func(context.Context) ([]Incident, error)
	}{{"NASA EONET", i.fetchEONET}, {"NOAA / NWS", i.fetchNWS}, {"USGS", i.fetchUSGS}}
	for _, loader := range loaders {
		wg.Add(1)
		go func() { defer wg.Done(); items, err := loader.fn(ctx); results <- result{loader.name, items, err} }()
	}
	go func() { wg.Wait(); close(results) }()
	for res := range results {
		if res.err != nil {
			i.logger.Error("source sync failed", "source", res.source, "error", res.err)
			continue
		}
		accepted := 0
		for _, item := range res.items {
			if err := i.publish(ctx, item); err != nil {
				i.logger.Error("incident publish failed", "source", res.source, "id", item.ID, "error", err)
				continue
			}
			accepted++
		}
		i.logger.Info("source sync complete", "source", res.source, "fetched", len(res.items), "accepted", accepted)
	}
}

func (i *Ingestor) fetchEONET(ctx context.Context) ([]Incident, error) {
	var payload struct {
		Events []struct {
			ID, Title, Description, Link string
			Categories                   []struct{ ID, Title string }
			Geometry                     []struct {
				Date        time.Time
				Type        string
				Coordinates []float64
			}
		} `json:"events"`
	}
	if err := i.getJSON(ctx, eonetURL, &payload); err != nil {
		return nil, err
	}
	items := make([]Incident, 0, len(payload.Events))
	for _, event := range payload.Events {
		if len(event.Geometry) == 0 || len(event.Geometry[len(event.Geometry)-1].Coordinates) < 2 {
			continue
		}
		geometry := event.Geometry[len(event.Geometry)-1]
		kind := "other"
		if len(event.Categories) > 0 {
			kind = normalizeKind(event.Categories[0].ID)
		}
		items = append(items, Incident{ID: "eonet-" + event.ID, ExternalID: event.ID, Title: event.Title, Kind: kind, Severity: "moderate", Status: "active", Source: "NASA EONET", SourceURL: event.Link, Description: fallback(event.Description, "Near-real-time natural event reported by NASA EONET."), Latitude: geometry.Coordinates[1], Longitude: geometry.Coordinates[0], StartedAt: geometry.Date, UpdatedAt: time.Now().UTC(), Confidence: .82, Regions: []string{}, Metadata: map[string]any{"provider": "eonet-v3"}})
	}
	return items, nil
}

func (i *Ingestor) fetchNWS(ctx context.Context) ([]Incident, error) {
	var payload struct {
		Features []struct {
			ID       string `json:"id"`
			Geometry *struct {
				Type        string          `json:"type"`
				Coordinates json.RawMessage `json:"coordinates"`
			} `json:"geometry"`
			Properties struct {
				Event, Severity, Certainty, Urgency, Description, AreaDesc, Web string
				Sent                                                            time.Time
				Ends                                                            *time.Time
			} `json:"properties"`
		} `json:"features"`
	}
	if err := i.getJSON(ctx, nwsURL, &payload); err != nil {
		return nil, err
	}
	items := make([]Incident, 0, len(payload.Features))
	for _, feature := range payload.Features {
		if feature.Geometry == nil {
			continue
		}
		lat, lon, ok := centroid(feature.Geometry.Coordinates)
		if !ok {
			continue
		}
		items = append(items, Incident{ID: "nws-" + shortID(feature.ID), ExternalID: feature.ID, Title: feature.Properties.Event, Kind: kindFromTitle(feature.Properties.Event), Severity: normalizeSeverity(feature.Properties.Severity), Status: "active", Source: "NOAA / NWS", SourceURL: feature.Properties.Web, Description: trim(feature.Properties.Description, 420), Latitude: lat, Longitude: lon, StartedAt: feature.Properties.Sent, UpdatedAt: time.Now().UTC(), Confidence: .96, Regions: splitRegions(feature.Properties.AreaDesc), Metadata: map[string]any{"expires": feature.Properties.Ends, "providerSeverity": feature.Properties.Severity, "certainty": feature.Properties.Certainty, "urgency": feature.Properties.Urgency}})
	}
	return items, nil
}

func (i *Ingestor) fetchUSGS(ctx context.Context) ([]Incident, error) {
	var payload struct {
		Features []struct {
			ID         string
			Properties struct {
				Mag          float64
				Place, URL   string
				Time         int64
				Significance int `json:"sig"`
				Tsunami      int
			}
			Geometry struct{ Coordinates []float64 }
		} `json:"features"`
	}
	if err := i.getJSON(ctx, usgsURL, &payload); err != nil {
		return nil, err
	}
	items := make([]Incident, 0, len(payload.Features))
	for _, feature := range payload.Features {
		if len(feature.Geometry.Coordinates) < 2 {
			continue
		}
		severity := "moderate"
		if feature.Properties.Mag >= 6 {
			severity = "critical"
		} else if feature.Properties.Mag >= 5 {
			severity = "high"
		}
		metadata := map[string]any{"magnitude": feature.Properties.Mag, "significance": feature.Properties.Significance, "tsunami": feature.Properties.Tsunami == 1}
		if len(feature.Geometry.Coordinates) >= 3 {
			metadata["depthKm"] = feature.Geometry.Coordinates[2]
		}
		items = append(items, Incident{ID: "usgs-" + feature.ID, ExternalID: feature.ID, Title: fmt.Sprintf("M%.1f earthquake — %s", feature.Properties.Mag, feature.Properties.Place), Kind: "earthquake", Severity: severity, Status: "monitoring", Source: "USGS", SourceURL: feature.Properties.URL, Description: "Automated earthquake event from the USGS significant-event feed.", Latitude: feature.Geometry.Coordinates[1], Longitude: feature.Geometry.Coordinates[0], StartedAt: time.UnixMilli(feature.Properties.Time).UTC(), UpdatedAt: time.Now().UTC(), Confidence: .99, Regions: []string{feature.Properties.Place}, Metadata: metadata})
	}
	return items, nil
}

func (i *Ingestor) getJSON(ctx context.Context, url string, target any) error {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, url, nil)
	if err != nil {
		return err
	}
	req.Header.Set("Accept", "application/geo+json, application/json")
	req.Header.Set("User-Agent", i.userAgent)
	res, err := i.client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	if res.StatusCode >= 300 {
		return fmt.Errorf("%s returned %s", url, res.Status)
	}
	return json.NewDecoder(res.Body).Decode(target)
}
func (i *Ingestor) publish(ctx context.Context, item Incident) error {
	payload, _ := json.Marshal(item)
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, strings.TrimRight(i.apiURL, "/")+"/api/v1/incidents", bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	if i.apiKey != "" {
		req.Header.Set("X-API-Key", i.apiKey)
	}
	res, err := i.client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	if res.StatusCode >= 300 {
		return fmt.Errorf("api returned %s", res.Status)
	}
	return nil
}

func centroid(raw json.RawMessage) (float64, float64, bool) {
	var rings [][][]float64
	if err := json.Unmarshal(raw, &rings); err == nil && len(rings) > 0 && len(rings[0]) > 0 {
		var lat, lon float64
		for _, point := range rings[0] {
			if len(point) >= 2 {
				lon += point[0]
				lat += point[1]
			}
		}
		n := float64(len(rings[0]))
		return lat / n, lon / n, true
	}
	var point []float64
	if err := json.Unmarshal(raw, &point); err == nil && len(point) >= 2 {
		return point[1], point[0], true
	}
	return 0, 0, false
}
func normalizeKind(value string) string {
	v := strings.ToLower(value)
	switch {
	case strings.Contains(v, "wildfire"):
		return "wildfire"
	case strings.Contains(v, "storm") || strings.Contains(v, "cyclone"):
		return "storm"
	case strings.Contains(v, "flood"):
		return "flood"
	case strings.Contains(v, "volcano"):
		return "volcano"
	case strings.Contains(v, "earthquake"):
		return "earthquake"
	default:
		return "other"
	}
}
func kindFromTitle(value string) string { return normalizeKind(value) }
func normalizeSeverity(value string) string {
	switch strings.ToLower(value) {
	case "extreme":
		return "critical"
	case "severe":
		return "high"
	case "moderate":
		return "moderate"
	default:
		return "low"
	}
}
func splitRegions(value string) []string {
	parts := strings.Split(value, ";")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		if v := strings.TrimSpace(part); v != "" {
			result = append(result, v)
		}
	}
	return result
}
func shortID(value string) string {
	parts := strings.Split(strings.TrimRight(value, "/"), "/")
	return parts[len(parts)-1]
}
func trim(value string, max int) string {
	value = strings.TrimSpace(value)
	if len(value) <= max {
		return value
	}
	return value[:max-1] + "…"
}
func fallback(value, other string) string {
	if strings.TrimSpace(value) == "" {
		return other
	}
	return value
}
func env(key, value string) string {
	if v := strings.TrimSpace(os.Getenv(key)); v != "" {
		return v
	}
	return value
}
func durationEnv(key string, value time.Duration) time.Duration {
	if v := os.Getenv(key); v != "" {
		if d, err := time.ParseDuration(v); err == nil {
			return d
		}
		if seconds, err := strconv.Atoi(v); err == nil {
			return time.Duration(seconds) * time.Second
		}
	}
	return value
}
