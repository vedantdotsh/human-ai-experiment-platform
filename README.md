<img src="assets/icon.svg" width="72" height="72" alt="Three linked participants labelled A, B and C">

# Three-Player Decision Maker Experiment

I built this local experiment to see how a group chooses a Decision Maker. Three
players (A, B and C) chat for two timed rounds and vote after each one. The condition
sets how many seats go to people and how many go to AI. Each person uses their own
browser tab. The FastAPI server keeps the state and the clock. The React and
TypeScript frontend runs in Vite and uses WebSockets to show updates and send actions.

The app never sends player types or the number of AI seats to a browser. See
[Known limitations](#known-limitations) for what players can still work out.

## Run locally

Start Docker Desktop (or Docker Engine) with Compose v2. Run the commands in Bash
or Git Bash from the repository root:

```bash
docker compose up --build -d --wait
```

The command builds and starts the app with Postgres 16 and waits for all services
to be healthy. Open <http://localhost:5173>. To check the API, run the command below.
In Windows PowerShell, use `curl.exe` instead of `curl`.

```bash
curl -fsS http://localhost:5173/api/health
# {"status":"ok","database":"ok"}
```

Use `docker compose down` to stop the app. Use `docker compose down -v` if you also
want to delete the database volume and start clean. Compose publishes only the
frontend on `127.0.0.1:5173`. The backend and database stay on the Compose network.

The AI players use scripted lines without any extra setup. To use a language model,
see [AI players and the API key](#ai-players-and-the-api-key).

## Try a run

Open a fresh tab for each human seat in the current condition. Don't duplicate a
tab: that copies its seat token from session storage and gives you the same seat.

1. Each tab claims a random open human seat in the next waiting run. The room says
   "Waiting for other participants" no matter who has arrived.
2. Once all human seats are taken and connected, the server waits a random amount
   of time (`start_delay_*_seconds`) and starts the run. Each player then sees their
   own label, such as "Player A".
3. Each round starts with discussion (`chat_seconds`, default 60 s), then moves to
   voting (`vote_seconds`, default 20 s). Players can post only during discussion,
   but round 1 chat stays visible in round 2. Results follow the second vote.
4. Each player casts one final ballot for one of the other two players by default
   (see `allow_self_vote`). During voting, players see how many ballots are in and
   see their own vote, but not anyone else's. The vote ends early if all three seats
   vote. Missing ballots at the deadline count as abstentions. After round 1,
   everyone sees the totals for each player.
5. The player with the most round 2 votes becomes the Decision Maker. If there's a
   tie, round 1 votes decide it. If there's still a tie, the server picks at random
   from the remaining tied players and saves the choice with the run. Players see
   the winner and the round 2 totals, not other players' individual ballots.

Refresh to reclaim the same seat and see the run's state or result. In the waiting
room, the Leave button frees the seat immediately. Closing a waiting tab frees it
after `waiting_grace_seconds`. Once a run starts, a disconnected player keeps their
seat. The server keeps advancing phases even if all tabs are closed.

## Conditions and how to switch

Set `humans` and `ai` in [`config.yml`](config.yml) to choose a condition. The
default is 2 humans and 1 AI.

| Condition | `humans` | `ai` | Tabs to open |
| --- | ---: | ---: | ---: |
| 2 humans + 1 AI (default) | 2 | 1 | 2 |
| 3 humans | 3 | 0 | 3 |
| 1 human + 2 AI | 1 | 2 | 1 |

After editing those two lines, recreate the backend:

```bash
docker compose up -d --force-recreate backend
```

The backend reads `config.yml` only at startup, so run this after any config change.
Use `--force-recreate`, not `restart`. The file is bind-mounted, so if your editor
replaces it, a restarted container can still see the old file. Recreating the backend
ends unfinished runs (see [Restarts](#restarts)). The server shuffles the seat layout
at random for each run.

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

For a quick demo, try 15 seconds for chat and 10 for voting. Set both start delay
values to 2 and recreate the backend. Restore the defaults afterwards.

## AI players and the API key

Each AI player attempts two or three messages per discussion and one vote per round.
It acts at random times within the phase and pauses before sending a message to
mimic typing. The server checks and saves its actions the same way it does for people.

Only the backend calls [Mistral](https://console.mistral.ai/api-keys). Copy `.env.example`
to the git-ignored `.env` next to `compose.yaml` and put the key there:

```bash
cp .env.example .env        # then set MISTRAL_API_KEY=...
docker compose up -d --force-recreate backend
```

If there's no key or a model call fails, times out or returns unusable text, the
AI draws from a large pool of scripted lines and gives more weight to players who
have spoken when it votes. The server checks chat replies for a single short line
that doesn't repeat an earlier one. It replaces an outright admission of being AI
with a scripted line, but leaves how to answer "are you a bot?" to the prompt. With
`allow_self_vote: false`, the AI can't vote for itself, even in the fallback. The
event log records whether each accepted AI action came from `llm` or `scripted` and
why it fell back, if it did.

I used AI coding assistants while building the app. I recorded their prompts, along
with the prompts and model the AI players use, in [`ai_prompts.md`](ai_prompts.md).

## Event log

The backend creates three Postgres tables at startup. `sessions` keeps one row per
run with its config snapshot and winner. `participants` stores the seats and their
private roles. `experiment_events` keeps the ordered log. You can query past runs.

Find a session (newest first):

```bash
docker compose exec db psql -U experiment -d experiment -c "SELECT id, status, phase, config->>'humans' AS humans, config->>'ai' AS ai, winner_slot, created_at FROM sessions ORDER BY created_at DESC LIMIT 5"
```

Read its events in SQL (replace `<session_id>`):

```bash
docker compose exec db psql -U experiment -d experiment -c "SELECT e.seq, e.ts, e.phase_seq, e.event_type, p.slot, p.role, e.payload FROM experiment_events e LEFT JOIN participants p ON p.id = e.actor_id WHERE e.session_id = '<session_id>' ORDER BY e.seq"
```

Or read them as ordered JSON from inside the Compose network:

```bash
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/internal/sessions/<session_id>/events').read().decode())"
```

The log records each accepted `message` and `vote`, along with `phase_change`, `join`
and `disconnect` events. The `seq` numbers have no gaps within a run, and `ts` is the
server's UTC timestamp. Rejected attempts don't enter the event log. The log and seat records
reveal roles and when people join or disconnect. The frontend returns 404 for
`/internal/...` instead of proxying it, and Compose doesn't publish the backend port.

## Tests

I wrote three automated tests for the Decision Maker rules. They check a clear round
2 winner and both tiebreaks: round 1 votes and a controlled random pick.

```bash
docker compose exec -T backend python -m unittest discover -s tests -v
```

I checked the rest by hand and kept the evidence for each build step in
[`reviews/`](reviews/).

## Restarts

Restarting or recreating the backend ends every unfinished run. On startup the server
marks those runs `abandoned`, adds a `phase_change` event and keeps the logs. Players
see "This run is no longer available". Seat tokens and timers live in memory, so the
old runs can't resume. Open a fresh tab or choose "Join a new run" to start again.

## Design decisions and tradeoffs

I kept the alternatives and my reasons for each choice in the build plan
([`plan.md`](plan.md)).

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
| An engaging look (option H: breathing waiting shape, countdown ring, animated vote reveal and podium) | A neutral, plain interface | I chose an engaging look over a neutral one; a real study would probably tone down the result reveal. |

I use one lock per run for seat claims, ballots and event numbering. A separate
process lock covers finding or creating the next open session and claiming a seat
in it. The backend commits changes to the database and event log together before
broadcasting them. It stores and enforces deadlines for each run, and the browser
uses server time to display the same voting and discussion windows for everyone.

A join response contains an opaque seat token and the current phase. Chat messages
have their own numbering, separate from the event log. Together with random seats
and labels that only appear when play starts, this keeps the payload fields, counts
and ordering from directly identifying AI players.

## What several backend processes would need

I kept the backend to one process for the local demo. Locks and seat tokens live
in memory, as do open WebSocket records, phase timers and AI schedulers. Behind a
load balancer, each process would have its own copy. To run more than one:

- Share locks for seat claims, messages, votes and phase changes using Redis or
  Postgres row or advisory locks (`SELECT ... FOR UPDATE`, `pg_advisory_xact_lock`).
  Otherwise two processes could claim the last seat, accept a second ballot or use
  the same event sequence number. Finding or creating a waiting run also needs a
  shared lock.
- Put seat tokens in Redis or a table every process can read.
- Send broadcasts over Redis pub/sub or Postgres `LISTEN/NOTIFY` so messages can
  reach browsers connected to any process.
- Give timers and AI turns one owner per run through leader election or a job
  queue, so each phase advances only once.

Redis could handle locks, tokens and broadcasts alongside row locks for the log.
I left that setup out because the local demo doesn't need it.

## Known limitations

- Someone who takes several seats in one run can use the start timing to work out
  which seats are AI. A real session assumes one seat per person. I didn't add
  participant identification to enforce that.
- Someone who waits a long time can tell at least one other player is human. The
  server starts the run a few random seconds after the last human connects. A
  scheduled start would hide this in a real deployment.
- I gave AI players short, casual messages and typing-like pauses. The prompt tells
  them not to say they're AI and to vary their answers to direct questions. A player
  who probes them or watches their timing, brevity and style can still spot them.
- Players can sometimes work out other ballots by subtracting their own vote from
  the totals.
- This is a local demo. It runs one backend process and the Vite dev server, with
  no authentication and default database credentials. Only network isolation
  protects the internal log endpoint. Seat tokens go in the WebSocket query string,
  so they appear in the backend access log. They last no longer than a restart.
- Closing a tab loses its session storage. You can refresh a running tab, but if
  you close it you can't rejoin its seat. A finished tab stays on the results, so
  open a fresh tab for the next run.
- Restarting the backend ends unfinished runs. See [Restarts](#restarts).
- The app supports one provider and one model at a time. Without a key or when calls
  fail, it uses scripted lines, which are weaker than the model's replies.

## Repository layout

```text
compose.yaml  config.yml  .env.example  plan.md  ai_prompts.md  reviews/
backend/app/   session/ experiment/ messaging/ voting/ ai/ realtime/ event_log/
backend/tests/ winner tests
frontend/src/  app/ session/ experiment/ messaging/ voting/ results/ realtime/
```
