package httpapi

import (
	"context"
	"crypto/rand"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"math"
	"net/http"
	"strconv"
	"strings"
	"sync/atomic"
	"time"

	"github.com/crisismesh/crisismesh/services/api/internal/domain"
	"github.com/crisismesh/crisismesh/services/api/internal/integrations"
	"github.com/crisismesh/crisismesh/services/api/internal/store"
	"github.com/crisismesh/crisismesh/services/api/internal/telemetry"
)

type Server struct {
	store        store.Store
	broker       telemetry.Broker
	intelligence *integrations.IntelligenceClient
	logger       *slog.Logger
	apiKey       string
	origins      map[string]struct{}
	requests     atomic.Uint64
	errors       atomic.Uint64
	ingested     atomic.Uint64
}

func New(st store.Store, broker telemetry.Broker, intelligence *integrations.IntelligenceClient, logger *slog.Logger, origins []string, apiKey string) *Server {
	allowed := make(map[string]struct{}, len(origins))
	for _, origin := range origins {
		allowed[origin] = struct{}{}
	}
	return &Server{store: st, broker: broker, intelligence: intelligence, logger: logger, origins: allowed, apiKey: apiKey}
}

func (s *Server) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("GET /healthz", s.health)
	mux.HandleFunc("GET /readyz", s.health)
	mux.HandleFunc("GET /metrics", s.metrics)
	mux.HandleFunc("GET /api/v1/incidents", s.listIncidents)
	mux.HandleFunc("POST /api/v1/incidents", s.ingestIncident)
	mux.HandleFunc("GET /api/v1/incidents/{id}", s.getIncident)
	mux.HandleFunc("GET /api/v1/resources", s.listResources)
	mux.HandleFunc("GET /api/v1/allocations", s.listAllocations)
	mux.HandleFunc("POST /api/v1/allocations", s.createAllocation)
	mux.HandleFunc("GET /api/v1/summary", s.summary)
	mux.HandleFunc("GET /api/v1/stream", s.stream)
	return s.recover(s.logging(s.cors(s.authenticate(mux))))
}

func (s *Server) health(w http.ResponseWriter, _ *http.Request) {
	writeJSON(w, http.StatusOK, map[string]any{"status": "ok", "service": "crisismesh-api", "time": time.Now().UTC()})
}

func (s *Server) metrics(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("Content-Type", "text/plain; version=0.0.4")
	fmt.Fprintf(w, "# HELP crisismesh_http_requests_total Total HTTP requests.\n# TYPE crisismesh_http_requests_total counter\ncrisismesh_http_requests_total %d\n", s.requests.Load())
	fmt.Fprintf(w, "# HELP crisismesh_http_errors_total Total HTTP errors.\n# TYPE crisismesh_http_errors_total counter\ncrisismesh_http_errors_total %d\n", s.errors.Load())
	fmt.Fprintf(w, "# HELP crisismesh_incidents_ingested_total Total incidents ingested.\n# TYPE crisismesh_incidents_ingested_total counter\ncrisismesh_incidents_ingested_total %d\n", s.ingested.Load())
}

func (s *Server) listIncidents(w http.ResponseWriter, r *http.Request) {
	limit, _ := strconv.Atoi(r.URL.Query().Get("limit"))
	items, err := s.store.ListIncidents(r.Context(), domain.IncidentFilter{Kind: r.URL.Query().Get("kind"), Severity: r.URL.Query().Get("severity"), Status: r.URL.Query().Get("status"), Limit: limit})
	if err != nil {
		s.fail(w, http.StatusInternalServerError, "list_failed", err)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"data": items, "count": len(items)})
}

func (s *Server) getIncident(w http.ResponseWriter, r *http.Request) {
	item, err := s.store.GetIncident(r.Context(), r.PathValue("id"))
	if errors.Is(err, store.ErrNotFound) {
		s.fail(w, http.StatusNotFound, "not_found", err)
		return
	}
	if err != nil {
		s.fail(w, http.StatusInternalServerError, "get_failed", err)
		return
	}
	writeJSON(w, http.StatusOK, item)
}

func (s *Server) ingestIncident(w http.ResponseWriter, r *http.Request) {
	var item domain.Incident
	if err := decodeJSON(w, r, &item); err != nil {
		s.fail(w, http.StatusBadRequest, "invalid_json", err)
		return
	}
	if strings.TrimSpace(item.Title) == "" || math.Abs(item.Latitude) > 90 || math.Abs(item.Longitude) > 180 {
		s.fail(w, http.StatusUnprocessableEntity, "invalid_incident", errors.New("title and valid coordinates are required"))
		return
	}
	now := time.Now().UTC()
	if item.ID == "" {
		item.ID = "cm-" + randomID()
	}
	if item.StartedAt.IsZero() {
		item.StartedAt = now
	}
	item.UpdatedAt = now
	if item.Status == "" {
		item.Status = "active"
	}
	if item.Source == "" {
		item.Source = "operator"
	}
	if item.Kind == "" {
		item.Kind = "other"
	}
	if scored, err := s.intelligence.Score(r.Context(), item); err == nil {
		item = scored
	} else if item.RiskScore == 0 {
		item.RiskScore = 50
		item.Confidence = .5
		item.Severity = "moderate"
	}
	if err := s.store.UpsertIncident(r.Context(), item); err != nil {
		s.fail(w, http.StatusInternalServerError, "persist_failed", err)
		return
	}
	payload, _ := json.Marshal(telemetry.Event{Type: "incident.updated", Data: item})
	_ = s.broker.Publish(r.Context(), payload)
	s.ingested.Add(1)
	writeJSON(w, http.StatusCreated, item)
}

func (s *Server) listResources(w http.ResponseWriter, r *http.Request) {
	items, err := s.store.ListResources(r.Context())
	if err != nil {
		s.fail(w, 500, "list_failed", err)
		return
	}
	writeJSON(w, 200, map[string]any{"data": items, "count": len(items)})
}

func (s *Server) listAllocations(w http.ResponseWriter, r *http.Request) {
	items, err := s.store.ListAllocations(r.Context(), r.URL.Query().Get("incidentId"))
	if err != nil {
		s.fail(w, 500, "list_failed", err)
		return
	}
	writeJSON(w, 200, map[string]any{"data": items, "count": len(items)})
}

func (s *Server) createAllocation(w http.ResponseWriter, r *http.Request) {
	var request domain.AllocationRequest
	if err := decodeJSON(w, r, &request); err != nil {
		s.fail(w, 400, "invalid_json", err)
		return
	}
	incident, err := s.store.GetIncident(r.Context(), request.IncidentID)
	if err != nil {
		s.fail(w, 404, "incident_not_found", err)
		return
	}
	resources, err := s.store.ListResources(r.Context())
	if err != nil {
		s.fail(w, 500, "resources_failed", err)
		return
	}
	if len(request.ResourceIDs) > 0 {
		allowed := map[string]bool{}
		for _, id := range request.ResourceIDs {
			allowed[id] = true
		}
		filtered := resources[:0]
		for _, resource := range resources {
			if allowed[resource.ID] {
				filtered = append(filtered, resource)
			}
		}
		resources = filtered
	}
	items, err := s.intelligence.Allocate(r.Context(), incident, resources)
	if err != nil {
		s.fail(w, 502, "allocation_failed", err)
		return
	}
	if err := s.store.SaveAllocations(r.Context(), items); err != nil {
		s.fail(w, 500, "persist_failed", err)
		return
	}
	payload, _ := json.Marshal(telemetry.Event{Type: "allocation.created", Data: items})
	_ = s.broker.Publish(r.Context(), payload)
	writeJSON(w, http.StatusCreated, map[string]any{"data": items, "count": len(items)})
}

func (s *Server) summary(w http.ResponseWriter, r *http.Request) {
	item, err := s.store.Summary(r.Context())
	if err != nil {
		s.fail(w, 500, "summary_failed", err)
		return
	}
	writeJSON(w, 200, item)
}

func (s *Server) stream(w http.ResponseWriter, r *http.Request) {
	flusher, ok := w.(http.Flusher)
	if !ok {
		s.fail(w, 500, "stream_unsupported", errors.New("streaming unavailable"))
		return
	}
	w.Header().Set("Content-Type", "text/event-stream")
	w.Header().Set("Cache-Control", "no-cache")
	w.Header().Set("Connection", "keep-alive")
	ch, cancel := s.broker.Subscribe()
	defer cancel()
	fmt.Fprint(w, "event: connected\ndata: {\"status\":\"connected\"}\n\n")
	flusher.Flush()
	keepAlive := time.NewTicker(20 * time.Second)
	defer keepAlive.Stop()
	for {
		select {
		case <-r.Context().Done():
			return
		case payload, open := <-ch:
			if !open {
				return
			}
			fmt.Fprintf(w, "event: update\ndata: %s\n\n", payload)
			flusher.Flush()
		case <-keepAlive.C:
			fmt.Fprint(w, ": keepalive\n\n")
			flusher.Flush()
		}
	}
}

func (s *Server) fail(w http.ResponseWriter, status int, code string, err error) {
	s.errors.Add(1)
	s.logger.Error("request failed", "code", code, "error", err)
	writeJSON(w, status, map[string]any{"error": map[string]string{"code": code, "message": err.Error()}})
}

func writeJSON(w http.ResponseWriter, status int, value any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(value)
}
func decodeJSON(w http.ResponseWriter, r *http.Request, target any) error {
	r.Body = http.MaxBytesReader(w, r.Body, 1<<20)
	decoder := json.NewDecoder(r.Body)
	decoder.DisallowUnknownFields()
	return decoder.Decode(target)
}
func randomID() string {
	bytes := make([]byte, 6)
	_, _ = rand.Read(bytes)
	return hex.EncodeToString(bytes)
}

type contextKey string

const requestIDKey contextKey = "request-id"

func (s *Server) logging(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		s.requests.Add(1)
		requestID := r.Header.Get("X-Request-ID")
		if requestID == "" {
			requestID = randomID()
		}
		w.Header().Set("X-Request-ID", requestID)
		next.ServeHTTP(w, r.WithContext(context.WithValue(r.Context(), requestIDKey, requestID)))
		s.logger.Info("request", "method", r.Method, "path", r.URL.Path, "duration", time.Since(start), "request_id", requestID)
	})
}
func (s *Server) recover(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer func() {
			if value := recover(); value != nil {
				s.fail(w, 500, "internal_error", fmt.Errorf("panic: %v", value))
			}
		}()
		next.ServeHTTP(w, r)
	})
}
func (s *Server) cors(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		origin := r.Header.Get("Origin")
		if _, ok := s.origins[origin]; ok {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Vary", "Origin")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type, X-API-Key, X-Request-ID")
			w.Header().Set("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
		}
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next.ServeHTTP(w, r)
	})
}
func (s *Server) authenticate(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if s.apiKey != "" && r.Method != "GET" && r.Header.Get("X-API-Key") != s.apiKey {
			s.fail(w, 401, "unauthorized", errors.New("valid X-API-Key required"))
			return
		}
		next.ServeHTTP(w, r)
	})
}
