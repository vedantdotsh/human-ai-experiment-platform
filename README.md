<img src="assets/icon.svg" width="64" height="64" alt="">

# p2aieval sol6.2

Created in [T3 Code](https://t3.codes).

## Running

Requires Docker with Compose. From the repository root:

```bash
docker compose up --build -d --wait
```

Then open <http://localhost:5173> in as many tabs as the condition needs (three
for `humans: 3`; two for the default 2 humans + 1 AI). Each tab claims a seat in
the next open waiting session and shows only "Waiting for other participants".
The seat token is kept per tab in session storage, so a refresh reclaims the same
seat; **Leave** releases it immediately, and closing a waiting tab releases its
seat after `waiting_grace_seconds`. Once every human is connected the run starts
after a random delay, and each player first learns their own label ("Player A/B/C")
at that moment. The run then goes: round 1 discussion, round 1 voting, round 2
discussion, round 2 voting, results. The server owns the clock, so it advances
even with every tab closed; a player who disconnects mid-run keeps their seat and
the run continues. Chat is open only during discussion.

During each voting phase a player casts one ballot for one of the other two
players; with `allow_self_vote: true` in `config.yml` they may also vote for
themselves (the server rejects a self vote otherwise, and the page only offers
the allowed choices). A ballot is final, only the number of ballots cast is
shown while voting, and voting closes early once all three ballots are in;
missing ballots count as abstentions at the deadline. After vote 1 every player
sees the per-player totals. The Decision Maker is the player with the most vote 2
ballots; ties are broken by vote 1 totals, and a remaining tie by a random pick
stored with the run. Players see the winner and the per-player totals, never
individual ballots. A refresh after the run still shows the stored result.

AI seats chat two or three times per discussion and vote once per round, at random
times inside the phase, with a typing-like delay before each message; voting closes
early once every seat, AI included, has voted. They use the same validation and
persistence as human actions.
For a quick demo, shorten `chat_seconds`, `vote_seconds` and the start delay in
`config.yml`. Check the health endpoint with:

```bash
curl -fsS http://localhost:5173/api/health
# {"status":"ok","database":"ok"}
```

Only the frontend is published (on `127.0.0.1:5173`); it proxies `/api` to the
backend, which is reachable only inside the Compose network. Stop with
`docker compose down` (add `-v` to also delete the Postgres volume).

## AI players and the API key

AI seats call Mistral from the backend only. Put the key in a `.env` file next to
`compose.yaml` (copy `.env.example`; `.env` is git-ignored and never committed):

```bash
cp .env.example .env   # then set MISTRAL_API_KEY=...
docker compose up -d --force-recreate backend
```

The model and call timeout are `ai_model` and `ai_call_timeout_seconds` in
`config.yml`. Without a key, or when a call fails, times out, or returns unusable
text, the AI falls back to varied scripted lines and a ballot weighted toward who
has spoken; each fallback and its reason is recorded in the event log. Model output
is checked before posting only for form (one short line, not a repeat) and for a plain
admission of being an AI, which is replaced by a scripted line. Questions such as
"are you a bot?" are answered by the model in its own words, in context. The AI
never votes for itself unless `allow_self_vote` is true, including in the scripted
fallback. Prompts and the model are listed in `ai_prompts.md`.

## Configuration

`config.yml` sets the condition (`humans`/`ai`: 2/1 by default, or 3/0, or 1/2)
and the chat and vote durations. The backend reads it once at startup, so after
editing, recreate the backend:

```bash
docker compose up -d --force-recreate backend
```

Restarting the backend ends any unfinished run (marked `abandoned`, logs kept),
so start a fresh run afterwards.

## Tests

Three automated tests cover the Decision Maker rules (clear vote 2 winner, vote 2
tie settled by vote 1, and a tie after vote 1 settled by a controlled random pick).
Run them in the backend container:

```bash
docker compose exec -T backend python -m unittest discover -s tests -v
```

Everything else is checked by hand.

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

## Known limitations

- **Several seats held by one person.** Enrollment is tab-based with no participant
  identity, so someone who opens several tabs in one run can tell when it starts
  and work out which seats are AI. The experiment assumes one seat per participant
  in a real session; preventing this would need participant identification, which
  is out of scope.
- **Long waits reveal a human.** The run starts a few random seconds after the last
  human connects, so a participant who waits a long time can tell that at least one
  other player is a human. A scheduled start time would hide this in a real
  deployment.
- **A determined participant may still catch the AI.** The AI is made hard to tell
  apart (short casual messages, typing-like delays, no admission, varied answers to
  direct questions), but someone who probes it, or who studies its timing, brevity
  and style across a run, may still work out which seat is the AI.
