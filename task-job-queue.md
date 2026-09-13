# Take-Home Task — Background Job Queue Service

You have **24 hours** from receipt to submit. Aim for **4-5 focused hours** — leave notes in your README for anything you didn't get to. You're welcome to use AI tools as you normally would; be ready to walk us through your decisions afterward.

## The task
**Tech stack: your choice.** Use whatever language, framework, and database you're most comfortable with.

Build a background job queue: clients submit a job (e.g. "resize this image," "send this email" — pick a concrete, simple job type you can meaningfully simulate, like sleeping for N seconds and writing a result), and a worker process picks it up and executes it asynchronously.

**Requirements:**
- `POST /jobs` — submit a job with a payload; returns immediately with a job ID and status `queued`
- `GET /jobs/{id}` — returns the job's current status (`queued`, `running`, `succeeded`, `failed`) and result/error if finished
- A worker (can run in the same process or a separate one — your choice, explain it) that picks up queued jobs and executes them
- Retry with backoff: a failed job should be retried a limited number of times (e.g. 3) with increasing delay between attempts, before being marked permanently `failed`
- Idempotency: submitting a job with the same client-supplied idempotency key twice should not create two jobs — the second submission should return the existing job

**Harder addition:**
- Handle a worker crash mid-job: if a job is stuck in `running` for longer than a reasonable timeout, it should be recoverable (retried or marked failed) rather than stuck forever
- Support job priority: a way to mark some jobs as higher priority so they're picked up before lower-priority queued jobs, even if submitted later

**Time-saving allowances (use these to stay in scope):**
- The "job" itself can be entirely simulated (e.g. `time.sleep()` plus a coin-flip failure for testing retries) — no need for real image processing or email sending
- A single worker is fine — no need to build multi-worker coordination unless you want to
- No need for a real message broker (RabbitMQ, SQS, etc.) — a database-backed queue (polling a table) is a legitimate, expected approach at this scale

**Deliverables:**
- Source code with a `README.md`: how jobs move through states, your retry/backoff strategy, how idempotency is enforced, and how you handled the stuck-worker recovery case
- Note any assumptions you made

## Submission
Push to a private repo and share access, or send a zip. Include run instructions (Docker Compose preferred if applicable).

## Resources
- FastAPI: https://fastapi.tiangolo.com/
- PostgreSQL: https://www.postgresql.org/docs/