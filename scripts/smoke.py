#!/usr/bin/env python3
"""Smoke checks for the iris-prediction service.

Three checks, all using only the Python standard library:

1. GET  /        -> HTTP 200 and service identity "iris-prediction".
2. POST /predict -> HTTP 200 and prediction "setosa" for four measurements.
3. POST /predict -> HTTP 400 and an "error" field for a two-number payload.

Home readiness is retried with bounded attempts so a container that is still
starting does not fail the run. Any unexpected result exits nonzero, so this
script can be used as a gate in CI. Success is printed only after every check
passes.

Usage: python scripts/smoke.py [BASE_URL]
       BASE_URL defaults to http://127.0.0.1:5000
"""

import json
import sys
import time
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "http://127.0.0.1:5000"
REQUEST_TIMEOUT = 10
READINESS_ATTEMPTS = 30
READINESS_DELAY_SECONDS = 1
EXPECTED_SERVICE = "iris-prediction"
VALID_MEASUREMENTS = [5.1, 3.5, 1.4, 0.2]
INVALID_MEASUREMENTS = [5.1, 3.5]


class SmokeFailure(Exception):
    """A check produced a result the release policy does not allow."""


def _url(base_url, path):
    return base_url.rstrip("/") + path


def _decode(raw):
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        raise SmokeFailure(f"response was not valid JSON: {exc}") from exc


def _request(base_url, method, path, payload=None):
    """Return (status_code, parsed_json_body) or raise SmokeFailure."""
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        _url(base_url, path), data=data, headers=headers, method=method
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            return response.status, _decode(response.read())
    except urllib.error.HTTPError as exc:
        # A 4xx/5xx is still a readable answer; the checks decide if it is correct.
        return exc.code, _decode(exc.read())
    except urllib.error.URLError as exc:
        raise SmokeFailure(f"{method} {path} could not reach the service: {exc.reason}") from exc
    except OSError as exc:
        raise SmokeFailure(f"{method} {path} failed: {exc}") from exc


def wait_for_home(base_url):
    """Poll GET / until it answers, so container startup is not mistaken for a fault."""
    last_error = "no attempt completed"
    for attempt in range(1, READINESS_ATTEMPTS + 1):
        try:
            status, body = _request(base_url, "GET", "/")
            if status == 200:
                print(f"home ready after {attempt} attempt(s)")
                return body
            last_error = f"status {status}"
        except SmokeFailure as exc:
            last_error = str(exc)
        time.sleep(READINESS_DELAY_SECONDS)
    raise SmokeFailure(
        f"service not ready after {READINESS_ATTEMPTS} attempts: {last_error}"
    )


def check_home(base_url):
    """GET / must be 200 and identify the service."""
    home = wait_for_home(base_url)
    if not isinstance(home, dict):
        raise SmokeFailure(f"GET / returned {type(home).__name__}, expected an object")
    service = home.get("service")
    if service != EXPECTED_SERVICE:
        raise SmokeFailure(f"service was {service!r}, expected {EXPECTED_SERVICE!r}")
    print(f"ok  GET / -> 200, service={service}")
    return home


def check_valid_prediction(base_url):
    """POST /predict with four numbers must predict setosa."""
    status, body = _request(
        base_url, "POST", "/predict", {"measurements": VALID_MEASUREMENTS}
    )
    if status != 200:
        raise SmokeFailure(f"valid request returned status {status}, expected 200")
    if not isinstance(body, dict):
        raise SmokeFailure(f"predict returned {type(body).__name__}, expected an object")
    prediction = body.get("prediction")
    if prediction != "setosa":
        raise SmokeFailure(f"prediction was {prediction!r}, expected 'setosa'")
    print(f"ok  POST /predict {VALID_MEASUREMENTS} -> 200, prediction={prediction}")
    return body


def check_invalid_payload_rejected(base_url):
    """POST /predict with two numbers must be rejected with an error message."""
    status, body = _request(
        base_url, "POST", "/predict", {"measurements": INVALID_MEASUREMENTS}
    )
    if status != 400:
        raise SmokeFailure(
            f"two-measurement payload returned status {status}, expected 400"
        )
    if not isinstance(body, dict) or not body.get("error"):
        raise SmokeFailure("rejected request did not include an error message")
    print(f"ok  POST /predict {INVALID_MEASUREMENTS} -> 400, error={body['error']!r}")
    return body


def main(argv):
    base_url = argv[1] if len(argv) > 1 else DEFAULT_BASE_URL
    print(f"smoke target: {base_url}")
    checks = (
        ("home identity", check_home),
        ("valid prediction", check_valid_prediction),
        ("invalid payload rejected", check_invalid_payload_rejected),
    )
    for name, check in checks:
        try:
            check(base_url)
        except SmokeFailure as exc:
            print(f"FAIL {name}: {exc}", file=sys.stderr)
            return 1
    print(f"SMOKE PASSED: 3/3 checks against {base_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))