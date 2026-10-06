"""Simple checks that the API behaves the way the assignment documents.

Run these after training:

    python train.py
    python test_app.py

The Flask test client talks to the application in-process, so no server has to
be started first. Any failure exits with a non-zero status so the run fails.
"""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import app  # noqa: E402  (needs the model, so train.py must run first)

VALID = [5.1, 3.5, 1.4, 0.2]
INVALID = [5.1, 3.5]

failures = []


def check(condition, label, detail):
    if condition:
        print(f"ok  {label}")
    else:
        print(f"FAIL {label}: {detail}")
        failures.append(label)


client = app.test_client()

home = client.get("/")
body = home.get_json()
check(
    home.status_code == 200 and isinstance(body, dict) and body.get("service") == "iris-prediction",
    "GET / returns 200 and service iris-prediction",
    f"status={home.status_code} body={body!r}",
)

good = client.post("/predict", json={"measurements": VALID})
body = good.get_json()
check(
    good.status_code == 200 and isinstance(body, dict) and body.get("prediction") == "setosa",
    "POST /predict with four numbers returns setosa",
    f"status={good.status_code} body={body!r}",
)

bad = client.post("/predict", json={"measurements": INVALID})
body = bad.get_json()
check(
    bad.status_code == 400 and isinstance(body, dict) and bool(body.get("error")),
    "POST /predict with two numbers is rejected with 400 and an error",
    f"status={bad.status_code} body={body!r}",
)

if failures:
    print(f"{len(failures)} check(s) failed", file=sys.stderr)
    sys.exit(1)

print("All checks passed")