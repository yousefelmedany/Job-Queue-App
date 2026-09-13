# Background Job Queue

React submits jobs to FastAPI, which saves them in PostgreSQL and immediately returns a job ID. A separate worker processes them while the client polls `GET /jobs/{id}` for updates.

## Run

Create the local database secret once:

```bash
mkdir -p .secrets
python3 -c 'import secrets,pathlib; p=pathlib.Path(".secrets/db_password"); p.exists() or p.write_text(secrets.token_urlsafe(36)+"\n"); p.chmod(0o600)'
docker compose up --build
```

Open the UI at http://localhost:8080 or the API docs at http://localhost:8000/docs. Keep the generated `.secrets/db_password` file for future runs: replacing it does not automatically change the password in an existing PostgreSQL volume. The file is Git-ignored and mounted as a Compose secret.

## Example

```bash
curl -X POST http://localhost:8000/jobs \
  -H 'Content-Type: application/json' \
  -d '{"idempotency_key":"demo-1","payload":{"duration":2,"fail_until_attempt":2},"priority":1,"max_attempts":3}'

curl http://localhost:8000/jobs/<returned-id>
```

The first call returns HTTP 202 with `queued` status. Reusing an idempotency key returns the same job. **Clear history** in the UI only clears this browser's saved job list; it does not delete database rows.

## How jobs work

- **States:** `queued → running → succeeded`. On failure, a job returns to `queued` if attempts remain; otherwise it becomes `failed`.
- **Retries:** `attempt_count` increases when the worker claims a job. After failure, `available_at` delays the next attempt by 5 seconds, then 10, 20, and so on. The worker can process other jobs during this delay.
- **Idempotency:** PostgreSQL has a unique constraint on `idempotency_key`. The API uses `INSERT ... ON CONFLICT DO NOTHING` and returns the existing row on conflict, including concurrent submissions.
- **Crash recovery:** Before claiming work, the worker finds jobs still `running` more than 60 seconds after `locked_at`. It records a timeout error and retries them if attempts remain, or marks them `failed`. A restarted worker or another running worker performs this recovery.
- **Claiming:** The worker selects an available job with `FOR UPDATE SKIP LOCKED` and marks it `running` in the same transaction. It orders by priority descending, then creation time ascending.

## Assumptions and limitations

- Jobs are simulated with `time.sleep(duration)`; `fail_until_attempt` makes failures deterministic. The client supplies duration and failure threshold in `payload`, and supplies `max_attempts` and `idempotency_key` alongside it in the same request.
- The first failed attempt waits 5 seconds before retry. Each later failed attempt doubles the delay, until the job succeeds or reaches `max_attempts`.
- The worker runs independently of FastAPI and accesses PostgreSQL directly. Job execution is asynchronous from the client's HTTP request, although one worker executes jobs sequentially.
- Priorities are `0` (normal), `1` (high), and `2` (urgent). The highest-priority **queued** job is claimed first; if priorities match, the oldest is claimed first. A running job is not preempted.
- The worker and PostgreSQL containers have no published ports. The API and frontend have published ports for this local demo.
- PostgreSQL stores data in the `postgres_data` named Docker volume, mounted from Docker's storage on the host. It survives container restarts.
- A crashed attempt counts toward `max_attempts`. Real jobs with variable runtimes need a renewable lease or heartbeat, and external side effects must be idempotent because a crash can cause a retry after the side effect occurred.
