package main

import (
	"context"
	"log/slog"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/crisismesh/crisismesh/services/api/internal/config"
	"github.com/crisismesh/crisismesh/services/api/internal/httpapi"
	"github.com/crisismesh/crisismesh/services/api/internal/integrations"
	"github.com/crisismesh/crisismesh/services/api/internal/store"
	"github.com/crisismesh/crisismesh/services/api/internal/telemetry"
)

func main() {
	cfg := config.Load()
	logger := slog.New(slog.NewJSONHandler(os.Stdout, nil))
	ctx := context.Background()
	var st store.Store = store.NewMemory()
	if cfg.DatabaseURL != "" {
		if pg, err := store.OpenPostgres(ctx, cfg.DatabaseURL); err == nil {
			st = pg
			logger.Info("postgres persistence enabled")
		} else {
			logger.Warn("postgres unavailable; using in-memory store", "error", err)
		}
	}
	defer st.Close()
	var broker telemetry.Broker = telemetry.NewLocalBroker()
	if cfg.NATSURL != "" {
		if natsBroker, err := telemetry.NewNATSBroker(cfg.NATSURL); err == nil {
			broker = natsBroker
			logger.Info("nats event bus enabled")
		} else {
			logger.Warn("nats unavailable; using local broker", "error", err)
		}
	}
	defer broker.Close()
	handler := httpapi.New(st, broker, integrations.NewIntelligenceClient(cfg.IntelligenceURL), logger, cfg.AllowedOrigins, cfg.APIKey).Handler()
	server := &http.Server{Addr: ":" + cfg.Port, Handler: handler, ReadHeaderTimeout: 5 * time.Second, ReadTimeout: 15 * time.Second, WriteTimeout: 30 * time.Second, IdleTimeout: 60 * time.Second}
	go func() {
		logger.Info("api listening", "port", cfg.Port, "environment", cfg.Environment)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			logger.Error("server stopped", "error", err)
			os.Exit(1)
		}
	}()
	stop := make(chan os.Signal, 1)
	signal.Notify(stop, syscall.SIGINT, syscall.SIGTERM)
	<-stop
	shutdownCtx, cancel := context.WithTimeout(context.Background(), cfg.ShutdownTimeout)
	defer cancel()
	_ = server.Shutdown(shutdownCtx)
}
