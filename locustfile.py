"""Locust load profile and release gate for the iris-prediction service.

Workload (unchanged between user-count comparisons):
  * wait_time      between(1, 2)
  * POST /predict  task weight 3  - a correct prediction must be setosa
  * GET /          task weight 1  - service identity must be iris-prediction

Every request is validated inside catch_response, so a sample only passes when
the status code AND the expected JSON content are right. HTTP 200 with the
wrong body is a failure, not a success.

@events.quitting applies the predeclared gate:
  * at least 20 requests
  * failure ratio at most 0.01
  * aggregate p95 response time at most P95_LIMIT_MS (default 1000 ms)

Missing p95 or no traffic fails the gate. The thresholds are classroom policy
and must not be loosened to obtain a green run.
"""

import os

from locust import HttpUser, between, events, task

WAIT_MIN_SECONDS = 1
WAIT_MAX_SECONDS = 2
REQUEST_TIMEOUT_SECONDS = 10
VALID_MEASUREMENTS = [5.1, 3.5, 1.4, 0.2]
EXPECTED_SERVICE = "iris-prediction"
EXPECTED_PREDICTION = "setosa"

MIN_REQUESTS = 20
MAX_FAILURE_RATIO = 0.01
P95_LIMIT_MS = int(os.environ.get("P95_LIMIT_MS", "1000"))


class IrisUser(HttpUser):
    """Simulated client: mostly predicts, occasionally reads service identity."""

    wait_time = between(WAIT_MIN_SECONDS, WAIT_MAX_SECONDS)

    @task(3)
    def predict(self):
        with self.client.post(
            "/predict",
            json={"measurements": VALID_MEASUREMENTS},
            timeout=REQUEST_TIMEOUT_SECONDS,
            catch_response=True,
            name="POST /predict",
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected status 200, got {response.status_code}")
                return
            try:
                body = response.json()
            except ValueError:
                response.failure("response body was not valid JSON")
                return
            prediction = body.get("prediction") if isinstance(body, dict) else None
            if prediction != EXPECTED_PREDICTION:
                response.failure(f"expected prediction {EXPECTED_PREDICTION!r}, got {prediction!r}")
            else:
                response.success()

    @task(1)
    def home(self):
        with self.client.get(
            "/",
            timeout=REQUEST_TIMEOUT_SECONDS,
            catch_response=True,
            name="GET /",
        ) as response:
            if response.status_code != 200:
                response.failure(f"expected status 200, got {response.status_code}")
                return
            try:
                body = response.json()
            except ValueError:
                response.failure("response body was not valid JSON")
                return
            service = body.get("service") if isinstance(body, dict) else None
            if service != EXPECTED_SERVICE:
                response.failure(f"expected service {EXPECTED_SERVICE!r}, got {service!r}")
            else:
                response.success()


def _aggregate_p95(stats_entry):
    """Return the aggregate p95 in ms, or None when it cannot be computed."""
    if not stats_entry.num_requests:
        return None
    try:
        return stats_entry.get_response_time_percentile(0.95)
    except (ValueError, IndexError):
        return None


@events.quitting.add_listener
def check_load_gate(environment, **_kwargs):
    """Turn the measured run into a pass/fail exit code for the pipeline."""
    stats = environment.stats.total
    total_requests = stats.num_requests
    total_failures = stats.num_failures
    failure_ratio = (total_failures / total_requests) if total_requests else 0.0
    p95_ms = _aggregate_p95(stats)
    median_ms = stats.get_response_time_percentile(0.5) if total_requests else 0
    mean_ms = stats.total_response_time / total_requests if total_requests else 0.0

    reasons = []
    if total_requests < MIN_REQUESTS:
        reasons.append(
            f"only {total_requests} requests, at least {MIN_REQUESTS} required (no traffic or too short)"
        )
    if failure_ratio > MAX_FAILURE_RATIO:
        reasons.append(
            f"failure ratio {failure_ratio:.4f} ({total_failures}/{total_requests}) "
            f"exceeds {MAX_FAILURE_RATIO}"
        )
    if p95_ms is None:
        reasons.append("aggregate p95 could not be computed")
    elif p95_ms > P95_LIMIT_MS:
        reasons.append(f"aggregate p95 {p95_ms:.0f} ms exceeds {P95_LIMIT_MS} ms")

    environment.process_exit_code = 1 if reasons else 0
    verdict = "FAIL" if reasons else "PASS"
    print(
        f"\nLOAD GATE {verdict}: requests={total_requests} failures={total_failures} "
        f"failure_ratio={failure_ratio:.4f} mean={mean_ms:.1f}ms median={median_ms:.0f}ms "
        f"p95={p95_ms if p95_ms is None else f'{p95_ms:.0f}ms'} "
        f"(limits: >={MIN_REQUESTS} requests, <={MAX_FAILURE_RATIO} failures, p95<={P95_LIMIT_MS}ms)"
    )
    for reason in reasons:
        print(f"  reason: {reason}")