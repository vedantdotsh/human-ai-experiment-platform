<img src="assets/icon.svg" width="72" height="72" alt="Three linked participants labelled A, B and C">

# Three-Player Decision Maker Experiment

A local web experiment. Three players (Player A, B and C) chat for two timed rounds,
vote after each round, and the votes pick a **Decision Maker**. Depending on the
condition, some of the seats are people (each in their own browser tab) and some are
AI players. The server owns the state and the clock; the browser only displays and
submits. Everything runs locally from one Docker Compose command.

- **Stack:** React + TypeScript (Vite) frontend, FastAPI backend, Postgres 16, WebSockets.
- **Blind by design:** a player never sees player types or how many AI seats exist, and
  learns their own label ("Player A/B/C") only when the run starts.
- **Auditable:** every accepted message, ballot, phase change, join and disconnect is
  written to an ordered, timestamped Postgres log.

## Run it (one command)

Requires Docker with Compose. From the repository root:

```bash
docker compose up --build -d --wait
```

That builds and starts Postgres, the backend and the frontend, and returns when all
three are healthy. Then open <http://localhost:5173>. Check the API with:

```bash
curl -fsS http://localhost:5173/api/health
# {"status":"ok","database":"ok"}
```

Stop with `docker compose down`. Add `-v` (`docker compose down -v`) to also delete
the database volume and start completely clean. Only the frontend is published
(on `127.0.0.1:5173`); the backend and database are reachable only inside the
Compose network.

AI players work without any setup (scripted lines). To let them use a language model,
see [AI players and the API key](#ai-players-and-the-api-key).

## The tab demo

Open the app in as many **separate tabs** as the current condition needs; each tab is
one participant (its seat token lives in that tab's session storage).

1. A tab claims a random open human seat in the next waiting run and shows only
   "Waiting for other participants", whoever has or has not arrived.
2. When every human seat is taken and connected, the run starts after a random delay
   (`start_delay_*_seconds`). Each player now sees their own label.
3. **Round 1 discussion** (`chat_seconds`, default 60 s) → **Round 1 voting**
   (`vote_seconds`, default 20 s) → **Round 2 discussion** → **Round 2 voting** →
   **Results**. Chat is open only during discussion; round 1 chat stays visible in
   round 2.
4. In voting each player casts one final ballot for one of the *other* two players
   (see `allow_self_vote`). Only the number of ballots cast is shown. Voting closes
   early once all three seats have voted; missing ballots count as abstentions at the
   deadline. After round 1 everyone sees the per-player totals.
5. The Decision Maker is the player with the most round 2 votes; a tie is broken by
   round 1 votes, and a remaining tie by a random pick stored with the run. Players
   see the winner and the totals, never individual ballots.

Refreshing a tab reclaims the same seat and shows the same state and result.
**Leave** (waiting room only) frees the seat at once; closing a waiting tab frees it
after `waiting_grace_seconds`. A player who disconnects mid-run keeps their seat and
the run carries on. The server advances every phase even with all tabs closed.

## Conditions and how to switch

The condition is set by `humans` and `ai` in [`config.yml`](config.yml). The shipped
default is **2 humans + 1 AI**.

| Condition | `humans` | `ai` | Tabs to open |
| --- | ---: | ---: | ---: |
| 2 humans + 1 AI (default) | 2 | 1 | 2 |
| 3 humans | 3 | 0 | 3 |
| 1 human + 2 AI | 1 | 2 | 1 |

To switch, edit those two lines in `config.yml`, then reload the config by
recreating the backend:

```bash
docker compose up -d --force-recreate backend
```

The backend reads `config.yml` once at startup, so this command is required after any
change. (Use `--force-recreate`, not plain `restart`: the file is bind-mounted and an
editor that replaces the file can leave a restarted container looking at the old one.)
Any run still in progress is ended; see [Restarts](#restarts). Seat roles are shuffled
for every run, so the same condition gives a different seat layout each time.

Other settings in `config.yml`:

| Key | Default | Meaning |
| --- | --- | --- |
| `chat_seconds` | 60 | Length of each discussion |
| `vote_seconds` | 20 | Length of each voting window |
| `start_delay_min_seconds` / `start_delay_max_seconds` | 3 / 8 | Random wait before the run starts once everyone is connected |
| `waiting_grace_seconds` | 5 | How long a waiting seat survives a closed socket (lets a refresh reconnect) |
| `allow_self_vote` | false | Whether a player may vote for themselves |
| `ai_model` | `mistral-small-latest` | Model the AI players use when a key is set |
| `ai_call_timeout_seconds` | 8 | Longest a model call may take before the scripted fallback |

For a quick demo shorten the two durations and the start delay (for example 15, 10
and 2), recreate the backend, and restore the defaults afterwards.

## AI players and the API key

AI seats chat two or three times per discussion and vote once per round, at random
times inside the phase, with a typing-like delay before each message. They use the
same validation and persistence as human actions.

They call [Mistral](https://console.mistral.ai/api-keys) from the backend only. Put the
key in a git-ignored `.env` file next to `compose.yaml` (copy `.env.example`):

```bash
cp .env.example .env        # then set MISTRAL_API_KEY=...
docker compose up -d --force-recreate backend
```

Without a key, or when a call fails, times out or returns unusable text, the AI falls
back to a large pool of varied scripted lines and a ballot weighted toward who has
spoken. The model's reply is checked only for form (one short line, not a repeat) and
for a plain admission of being an AI, which is replaced by a scripted line; how it
answers "are you a bot?" is left to the prompt. With `allow_self_vote: false` the AI
never votes for itself, including in the fallback. Every AI action records its source
(`llm` or `scripted`) and any fallback reason in the event log. The prompts and model
are listed in [`ai_prompts.md`](ai_prompts.md).

## Event log

Postgres keeps three tables, created at backend startup: `sessions` (one row per run,
including its config snapshot and persisted winner), `participants` (seats, with the
private role) and `experiment_events` (the ordered log). Previous runs stay queryable.

**1. Find a session** (newest first):

```bash
docker compose exec db psql -U experiment -d experiment -c \
  "SELECT id, status, phase, config->>'humans' AS humans, config->>'ai' AS ai, winner_slot, created_at FROM sessions ORDER BY created_at DESC LIMIT 5"
```

**2. Read its events in SQL** (replace `<session_id>`):

```bash
docker compose exec db psql -U experiment -d experiment -c \
  "SELECT e.seq, e.ts, e.phase_seq, e.event_type, p.slot, p.role, e.payload FROM experiment_events e LEFT JOIN participants p ON p.id = e.actor_id WHERE e.session_id = '<session_id>' ORDER BY e.seq"
```

**3. Or as ordered JSON** from inside the Compose network:

```bash
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/internal/sessions/<session_id>/events').read().decode())"
```

Event types are `message`, `vote`, `phase_change`, `join` and `disconnect`; `seq` is
gap-free per run and `ts` is server UTC. Rejected attempts are never logged. The log
and the `participants` table contain roles and join/disconnect records, so
`/internal/...` is deliberately not proxied to browsers (through the frontend it
returns 404) and the backend port is unpublished.

## Tests

Three automated tests cover the Decision Maker rules: a clear round 2 winner, a round 2
tie settled by round 1, and a tie after round 1 settled by a controlled random pick.

```bash
docker compose exec -T backend python -m unittest discover -s tests -v
```

Everything else is checked by hand; each build step's evidence is in
[`reviews/`](reviews/).

## Restarts

Restarting or recreating the backend ends every unfinished run: on startup each is
marked `abandoned` and a `phase_change` event records it, and the logs are kept.
Players in those runs see "This run is no longer available". Seat tokens and timers
live in the backend's memory, so runs cannot be resumed; **start a fresh run** by
opening a new tab (or choosing "Join a new run").

## Design decisions and tradeoffs

The choices below come from the build plan ([`plan.md`](plan.md)); the right-hand column
is the reason each was made.

| Chosen | Alternative | Why |
| --- | --- | --- |
| Automatic join, per-tab seat, shuffled roles, generic waiting text, and randomized start | Join codes, fixed roles, or visible waiting counts | Keeps the tab-based demo simple and avoids exposing the participant mix through labels, counts, or an immediate start. |
| Server-owned phases and deadlines with browser display | Browser-controlled timers | All participants follow the same deadlines and the run can continue through a disconnect. |
| Startup table creation and a single-process in-memory lock per session | Migrations and database row locks or Redis-backed coordination | Fits one local backend process. Several processes would need Redis or database row locks to coordinate shared state, plus a way to coordinate sockets and timers. |
| End unfinished runs on restart while preserving logs | Recover live runs after restart | Keeps runtime recovery out of scope and retains the audit trail. |
| Final ballots, early close, and abstentions. Vote 2 decides, then vote 1, then a stored random pick. | Revisable ballots, a fixed full window, or another voting round to settle ties | Keeps results reproducible and lets a run finish on time with missing votes. |
| LLM-written chat and chat-based votes, with scripted fallback | Scripted players for every run | Adapts to the discussion while keeping the experiment runnable through provider failures or without a key. |
| SQL and an internal JSON endpoint | A researcher dashboard or browser log | Gives the operator inspectable data without exposing join and disconnect records to participants. |
| Three automated winner tests and manual checks for the rest | Automated browser and integration suites | Concentrates the four-hour test budget on the outcome rules while preserving manual end-to-end verification. |
| Tab-based enrollment with no participant identity | Participant identification to enforce one seat per person | The demo needs several tabs on one machine. A person who controls several seats in one run can work out the AI seats from when the run starts, which is accepted as out of scope. A real participant holds one seat, and preventing this needs participant identity. |
| Start a few random seconds after the last human connects | A scheduled start time | A participant who waits a long time can tell that at least one other player is a human, because the run starts only once the humans arrive. A scheduled start time would hide this in a real deployment, but the tab demo needs prompt starts. |
| Show per-player vote totals after round 1 and at the end | Show only the winner | A voter can sometimes work out other ballots by subtracting their own vote from the totals, which is accepted. Showing only the winner would hide this, but the totals give round 2 something to discuss. |
| No self votes by default (`allow_self_vote: false`) | Allow players to vote for themselves | I chose no self votes because it forces players to persuade each other and the alternative let everyone pick themselves and leave the result to chance. |

A few of these deserve more explanation:

- **One backend process, in-memory locks.** Correctness of seat claims, ballots and
  event numbering comes from one lock per run plus a short process-level lock for
  "find or create the next open session". That is simple and enough for a local demo,
  and it is why the backend must run as a single process (see below). Database
  state and its events are committed together, then broadcast, so a socket never sees
  something the log does not hold.
- **The server is the clock.** Deadlines are stored with the run and enforced by the
  server; browsers only display a countdown from server time. That is what lets a run
  finish through a disconnect and makes every player's window identical.
- **Totals reveal a little.** Showing per-player totals means a voter can sometimes
  infer others' ballots by subtracting their own. It was accepted because the totals
  give round 2 something to discuss and the alternative (winner only) removes that.
- **Blindness over convenience.** Join responses carry only an opaque token, labels
  appear only at the start, chat numbers count chat only, and seats are drawn at
  random, all so a browser cannot work out who is an AI from field names, counts or
  ordering. The costs are in the limitations below.

## What several backend processes would need

The backend is built to run as exactly one process. Its coordination state lives in
that process's memory: the per-run locks, the seat-token map, the registry of open
WebSockets, the phase timers and the AI schedulers. With several processes behind a
load balancer each would hold its own copy, and things would break:

- **Locks.** Two processes could both claim the last seat, accept a second ballot, or
  hand out the same event sequence number. The in-memory locks would have to become
  shared: Redis locks, or Postgres row locks / advisory locks (`SELECT ... FOR UPDATE`,
  `pg_advisory_xact_lock`) around seat claims, messages, votes and phase changes. The
  "find or create the next open session" step would need the same.
- **Seat tokens** would have to be stored somewhere every process can read (Redis or a
  table), not in one process's dictionary.
- **Sockets.** A message accepted by one process must reach browsers connected to
  another, so broadcasts need a shared channel such as Redis pub/sub (or Postgres
  `LISTEN/NOTIFY`).
- **Timers and AI turns.** A phase must advance exactly once. Timers and AI schedulers
  would need a single owner per run (leader election or a job queue) instead of every
  process running its own.

Redis (locks, token store, pub/sub) plus row locks for the log would cover all of it;
that is a larger system than this project needs.

## Known limitations

- **Several seats held by one person.** Enrollment is tab-based with no participant
  identity, so someone who opens several tabs in one run can tell when it starts and
  work out which seats are AI. The experiment assumes one seat per participant in a
  real session; preventing this would need participant identification, which is out
  of scope.
- **Long waits reveal a human.** The run starts a few random seconds after the last
  human connects, so a participant who waits a long time can tell that at least one
  other player is a human. A scheduled start time would hide this in a real
  deployment.
- **A determined participant may still catch the AI.** The AI is made hard to tell
  apart (short casual messages, typing-like delays, no admission, varied answers to
  direct questions), but someone who probes it, or who studies its timing, brevity
  and style across a run, may still work out which seat is the AI.
- **Vote totals leak a little.** A voter can sometimes work out other ballots by
  subtracting their own vote from the totals.
- **Local demo, not a deployment.** One backend process; the frontend is the Vite dev
  server; no authentication; default database credentials; the internal log endpoint
  is protected only by network isolation. The socket token travels in the WebSocket
  query string, so it appears in the backend's access log (tokens last only until the
  backend restarts).
- **Seats are per tab.** A closed tab cannot reclaim its seat (its session storage is
  gone), so a player who closes a running tab cannot rejoin that run; refresh is fine.
  After a run ends a tab stays on the results; open a new tab for another run.
- **Restarts end runs.** See [Restarts](#restarts).
- **AI quality depends on the provider.** Without a key, or when calls fail, the AI
  uses scripted lines, which are weaker than model output. One provider and model are
  supported.

## Repository layout

```text
compose.yaml  config.yml  .env.example  plan.md  ai_prompts.md  reviews/
backend/app/   session/ experiment/ messaging/ voting/ ai/ realtime/ event_log/
backend/tests/ winner tests
frontend/src/  app/ session/ experiment/ messaging/ voting/ results/ realtime/
```
