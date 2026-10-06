# Week 14 — ML Image Delivery: evidence record

Repo: `https://github.com/ravindu57/ml_ops.git` · image name: `ghcr.io/ravindu57/ml_ops`
Author for all commits: `ravindu57 <djravinduremix2004@gmail.com>`
Pushed over SSH (`git@github.com:ravindu57/ml_ops.git`) — branches `main`, `staging`, `release-a` are live.

## GitHub runs — actual results

| Run | Branch | Source SHA | Tag | Digest | Outcome |
| --- | --- | --- | --- | --- | --- |
| [#1](https://github.com/ravindu57/ml_ops/actions/runs/37416627392) | main | `e1efeae2507e96265053689f3e579bbcf566fde4` | `sha-e1efeae2507e96265053689f3e579bbcf566fde4` | `sha256:377a2f8aee92c3b28e9d3ca10e6b3fa442a27faf533a6c6d03ca2f7ad2bc6132` | build ✅ · load_test ✅ · release ✅ → artifact `approved-release-e1efeae2507e96265053689f3e579bbcf566fde4` |
| [#2](https://github.com/ravindu57/ml_ops/actions/runs/37416628924) | staging | `96696f3393a6d94cf7944ba50c1fd8423e430d56` | `sha-96696f3393a6d94cf7944ba50c1fd8423e430d56` | `sha256:9d3e41cb34562daa6fa18fdc52346a3c19515cd72f0a37d5d92d03fce8024033` | build ✅ · load_test ✅ · **release ⏭️ skipped** |

Per-step results came from the public Actions API (`/actions/runs/<id>/jobs`); every build step
(checkout, lowercase name, QEMU, Buildx, GHCR login, build-push, digest output), every `load_test`
step (smoke, headless gate, report upload, logs, cleanup) and the `release` bundle steps on `main`
reported `success`. On `staging` the `Approved release bundle` job reported `skipped`, which is the
release-skip evidence: `if: github.ref == 'refs/heads/main'` held even though `build` and `load_test`
ran to completion.

### Cross-group handover, executed for real

The published digest was pulled **anonymously**, with no credentials of the publisher, and served a
valid prediction:

```bash
docker pull ghcr.io/ravindu57/ml_ops@sha256:377a2f8aee92c3b28e9d3ca10e6b3fa442a27faf533a6c6d03ca2f7ad2bc6132
# Status: Image is up to date for ghcr.io/ravindu57/ml_ops@sha256:377a2f8a...
docker run -d --name iris-share -p 127.0.0.1:5000:5000 ghcr.io/ravindu57/ml_ops@sha256:377a2f8a...
docker ps --filter name=iris-share
# iris-share | 377a2f8aee92e | Up 6 seconds | 127.0.0.1:5000->5000/tcp
curl -s http://127.0.0.1:5000/
# {"service":"iris-prediction","usage":"POST /predict with four measurements (release B)"}
curl -i -X POST http://127.0.0.1:5000/predict -H 'Content-Type: application/json' -d '{"measurements":[5.1,3.5,1.4,0.2]}'
# HTTP/1.1 200 OK
# {"prediction":"setosa"}
python scripts/smoke.py http://127.0.0.1:5000
# SMOKE PASSED: 3/3 checks against http://127.0.0.1:5000
```

No rebuild, no local build context and no `latest` tag were involved. Note that
`ghcr.io/v2/ravindu57/ml_ops/tags/list` answers `401 authentication required` even for a publicly
pullable package, so do not use that endpoint to test visibility — use `docker pull` instead.

### Branch history

| Commit | Branch | What it contains |
| --- | --- | --- |
| `b37dd9a` | main | `app.py`, `train.py`, `requirements.txt`, `Dockerfile`, `.dockerignore`, `.gitignore`, handout material |
| `2eca2b9` | main | `ML Delivery` workflow — `build` job only (Practical A) |
| `a8cacb8` | staging | `scripts/smoke.py`, `locustfile.py`, `load_test` job (Practical B) |
| `80b39e1` | staging → `release-a` | `compose.yaml`, `release` job with `production` environment (Practical C) |
| `4ee87db` | main ← staging | merge "approve release A after load gate" |
| `96696f3` | staging | `app.py` home usage message marked as release B (only line changed) |
| `e0e9ca3` | main ← staging | merge "approve release B" |
| `18d52e2`, `74a054a`, `e1efeae` | main | `EVIDENCE.md` documentation commits; the last one is the SHA that produced the published main digest |

`release-a` points at `80b39e1`, the last state whose `app.py` still carries the **original** usage
message. Running `ML Delivery` manually on that branch publishes a second digest whose `/` response
differs from the current one, which is the "old digest still returns the old message" demonstration.

Verified: `train.py` is byte-identical to `original_project/train.py`; `app.py` differs from the
original on exactly one line (the `usage` string), and `service` stays `iris-prediction`.

---

## Environment used for the measurements

| Item | Value |
| --- | --- |
| Host architecture | `x86_64` (Linux, Docker Desktop 29.6.2, engine API 1.55) |
| Docker Compose | v5.3.1 |
| Python | 3.12.3 (venv at `.venv`, Locust 2.46.7) |
| Image under test | locally built from `Dockerfile`, 555 MB, `linux/amd64` |
| Server | Flask development server inside the container, loopback `127.0.0.1:5000` |
| Fixed for both runs | image digest, 60 s duration, `between(1, 2)` wait, weights 3:1, payload `[5.1, 3.5, 1.4, 0.2]` |

---

## Practical A — automatic build and publish

### A1 Dockerfile and where the model exists

`Dockerfile` keeps the working structure from last week: `WORKDIR /app`, `COPY requirements.txt`
+ `pip install`, `COPY train.py` / `COPY app.py`, `RUN python train.py`, `EXPOSE 5000`,
`CMD ["python", "app.py"]`. The only additions are `ENV PYTHONUNBUFFERED=1` and
`PYTHONDONTWRITEBYTECODE=1` so container logs are reliable evidence.

`iris_model.joblib` exists **only inside the image**, created at build time by `RUN python train.py`:

```bash
docker build -t iris-local:a .
docker run --rm iris-local:a python -c "from pathlib import Path; print('model in image:', Path('/app/iris_model.joblib').is_file())"
# model in image: True
```

`.dockerignore` keeps `.venv`, `.git`, `__pycache__`, `reports/`, `original_project/`, `clues/`,
`iris_model.joblib` and any `.env`/`release.env` out of the build context, so no credentials and
no locally trained model enter a layer.

### A2 The publishing workflow

`.github/workflows/ml-delivery.yml`, `build` job, trigger `push` to `main` and `staging` plus
`workflow_dispatch`. Permissions `contents: read` + `packages: write`, `timeout-minutes: 45`.

Step order (ids in brackets): checkout `v5` → choose lowercase name `[name]` → QEMU `v3` →
Buildx `v3` → GHCR login `v3` → build-push `v6` `[build]` → expose digest `[build_ref]`.

* Image name `ghcr.io/${GITHUB_REPOSITORY,,}` → `ghcr.io/ravindu57/ml_ops` (lowercase enforced in Bash).
* Tag `sha-${{ github.sha }}`.
* `platforms: linux/amd64,linux/arm64`, `push: true`.
* Labels `org.opencontainers.image.source`, `.revision`, `.title`.
* Login uses `registry: ghcr.io`, `username: ${{ github.actor }}`, `password: ${{ secrets.GITHUB_TOKEN }}` — no literal token.
* Job output `image_ref = ghcr.io/ravindu57/ml_ops@<digest from steps.build.outputs.digest>`; the
  step fails loudly if the digest is empty. `load_test` and `release` consume exactly this string.

### A3 Error diagnosed (real, from this session)

**Symptom.** The first `docker version` reported a complete client section and then:

```
Cannot connect to the Docker daemon at unix:///home/ravindu/.docker/desktop/docker.sock. Is the docker daemon running?
```

`docker compose version` and `python3 --version` worked, so the CLI was installed; only the engine
socket was missing. Every later `docker build`, `docker run`, `docker pull` would have failed the
same way, and on GitHub-hosted CI this class of failure shows up as a build step error while the
local environment is fine.

**Fix.** Start the engine, then re-check with `docker info --format '{{.ServerVersion}} {{.Architecture}}'`,
which returned `29.6.2 x86_64`. Only then did `docker build` succeed.

Two smaller faults worth recording:

* `ModuleNotFoundError: No module named 'locust'` after creating `.venv` — the `pip install` had
  been interrupted. Fix: reinstall into `.venv` and verify with `python -c "import locust; print(locust.__version__)"` before running any load test.
* `cp: cannot stat 'compose.yaml'` when rehearsing the release bundle — the command was executed
  from the parent `week 11` folder instead of the project root. Fix: always run bundle steps with
  the project directory as the working directory; the workflow's `actions/checkout` step guarantees this.

### A3b Two deployment errors diagnosed against the published digest

**1. Port already allocated.** Starting the digest-pinned container failed:

```
docker: Error response from daemon: failed to set up container networking:
Bind for 127.0.0.1:5000 failed: port is already allocated
```

Evidence: `docker ps -a --filter label=com.docker.compose.project` still showed the `iris` container
of the `iris-classroom` project from the C-section rollback rehearsal. The requests that appeared to
succeed at that moment were answered by the compose stack, not by the new container — a silent
wrong-source trap. Fix: `docker compose --env-file release.env -p iris-classroom down` before
starting a standalone container, or put the release on another port with `HOST_PORT=5001`. The
smoke script was also the useful signal here: pointed at nothing it printed
`FAIL home identity: service not ready after 30 attempts: GET / could not reach the service: [Errno 111] Connection refused`
instead of a false pass.

**2. Container name already in use.** The next attempt failed with
`Conflict. The container name "/iris-share" is already in use`, because the failed run had left a
created-but-not-started container behind. Fix: `docker rm -f iris-share` before re-running; inspect
`docker ps -a`, not `docker ps`, when a container is "missing".

### A4 Handover to another group

After the first successful run, fill in and give the other group the full reference (not the
abbreviated display form):

```bash
docker pull ghcr.io/ravindu57/ml_ops@sha256:DIGEST
docker run -d --name iris-share -p 127.0.0.1:5000:5000 ghcr.io/ravindu57/ml_ops@sha256:DIGEST
docker ps
docker logs iris-share
curl http://127.0.0.1:5000/
curl -i -X POST http://127.0.0.1:5000/predict -H 'Content-Type: application/json' -d '{"measurements":[5.1,3.5,1.4,0.2]}'
```

Local rehearsal of the same flow against a scratch registry (`registry:2` on `127.0.0.1:5001`,
used only because GHCR publishing needs the push to GitHub):

| Version | Digest | Result |
| --- | --- | --- |
| A | `sha256:da13d7ee4edde676c3ef1649b01eafa9780678ff762144a8528c728d842c626a` | `GET /` → `{"service":"iris-prediction","usage":"POST /predict with four measurements"}`, `POST /predict` → `{"prediction":"setosa"}` |
| B | `sha256:ff2daf757b845ab47a213f9ed836dcd23020c34de58a6af89120faa63d716ada` | same service, usage marked `(release B)` |

Pulling each digest by value, with no rebuild and no credentials of the publisher, produced both
identities: the old digest still returns the old message, which is the point of digest pinning.

### Diagram

```
  [ source push ]            [ GitHub runner ]              [ GHCR registry ]        [ receiver group ]
  git commit + push  ──────► checkout @SHA                    ghcr.io/ravindu57/ml_ops
  main | staging             Buildx + QEMU                     tag  sha-<commit>
                            train.py runs inside build        digest sha256:...
                            build-push  ──────────────────►    one manifest, two platforms
                                   │                           linux/amd64 + linux/arm64
                                   └── job output image_ref ──►  name@sha256:...
                                                                        │
                                              docker pull name@sha256:... ┘
                                                            │
                                                  [ container ] iris-prediction
                                                  Flask :5000, GET / + POST /predict
```

* Source stores the files and the commit graph.
* The runner stores nothing permanent; it is an ephemeral Ubuntu VM that builds, trains, tests and
  pushes, then is discarded.
* The registry stores the image layers and, crucially, the immutable manifest digest plus the
  platform list; the digest is the identity used everywhere downstream.
* The receiver stores only a local image copy plus the running container's state.

---

## Practical B — load test with Locust

### B1 Files and what they assert

`scripts/smoke.py` (standard library only, 3 checks, exit code gates CI):

1. `GET /` retried up to 30 times with a 1 s delay so a starting container is not a fault; must be
   HTTP 200 **and** `service == "iris-prediction"`.
2. `POST /predict {"measurements":[5.1,3.5,1.4,0.2]}` must be HTTP 200 **and**
   `prediction == "setosa"` — status alone is not enough.
3. `POST /predict {"measurements":[5.1,3.5]}` must be HTTP 400 **and** contain an `error` field.
   `urllib` raises `HTTPError` on 400, so the body is read from the exception to confirm the
   rejection is deliberate and explained.

`locustfile.py`: `IrisUser(HttpUser)` with `wait_time = between(1, 2)`, `@task(3)` predict,
`@task(1)` home, `timeout=10`, and every request inside `catch_response` with an explicit
`response.success()` / `response.failure(reason)`. A 200 with the wrong JSON is a failure — this is
the check that the web UI at 8089 being confused with port 5000 would otherwise hide.

Gate in `@events.quitting`: requests ≥ 20, failure ratio ≤ 0.01, aggregate p95 ≤ `P95_LIMIT_MS`
(default 1000). No traffic or an uncomputable p95 fails the gate; `environment.process_exit_code`
is set to 0 or 1. The thresholds are the predeclared classroom policy and were not changed to
obtain a green result.

### B2 Measurements (actual values from `reports/`)

| Metric | 10 users (`-u 10 -r 2`) | 50 users (`-u 50 -r 5`) |
| --- | --- | --- |
| Requests | 386 (391 after shutdown flush) | 1852 (1878 after shutdown flush) |
| Failures and failure percent | 0 — 0.00 % | 0 — 0.00 % |
| Mean response time ms | 4.21 | 3.87 |
| Median response time ms | 4 | 4 |
| p95 response time ms | 7 | 6 |
| Requests per second | 6.54 | 31.36 |
| Gate result | **Pass** — 386 ≥ 20, ratio 0 ≤ 0.01, p95 7 ≤ 1000 | **Pass** — 1852 ≥ 20, ratio 0 ≤ 0.01, p95 6 ≤ 1000 |

Retained artefacts: `reports/baseline_stats.csv`, `reports/baseline.html`,
`reports/comparison_stats.csv`, `reports/comparison.html`, plus the history CSVs. The CSV files
snapshot the stats at the final 1 s tick; Locust's shutdown flush accounts the few in-flight
requests shown in brackets in the console totals.

Hypothesis and conclusion: raising concurrency from 10 to 50 users was expected to increase
throughput roughly proportionally and to leave latency broadly flat, because inference is a single
in-memory decision-tree lookup. The measurements support that — throughput rose ~4.8× (6.54 →
31.36 req/s) while p95 stayed at 6–7 ms and no request failed — so for this workload the service
is CPU-bound per request rather than queue-bound at 50 users. It does **not** establish capacity:
60 s is short, the Flask development server was measured rather than a production WSGI server, and
one container on one laptop cannot show behaviour near saturation.

### B3 Staging load job

`load_test` job: `needs: build`, `packages: read`, fresh `ubuntu-latest`, checkout, Python 3.12,
`pip install "locust>=2.32,<3"`, GHCR login, `docker pull ${{ needs.build.outputs.image_ref }}`,
`docker run -d --name iris-staging -p 127.0.0.1:5000:5000 <same digest>`, `scripts/smoke.py`, then
`locust --headless -u 20 -r 5 -t 60s --csv reports/staging-load --html reports/staging-load.html`.
Report upload, container logs and container removal all use `if: always()`; `continue-on-error` is
not used anywhere, so a failed gate fails the job. On a `staging` push the `release` job is
skipped by `if: github.ref == 'refs/heads/main'` while `build` and `load_test` still run — that is
the expected release-skip evidence.

### B4 B6 failed-payload evidence, diagnosis and restore

Temporarily setting `VALID_MEASUREMENTS = [5.1, 3.5]` and running 10 users for 15 s:

```
64                 POST POST /predict: expected status 200, got 400
LOAD GATE FAIL: requests=90 failures=64 failure_ratio=0.7111 mean=3.9ms median=3ms p95=8ms
  reason: failure ratio 0.7111 (64/90) exceeds 0.01
EXIT=1
```

Diagnosis: the response times stayed at ~3–4 ms and p95 even improved, so this is not a
performance problem. The service correctly rejected the payload with HTTP 400
(`"measurements must be four numbers"`), and the semantic check inside `catch_response` converted
that correct rejection into a failed sample. The gate then failed on the failure-ratio condition
and returned exit code 1, which is the intended behaviour: the workload no longer matched the
service contract.

Restored `VALID_MEASUREMENTS = [5.1, 3.5, 1.4, 0.2]`, then `scripts/smoke.py` passed 3/3 and the
15 s rerun reported `requests=90 failures=0 failure_ratio=0.0000 p95=6ms`, `LOAD GATE PASS`,
`EXIT=0` (`reports/b6-fault*` and `reports/b6-restored*` retained).

---

## Practical C — continuous delivery

### C1 Compose and the release job

`compose.yaml` defines one service `iris` whose `image` comes from a **required** interpolation
variable, so a missing `IMAGE_REF` is an error rather than an accidental `latest`:

```bash
docker compose -f release/compose.yaml config      # without IMAGE_REF
# error while interpolating services.iris.image: required variable IMAGE_REF is missing a value
```

Ports `127.0.0.1:${HOST_PORT:-5000}:5000`, `restart: unless-stopped`, no `build:` section.

`release` job: `needs: [build, load_test]`, `if: github.ref == 'refs/heads/main'`,
`environment: production`. After approval it builds `release/` containing `compose.yaml`,
`smoke.py`, `release.env` (`IMAGE_REF` + `HOST_PORT`) and `source-commit.txt`, and uploads it as
`approved-release-<source SHA>`. No secrets are placed in the bundle.

`load_test` succeeding before `release` can start is what forces the load gate to precede approval;
the staging image is never silently substituted because `release` receives `needs.build.outputs.image_ref`
from the main-branch run itself.

**Finding: the environment name alone did not create a human gate.** Run #1 on `main` shows the
`Approved release bundle` job completing with `success` and no wait, because the `production`
environment did not exist beforehand — GitHub created it implicitly when the job first referenced
it, with **no required reviewers**, so nothing waited for a person. This is exactly the README's
"naming an environment does not require a human by itself". To get a real approval wait:

1. Repository **Settings → Environments → `production`** (now present) → **Required reviewers** →
   add an eligible collaborator → tick **Prevent self-review** → **Deployment branches and tags** →
   add `main`.
2. Re-run `ML Delivery` on `main`. The `Approved release bundle` job then shows *Waiting for approval*
   and only proceeds after that reviewer accepts.

Until that is configured, the merge to `main` is the only human decision actually being enforced,
and any claim of an enforced approval wait would be false.

### Multi-platform leg verified locally

The `linux/arm64` platform that the workflow publishes was built and run on this machine, so a
publish failure here is not a surprise waiting for CI:

```bash
docker buildx build --platform linux/arm64 -t iris-local:arm64-check .
docker image inspect iris-local:arm64-check --format '{{.Os}}/{{.Architecture}} size={{.Size}}'
# linux/arm64 size=128382377
docker run -d --name iris-arm64 -p 127.0.0.1:5002:5000 iris-local:arm64-check
curl http://127.0.0.1:5002/
# {"service":"iris-prediction","usage":"POST /predict with four measurements (release B)"}
curl -X POST http://127.0.0.1:5002/predict -H 'Content-Type: application/json' -d '{"measurements":[5.1,3.5,1.4,0.2]}'
# {"prediction":"setosa"}
```

`pip` resolves prebuilt `manylinux_2_27_aarch64` wheels for numpy, scipy and scikit-learn, so the
arm64 leg downloads rather than compiles; under QEMU the container needs roughly 30–60 s before the
first request is served, which is why `scripts/smoke.py` retries home readiness for 30 attempts
instead of failing on the first connection refusal.

### C2 A → B → A deployment (rehearsed locally)

The same commands were run against two digest-pinned images in `release-A/` and `release-B/`,
always with `-p iris-classroom`. `docker ps -a --filter label=com.docker.compose.project` showed a
single `iris` container in the single `iris-classroom` project throughout, confirming that a
rollback replaces the container instead of creating a second stack.

| Step | Folder | Digest | `GET /` usage message | Smoke |
| --- | --- | --- | --- | --- |
| Deploy A | `release-A` | `sha256:da13d7ee…` | `POST /predict with four measurements` | 3/3 pass |
| Deploy B | `release-B` | `sha256:ff2daf75…` | `POST /predict with four measurements (release B)` | 3/3 pass |
| Roll back | `release-A` | `sha256:da13d7ee…` | `POST /predict with four measurements` | 3/3 pass |

```bash
docker compose --env-file release.env -p iris-classroom config
docker compose --env-file release.env -p iris-classroom pull
docker compose --env-file release.env -p iris-classroom up -d --force-recreate
docker compose --env-file release.env -p iris-classroom ps
python3 smoke.py http://127.0.0.1:5000
curl http://127.0.0.1:5000/
```

This single-container replacement briefly interrupts service; it is not a zero-downtime rollout.

### C3 Release-decision diagram

```
 push to staging ──► build (publish digest) ──► load_test (smoke + gate)
                            │                        │
                            │                        ├─ fail ──► job red, release never runs
                            │                        └─ pass
                            ▼
 merge staging → main ──► build again on main (its own digest)
                            │
                            ▼
                    release job  (if main only)
                            │
                            ▼
                 GitHub environment "production"
                 required reviewer, self-review prevented, main only
                            │  human approves after reading commit,
                            │  build + smoke output, load report, intent
                            ▼
                  artifact approved-release-<SHA>
                  (compose.yaml, smoke.py, release.env, source-commit.txt)
                            │
                            ▼
              download → release-A/ → compose -p iris-classroom → smoke
                            │
              usage message changed → staging → main → approved-release-<SHA_B>
                            │
                            ▼
                     release-B/ → compose -p iris-classroom (same project)
                            │
                            ▼
                 rollback: enter release-A/ → pull + up → A's digest returns
```

### C4 Classroom limitations

* Required reviewers for an environment depend on the GitHub plan and repository visibility; if
  the rule cannot be enforced, the substitute is a **recorded external student review** naming
  reviewer, commit, digest, decision and reason — labelled as external, not as a GitHub-enforced wait.
* The load gate ran for 60 s against a development server on one laptop; the thresholds are
  classroom policy, not a production service agreement.
* Digest pinning proves identity and rollback, not zero downtime: `up -d --force-recreate` stops the
  old container before starting the new one.
* The GitHub-hosted runner is temporary, so `load_test` is a smoke-and-gate environment, not a
  persistent API. Nothing is deployed by the pipeline to a long-lived host.
* Multi-platform images publish `linux/arm64`, and that leg was built and served a valid prediction
  locally (see C2 above). The measurement host itself remains `x86_64`.

---

## Remaining steps that require your GitHub account

Everything below is a click in the GitHub UI, or a name you have to supply.

1. **Add the approval gate.** Settings → Environments → `production` → Required reviewers (a
   collaborator who is not you) → enable **Prevent self-review** → Deployment branches: `main`.
   Then re-run `ML Delivery` on `main` and confirm the release job shows *Waiting for approval*.
   Until then, use a recorded external review (reviewer, commit, digest, decision, reason).
2. **Publish the Version-A digest.** Actions → **ML Delivery** → **Run workflow** → branch
   `release-a` → Run. Record the resulting digest next to the Version-B digest above, then pull
   both and show that the older digest still answers with the original usage message:
   ```bash
   docker pull ghcr.io/ravindu57/ml_ops@sha256:<VERSION_A_DIGEST>
   docker run -d --name iris-share-a -p 127.0.0.1:5010:5000 ghcr.io/ravindu57/ml_ops@sha256:<VERSION_A_DIGEST>
   curl http://127.0.0.1:5010/     # original usage message
   ```
   Also verify the package is genuinely public in the container package settings
   (`https://github.com/users/ravindu57/packages/container/ml_ops` → Change visibility). The
   anonymous pulls above already succeed, so the repository's public visibility was inherited by
   the package; confirm it in the settings rather than assuming.
3. **Download the approved bundle** from run #1
   (`approved-release-e1efeae2507e96265053689f3e579bbcf566fde4`), extract it into `release-A/`,
   put the Version-A digest in `release.env`, then:
   ```bash
   docker rm -f iris-share          # free 127.0.0.1:5000 first
   docker compose --env-file release.env -p iris-classroom config
   docker compose --env-file release.env -p iris-classroom pull
   docker compose --env-file release.env -p iris-classroom up -d --force-recreate
   python3 smoke.py http://127.0.0.1:5000 && curl http://127.0.0.1:5000/
   ```
   Rollback = enter `release-A/` again and repeat `pull` + `up` with the same `-p iris-classroom`.
4. **Collect the other group's evidence**: their group name plus `docker pull`, `docker ps`,
   `docker logs` and a successful `POST /predict` using one of the digests above.
5. **Run Tests**: this repository was empty, so no such workflow exists. The README refers to a
   workflow kept from last week; import or create it separately if your group expects it. `ML
   Delivery` is deliberately a separate workflow and was never folded into it.
6. **Cleanup** after the final deployment evidence:
   ```bash
   docker rm -f iris-share
   docker compose --env-file release.env -p iris-classroom down
   ```
   Keep the retained bundles (`release-A/`, `release-B/`) and `reports/` for submission; do not
   delete images before the evidence has been reviewed.