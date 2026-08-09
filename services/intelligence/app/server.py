from __future__ import annotations

import json
import logging
import os
import time
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .allocation import allocate
from .features import EnvironmentalSignals
from .models import Incident, Resource
from .risk import score_incident
from .service import NeuralIntelligenceService

logging.basicConfig(level=logging.INFO, format='{"level":"%(levelname)s","message":"%(message)s"}')
LOGGER = logging.getLogger("crisismesh.intelligence")
METRICS = {"requests": 0, "errors": 0, "scores": 0, "neural_scores": 0, "allocations": 0}
NEURAL = NeuralIntelligenceService()


class Handler(BaseHTTPRequestHandler):
    server_version = "CrisisMeshIntelligence/0.1"

    def do_GET(self) -> None:  # noqa: N802
        METRICS["requests"] += 1
        if self.path == "/healthz":
            self.respond(HTTPStatus.OK, {"status": "ok", "service": "crisismesh-intelligence"})
        elif self.path == "/metrics":
            lines = []
            for name, value in METRICS.items():
                lines.append(f"# TYPE crisismesh_intelligence_{name}_total counter")
                lines.append(f"crisismesh_intelligence_{name}_total {value}")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(("\n".join(lines) + "\n").encode())
        else:
            self.respond(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})

    def do_POST(self) -> None:  # noqa: N802
        started = time.perf_counter()
        METRICS["requests"] += 1
        try:
            body = self.read_json()
            if self.path == "/v1/risk/score":
                METRICS["scores"] += 1
                self.respond(HTTPStatus.OK, score_incident(Incident.from_dict(body)))
            elif self.path == "/v1/neural/score":
                METRICS["neural_scores"] += 1
                incident = Incident.from_dict(body.get("incident", body))
                environment_payload = body.get("environment")
                environment = (
                    EnvironmentalSignals(**environment_payload)
                    if isinstance(environment_payload, dict)
                    else None
                )
                self.respond(HTTPStatus.OK, NEURAL.score(incident, environment))
            elif self.path == "/v1/allocate":
                incident = Incident.from_dict(body.get("incident") or {})
                resources = [Resource.from_dict(item) for item in body.get("resources", [])]
                allocations = allocate(incident, resources)
                METRICS["allocations"] += len(allocations)
                self.respond(
                    HTTPStatus.OK,
                    {"allocations": allocations, "modelVersion": "allocator-v1.0"},
                )
            else:
                self.respond(HTTPStatus.NOT_FOUND, {"error": {"code": "not_found"}})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            METRICS["errors"] += 1
            self.respond(
                HTTPStatus.BAD_REQUEST,
                {"error": {"code": "invalid_request", "message": str(exc)}},
            )
        finally:
            duration_ms = (time.perf_counter() - started) * 1000
            LOGGER.info("request path=%s duration_ms=%.2f", self.path, duration_ms)

    def read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_048_576:
            raise ValueError("request body must be between 1 byte and 1 MiB")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("request body must be a JSON object")
        return value

    def respond(self, status: HTTPStatus, value: object) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        return


def main() -> None:
    host = os.getenv("INTELLIGENCE_HOST", "0.0.0.0")
    port = int(os.getenv("INTELLIGENCE_PORT", "8090"))
    server = ThreadingHTTPServer((host, port), Handler)
    LOGGER.info("intelligence service listening host=%s port=%d", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
