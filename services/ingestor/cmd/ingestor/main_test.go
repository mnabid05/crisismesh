package main

import (
	"encoding/json"
	"testing"
)

func TestCentroidPolygon(t *testing.T) {
	raw := json.RawMessage(`[[[-100,30],[-98,30],[-98,32],[-100,32]]]`)
	lat, lon, ok := centroid(raw)
	if !ok || lat != 31 || lon != -99 {
		t.Fatalf("unexpected centroid %.2f %.2f %v", lat, lon, ok)
	}
}
func TestCentroidPoint(t *testing.T) {
	lat, lon, ok := centroid(json.RawMessage(`[-74.2,26.7]`))
	if !ok || lat != 26.7 || lon != -74.2 {
		t.Fatalf("unexpected point")
	}
}
func TestNormalizeKind(t *testing.T) {
	cases := map[string]string{"wildfires": "wildfire", "Severe Storm Warning": "storm", "floods": "flood", "unknown": "other"}
	for input, want := range cases {
		if got := normalizeKind(input); got != want {
			t.Fatalf("%q: got %q want %q", input, got, want)
		}
	}
}

func TestNormalizeSeverity(t *testing.T) {
	cases := map[string]string{"Extreme": "critical", "Severe": "high", "Moderate": "moderate", "Minor": "low"}
	for input, want := range cases {
		if got := normalizeSeverity(input); got != want {
			t.Fatalf("%q: got %q want %q", input, got, want)
		}
	}
}
