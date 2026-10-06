# Week 14 extend an ML prediction service

**Goal:** extend the Iris container activity you completed last week so that a source change can produce a published, tested and approved release.

You will complete three connected practicals: automatically build and publish the Docker ML image with GitHub Actions; load test the application with Locust; and demonstrate continuous delivery through an approved release, student deployment and rollback. Students write, run, review and troubleshoot every step.

Keep your original `train.py` unchanged. Continue with your existing `app.py`, `requirements.txt` and working Dockerfile. The folder contains the original three project files in `original_project` for reference; do not overwrite your existing work blindly. `clues` contains planning templates, not completed solutions. No AWS account is needed.

## Reference materials

Use the official links below to solve your current problem.

| If you need to understand | Read these official sections |
| --- | --- |
| RUN, CMD, WORKDIR, COPY and EXPOSE; distinguish build instructions from startup configuration. | [Dockerfile reference](https://docs.docker.com/reference/dockerfile/) |
| Publishing images to GitHub Packages; adapt its trigger and tag to this activity. | [Publishing Docker images](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images) |
| Authentication, initial private visibility, image names and pulling by digest. | [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) |
| QEMU, Buildx and publishing linux/amd64 plus linux/arm64. | [Multi platform image with GitHub Actions](https://docs.docker.com/build/ci/github-actions/multi-platform/) |
| HttpUser, tasks, wait_time, task weights and response validation with catch_response. | [Writing a locustfile](https://docs.locust.io/en/stable/writing-a-locustfile.html) |
| Headless users, spawn rate, duration and controlling the process exit code. | [Running without the web UI](https://docs.locust.io/en/stable/running-without-web-ui.html) |
| on, permissions, jobs, needs, outputs, environment and if conditions. | [Workflow syntax for GitHub Actions](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax) |
| Create an environment, required reviewers, prevent self-review and selected branches. | [Managing environments for deployment](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/manage-environments) |
| image, ports and restart for a single service. | [Compose services](https://docs.docker.com/reference/compose-file/services/) |
| Project name and --env-file; use the same project name during rollback. | [docker compose](https://docs.docker.com/reference/cli/docker/compose/) |

**Input quick reference:** `measurements` is a JSON list of four numbers in this order: sepal length, sepal width, petal length, petal width, in centimetres. `GET /` gives service information; `POST /predict` accepts `{"measurements":[5.1,3.5,1.4,0.2]}` and returns HTTP 200 with `{"prediction":"setosa"}`. Two measurements must return HTTP 400 and an error message.

## Before class work starts

Start Docker Desktop, open a terminal and editor, and work in your existing project directory. Confirm Docker Compose and Python 3.12 are available. Use Git Bash for the shown commands on Windows; if your Python command is `python`, use it instead of `python3`.

Use a non-sensitive GitHub repository that your group is authorised to make public. Add group members as collaborators. Keep the previous workflow named **Run Tests** unchanged. Create a separate workflow named **ML Delivery** at `.github/workflows/ml-delivery.yml`. This guide assumes the default branch is `main`; substitute your actual default branch consistently if needed. The two workflows have separate outcomes; inspect both before merging.

```bash
docker version
docker compose version
python3 --version
git status
git branch --show-current
```

Commit or safely preserve local work before changing branches. Keep credentials, `.venv`, `__pycache__`, generated reports and local model files out of Git. Keep them out of the Docker build context where appropriate. Build-time training creates the model inside the image.

## Tasks

| Session | Your work | Final checkpoint |
| --- | --- | --- |
| A | Build and publish automatically; another group pulls your image | Two version identities and a successful handover |
| B | Measure local load; automate a staging smoke and load gate | Actual reports and a diagnosed failure |
| C | Approve releases A and B; deploy and roll back | Tested digest deployed and previous release restored |

## Practical A automatically build and publish the image

**Task:** replace an ad hoc image handover with a registry-based handover produced by a source push.

| Your work | Checkpoint |
| --- | --- |
| Revisit the working Dockerfile and draw source, image, registry and container | Identify where `iris_model.joblib` exists |
| Write and push the publishing workflow; investigate errors | Published image and source commit |
| Share the digest; another group pulls and runs the image | Their valid prediction without rebuilding |
| Publish a changed home usage message; retain both identities | Old digest still returns the old message |

### Workflow clues write it yourselves

1. Use your existing Dockerfile. Confirm it copies and installs dependencies, copies both Python files, runs `python train.py` during the build, and starts `python app.py` when a container starts. Preserve the training script.
2. Use the workflow planning template in `clues/workflow_plan.yml.txt`. Write the actual YAML yourself in `.github/workflows/ml-delivery.yml`; do not commit the unfinished template as an active workflow.
3. Trigger **ML Delivery** on pushes to `main` and `staging`. Optionally allow a manual run. Define a `build` job on `ubuntu-latest`, with `contents: read` and `packages: write` permissions and a sensible timeout.
4. Order its steps: checkout; choose a lowercase image name; configure QEMU and Buildx; log in to GHCR; build and publish. Use the official publishing and multi-platform examples. Suggested compatible majors for this activity are checkout v5, QEMU v3, Buildx v3, login v3 and build-push v6; `@vN` identifies an action release. These are classroom reference versions, not a claim about the newest releases.
5. Publish a multi-platform image for `linux/amd64,linux/arm64`. Name it `ghcr.io/owner/repository`, use a `sha-COMMIT` tag, and add the source repository label. Registry names must be lowercase. In Bash, `${GITHUB_REPOSITORY,,}` lowercases the repository value.
6. Authenticate with registry `ghcr.io`, username `${{ github.actor }}` and password `${{ secrets.GITHUB_TOKEN }}`. The last value refers to GitHub's workflow token; do not substitute a literal password.
7. Give the naming and build steps IDs. Write the image name to `$GITHUB_OUTPUT` and expose a job output named `image_ref` combining the lowercase name with the build action's `digest`: `name@sha256:...`. Later jobs must receive that exact output.
8. Commit and push the new workflow. Open Actions then ML Delivery. Inspect the first meaningful error if a step fails. Record the successful run link, source SHA, tag and full digest.
9. Open your account or organisation Packages page and the container package settings. Initial package visibility is private. Make only this authorised classroom package public for anonymous cross-group pulls. Repository visibility and package visibility are separate.
10. Give another group your full lowercase `name@sha256:...` reference. They must pull and run it without rebuilding or using your credentials. Change only the home `usage` message in `app.py`, keep `service` equal to `iris-prediction`, and publish a second version. Demonstrate both digests.

### Commands to try after writing the workflow

Replace OWNER, REPOSITORY and DIGEST with your actual values. DIGEST below is the hexadecimal part only; the command already contains `sha256:`. Copy the complete reference rather than its abbreviated display.

```bash
docker pull ghcr.io/OWNER/REPOSITORY@sha256:DIGEST
docker run -d --name iris-share -p 127.0.0.1:5000:5000 ghcr.io/OWNER/REPOSITORY@sha256:DIGEST
docker ps
docker logs iris-share
curl http://127.0.0.1:5000/
curl -i -X POST http://127.0.0.1:5000/predict -H 'Content-Type: application/json' -d '{"measurements":[5.1,3.5,1.4,0.2]}'
```

### Submit one result per group

1. Your Dockerfile, `.dockerignore` and workflow.
2. Successful Actions run link, source SHA, tag and digest for each version.
3. The other group's name and their pull, running container and valid prediction evidence.
4. A labelled diagram of source push, runner, registry and receiver; one paragraph explaining what each stores.
5. One error your group diagnosed, its evidence and the fix.

## Practical B load test the ML application with Locust

**Task:** measure how the published service behaves under a stated workload and make unacceptable observations stop the release path.

| Your work | Checkpoint |
| --- | --- |
| Write smoke checks and Locust tasks; run a short UI test | Correct status and response checks |
| Run the 10-user and 50-user tests; preserve reports | Actual measurements with controlled settings |
| Append the load job; push to staging | Exact image tested; reports retained |
| Compare evidence and submit | Defensible conclusion with limitations |

### Smoke check and Locust clues write them yourselves

1. Create a separate Python 3.12 virtual environment for Locust. Do not add Locust to the serving application's `requirements.txt`.
2. Use `clues/smoke_plan.py.txt` to plan `scripts/smoke.py`. Use Python's standard-library HTTP and JSON modules. Accept an optional base URL, defaulting to `http://127.0.0.1:5000`. Retry home readiness with bounded attempts and timeouts. Check home identity, a valid setosa prediction, and rejection of a two-number payload. Exit nonzero on any unexpected result; print success only after all checks pass.
3. Use `clues/locust_plan.py.txt` to plan `locustfile.py`. Define an `HttpUser` with `between(1, 2)` wait time, a prediction task of weight 3 and a home task of weight 1. Use the correct JSON payload and a request timeout. With `catch_response`, fail a sample when status or expected JSON content is wrong.
4. Add a quitting-event listener using the official headless example. Accept only at least 20 requests, failure ratio at most 0.01, and aggregate p95 at most 1000 ms. Handle a missing p95 or no traffic as failure. Set `environment.process_exit_code` to 0 for pass and 1 for fail. Optionally read the p95 limit from `P95_LIMIT_MS` with default 1000.
5. These are predeclared classroom thresholds, not a production service agreement. Do not quietly loosen them to obtain a green result.
6. Run the published digest from A. Pass smoke checks before starting load. Open Locust at port 8089; its target API is port 5000. Stop the UI test and close Locust before starting the controlled headless runs.
7. Keep image digest, duration, wait time and task weights unchanged while comparing user counts. Record architecture and test conditions. Complete B6 by temporarily using two measurements, observing the failure and restoring the valid input.

### Commands to try after writing the test files

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install "locust>=2.32,<3"
python scripts/smoke.py
locust -f locustfile.py --host http://127.0.0.1:5000
```

Windows Git Bash activation is `source .venv/Scripts/activate`. In PowerShell use `.venv\Scripts\Activate.ps1`, or invoke the virtual environment's Python directly if activation is unavailable. The version range permits compatible 2.x updates; a pinned rehearsed version gives stronger repeatability.

```bash
mkdir -p reports
locust -f locustfile.py --headless --host http://127.0.0.1:5000 -u 10 -r 2 -t 60s --stop-timeout 5 --csv reports/baseline --html reports/baseline.html
locust -f locustfile.py --headless --host http://127.0.0.1:5000 -u 50 -r 5 -t 60s --stop-timeout 5 --csv reports/comparison --html reports/comparison.html
```

| Metric | 10 users | 50 users |
| --- | --- | --- |
| Requests | Record actual value | Record actual value |
| Failures and failure percent | Record actual value | Record actual value |
| Mean response time ms | Record actual value | Record actual value |
| Median response time ms | Record actual value | Record actual value |
| p95 response time ms | Record actual value | Record actual value |
| Requests per second | Record actual value | Record actual value |
| Gate result | Pass or fail with reason | Pass or fail with reason |

### Staging workflow clues

Append a `load_test` job under `jobs`, alongside `build`, in the same workflow. Use `needs: build`, obtain `image_ref` from the build job output, and grant package read access. On a fresh Ubuntu runner, check out the source, set up Python 3.12, install Locust and log in to GHCR. Pull that exact digest and start a named staging container. Run smoke, then a 20-user, 5-users-per-second, 60-second headless test with CSV and HTML reports. Upload reports even after failure; show container logs and remove the staging container in cleanup steps that always run. Do not use `continue-on-error` to conceal a failed gate.

Create the `staging` branch from up-to-date main after preserving your work. Stage only the intended files, commit and push. If staging already exists, switch to it instead of creating it again. In GitHub Actions inspect the build output, smoke output, load gate, report artifact and cleanup. The runner is temporary; this is a test environment, not a persistent hosted API.

```bash
git switch main
git pull --ff-only
git switch -c staging
git add .github/workflows/ml-delivery.yml scripts/smoke.py locustfile.py
git commit -m "Add staging smoke and load checks"
git push -u origin staging
```

### Submit one result per group

1. Smoke and Locust files, with annotations explaining their response checks and gate.
2. Baseline and comparison reports, completed metric table, image digest and test settings.
3. Failed-payload evidence, diagnosis and restored-run evidence.
4. Staging run link and report artifact; one paragraph explaining whether the hypothesis was supported.

## Practical C continuous delivery of the ML application

**Task:** produce an approved release from verified content, deploy it on your computer, and restore the previous release using its retained identity.

| Your work | Checkpoint |
| --- | --- |
| Create Compose definition, environment gate and release job | Main waits for student approval |
| Review, download and deploy release A | Exact tested digest and smoke success |
| Change the usage message; publish, approve and deploy B | Same service now shows B |
| Peer review, cleanup and submit | Complete evidence and limitations |

### Delivery clues write it yourselves

1. Create `compose.yaml` using `clues/compose_plan.yaml.txt` and the Compose service reference. Define one service named `iris`. Obtain its `image` from a required `IMAGE_REF` interpolation variable, containing the full digest reference. Do not add a local build. Map host loopback and configurable `HOST_PORT` (default 5000) to container port 5000; choose `unless-stopped` as the restart policy.
2. In repository Settings then Environments, create `production`. Configure an eligible student collaborator as required reviewer, prevent self-review and allow main. Required-reviewer availability depends on GitHub plan and repository visibility; check the official reference. A public non-sensitive classroom repository supports this path on current common plans. An environment name alone does not enforce approval.
3. If enforced reviewers are unavailable, use a recorded external student review before manual deployment. Record reviewer, commit, digest, decision and reason. Label it external approval; do not present it as a GitHub-enforced wait.
4. Append a sibling `release` job with dependencies on both `build` and `load_test`. Restrict it to `refs/heads/main` and associate it with the `production` environment. Pass the build job's exact image reference and the source SHA into the job.
5. After approval, prepare `release/` containing `compose.yaml`, a copy of the smoke script named `smoke.py`, `release.env` with `IMAGE_REF` and `HOST_PORT`, and `source-commit.txt`. Upload that folder as `approved-release-COMMIT`. Do not place secrets in the bundle.
6. Commit your changes on staging and push. Inspect both **Run Tests** and **ML Delivery** before creating and merging a staging-to-main pull request. Main rebuilds and rechecks its own image. Its successful load gate must precede release approval; the staging image is not silently substituted.
7. The designated student reviewer inspects commit, build and smoke outputs, the measured load report and release intent. Approve only an understood acceptable release. Download and extract the approved bundle into a retained folder such as `release-A`; work in the folder containing `compose.yaml` and `release.env`.
8. Before deployment, stop and remove the named earlier lab container if it occupies the port. Use the same Compose project name `iris-classroom` for every release and rollback. Validate configuration, pull the digest, start the service and run smoke. Save A unchanged.
9. Change only the home usage message to mark B; keep the service identity and `train.py` unchanged. Commit, push, test, review and approve B. Keep its bundle in `release-B`. Deploy B using the same project name and record its usage response and digest.
10. To roll back, enter the retained A folder and repeat pull and up using the same project name. Smoke must pass and the home usage message must return to A. This single-container replacement can interrupt service; it is not a zero-downtime rollout.

### Commands to try inside an approved release folder

```bash
docker compose --env-file release.env -p iris-classroom config
docker compose --env-file release.env -p iris-classroom pull
docker compose --env-file release.env -p iris-classroom up -d --force-recreate
docker compose --env-file release.env -p iris-classroom ps
docker compose --env-file release.env -p iris-classroom logs iris
python3 smoke.py http://127.0.0.1:5000
curl http://127.0.0.1:5000/
```

If you select host port 5001 in `release.env`, use port 5001 in smoke and curl URLs. Deploy A and B from their own retained folders. For rollback, enter A's folder and repeat `config`, `pull`, `up`, `ps`, smoke and curl with the same project name. Do not rebuild locally or replace the digest with `latest`.

### Submit one result per group

1. Completed Compose definition and cumulative workflow.
2. Staging release-skip evidence and main approval evidence, or the clearly labelled external review record.
3. Retained release A and B bundles, source SHAs and digests.
4. A-to-B-to-A deployment evidence, home responses and smoke results.
5. A labelled release-decision diagram and an explanation of classroom limitations.

## Cleanup

After recording handover evidence, stop and remove only your named standalone lab container. After the final deployment evidence, run the following from the active release folder. Retain the approved bundles and reports for submission.

```bash
docker compose --env-file release.env -p iris-classroom down
```

Do not delete images before evidence review. Never use a broad cleanup command on shared computers.

## When something does not work

1. For YAML errors, check spaces, sibling job indentation and the first invalid line. A file in `clues` is a plan, not a runnable workflow.
2. For publication permission errors, inspect `packages: write`, GHCR login, package ownership and repository access. Lowercase the registry path. Do not commit a token.
3. For anonymous pull failures, inspect package visibility separately from repository visibility. Check the full digest and published platforms.
4. For a stopped container or readiness failure, use `docker ps -a` and the named container's logs. Confirm build-time training generated the model and the expected port is used.
5. For HTTP 400, inspect the `measurements` key and its four numeric values. A deliberately invalid request should be rejected.
6. For Locust failures with HTTP 200, inspect the JSON assertion. The web UI at 8089 is not the target API.
7. For a failed performance gate, read the actual sample count, failure ratio and p95. Keep the report and investigate before changing the declared policy.
8. For immediate release execution, inspect the actual required-reviewer rule. Naming an environment does not require a human by itself.
9. For rollback creating a second stack, check that both releases use `-p iris-classroom`. Verify the active folder, digest and port.