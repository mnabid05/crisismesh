package config

import (
	"os"
	"strings"
	"time"
)

type Config struct {
	Port            string
	Environment     string
	DatabaseURL     string
	NATSURL         string
	IntelligenceURL string
	AllowedOrigins  []string
	APIKey          string
	ShutdownTimeout time.Duration
}

func Load() Config {
	return Config{
		Port:            env("API_PORT", "8080"),
		Environment:     env("CRISISMESH_ENV", "development"),
		DatabaseURL:     os.Getenv("DATABASE_URL"),
		NATSURL:         os.Getenv("NATS_URL"),
		IntelligenceURL: env("INTELLIGENCE_URL", "http://localhost:8090"),
		AllowedOrigins:  split(env("ALLOW_ORIGINS", "http://localhost:3000")),
		APIKey:          os.Getenv("CRISISMESH_API_KEY"),
		ShutdownTimeout: 10 * time.Second,
	}
}

func env(key, fallback string) string {
	if value := strings.TrimSpace(os.Getenv(key)); value != "" {
		return value
	}
	return fallback
}

func split(value string) []string {
	parts := strings.Split(value, ",")
	result := make([]string, 0, len(parts))
	for _, part := range parts {
		if trimmed := strings.TrimSpace(part); trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}
