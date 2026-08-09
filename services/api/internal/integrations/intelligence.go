package integrations

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"time"

	"github.com/crisismesh/crisismesh/services/api/internal/domain"
)

type IntelligenceClient struct {
	baseURL string
	client  *http.Client
}

func NewIntelligenceClient(baseURL string) *IntelligenceClient {
	return &IntelligenceClient{baseURL: baseURL, client: &http.Client{Timeout: 5 * time.Second}}
}

func (c *IntelligenceClient) Score(ctx context.Context, incident domain.Incident) (domain.Incident, error) {
	var response struct {
		RiskScore  float64 `json:"riskScore"`
		Confidence float64 `json:"confidence"`
		Severity   string  `json:"severity"`
	}
	if err := c.post(ctx, "/v1/risk/score", incident, &response); err != nil {
		return incident, err
	}
	incident.RiskScore, incident.Confidence, incident.Severity = response.RiskScore, response.Confidence, response.Severity
	return incident, nil
}

func (c *IntelligenceClient) Allocate(ctx context.Context, incident domain.Incident, resources []domain.Resource) ([]domain.Allocation, error) {
	request := map[string]any{"incident": incident, "resources": resources}
	var response struct {
		Allocations []domain.Allocation `json:"allocations"`
	}
	if err := c.post(ctx, "/v1/allocate", request, &response); err != nil {
		return nil, err
	}
	return response.Allocations, nil
}

func (c *IntelligenceClient) post(ctx context.Context, path string, body, target any) error {
	payload, err := json.Marshal(body)
	if err != nil {
		return err
	}
	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+path, bytes.NewReader(payload))
	if err != nil {
		return err
	}
	req.Header.Set("Content-Type", "application/json")
	res, err := c.client.Do(req)
	if err != nil {
		return err
	}
	defer res.Body.Close()
	if res.StatusCode >= 300 {
		return fmt.Errorf("intelligence service returned %s", res.Status)
	}
	return json.NewDecoder(res.Body).Decode(target)
}
