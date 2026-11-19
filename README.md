<img src="assets/icon.svg" width="64" height="64" alt="">

# p2aieval sol6.2

Created in [T3 Code](https://t3.codes).

## Running

Requires Docker with Compose. From the repository root:

```bash
docker compose up --build -d --wait
```

Then open <http://localhost:5173>. The page reports API and database readiness.
Check the health endpoint directly with:

```bash
curl -fsS http://localhost:5173/api/health
# {"status":"ok","database":"ok"}
```

Only the frontend is published (on `127.0.0.1:5173`); it proxies `/api` to the
backend, which is reachable only inside the Compose network. Stop with
`docker compose down` (add `-v` to also delete the Postgres volume).
