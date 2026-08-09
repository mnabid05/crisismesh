import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  scenarios: {
    incident_readers: { executor: "ramping-vus", startVUs: 0, stages: [{ duration: "30s", target: 25 }, { duration: "1m", target: 25 }, { duration: "15s", target: 0 }] },
  },
  thresholds: { http_req_failed: ["rate<0.01"], http_req_duration: ["p(95)<300"] },
};

const baseUrl = __ENV.API_URL || "http://localhost:8080";
export default function () {
  const incidents = http.get(`${baseUrl}/api/v1/incidents?limit=50`);
  check(incidents, { "incidents status is 200": (response) => response.status === 200 });
  const summary = http.get(`${baseUrl}/api/v1/summary`);
  check(summary, { "summary status is 200": (response) => response.status === 200 });
  sleep(1);
}

