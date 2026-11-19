<img src="assets/icon.svg" width="64" height="64" alt="">

# p2aieval sol6.2

Created in [T3 Code](https://t3.codes).

## Running

Requires Docker with Compose. From the repository root:

```bash
docker compose up --build -d --wait
```

Then open <http://localhost:5173>. Each tab claims a seat in the next open
waiting session and shows "Waiting for other participants". The seat token is
kept per tab in session storage, so a refresh reclaims the same seat; **Leave**
releases it immediately. Check the health endpoint with:

```bash
curl -fsS http://localhost:5173/api/health
# {"status":"ok","database":"ok"}
```

Only the frontend is published (on `127.0.0.1:5173`); it proxies `/api` to the
backend, which is reachable only inside the Compose network. Stop with
`docker compose down` (add `-v` to also delete the Postgres volume).

## Configuration

`config.yml` sets the condition (`humans`/`ai`: 2/1 by default, or 3/0, or 1/2)
and the chat and vote durations. The backend reads it once at startup, so after
editing, recreate the backend:

```bash
docker compose up -d --force-recreate backend
```

Restarting the backend ends any unfinished run (marked `abandoned`, logs kept),
so start a fresh run afterwards.

## Inspecting the log

Tables (`sessions`, `participants`, `experiment_events`) are created at backend
startup. Query them with SQL:

```bash
docker compose exec db psql -U experiment -d experiment \
  -c "SELECT seq, ts, event_type, actor_id, payload FROM experiment_events ORDER BY session_id, seq"
```

or fetch one run's ordered events from inside the Compose network:

```bash
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/internal/sessions/<session_id>/events').read().decode())"
```

The log contains roles, so `/internal/...` is not proxied to the browser.
