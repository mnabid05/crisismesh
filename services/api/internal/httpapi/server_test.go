package httpapi

import (
	"encoding/json"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"testing"

	"github.com/crisismesh/crisismesh/services/api/internal/integrations"
	"github.com/crisismesh/crisismesh/services/api/internal/store"
	"github.com/crisismesh/crisismesh/services/api/internal/telemetry"
)

func testServer() http.Handler {
	return New(store.NewMemory(), telemetry.NewLocalBroker(), integrations.NewIntelligenceClient("http://127.0.0.1:1"), slog.New(slog.NewTextHandler(io.Discard, nil)), []string{"http://localhost:3000"}, "").Handler()
}

func TestHealth(t *testing.T) {
	request := httptest.NewRequest(http.MethodGet, "/healthz", nil)
	response := httptest.NewRecorder()
	testServer().ServeHTTP(response, request)
	if response.Code != 200 {
		t.Fatalf("expected 200, got %d", response.Code)
	}
}

func TestListIncidents(t *testing.T) {
	request := httptest.NewRequest(http.MethodGet, "/api/v1/incidents?severity=critical", nil)
	response := httptest.NewRecorder()
	testServer().ServeHTTP(response, request)
	if response.Code != 200 {
		t.Fatalf("expected 200, got %d", response.Code)
	}
	var body struct {
		Count int `json:"count"`
	}
	if err := json.NewDecoder(response.Body).Decode(&body); err != nil {
		t.Fatal(err)
	}
	if body.Count != 1 {
		t.Fatalf("expected one critical incident, got %d", body.Count)
	}
}

func TestCORS(t *testing.T) {
	request := httptest.NewRequest(http.MethodOptions, "/api/v1/incidents", nil)
	request.Header.Set("Origin", "http://localhost:3000")
	response := httptest.NewRecorder()
	testServer().ServeHTTP(response, request)
	if got := response.Header().Get("Access-Control-Allow-Origin"); got != "http://localhost:3000" {
		t.Fatalf("unexpected origin %q", got)
	}
}
