# Three-participant experiment build plan

## What we’re building

A local React and TypeScript app with FastAPI, Postgres, and WebSockets. A single Docker Compose command starts the app. Human participants join in separate tabs and complete a waiting room, two rounds of timed chat and voting, and a final Decision Maker result. The server owns state and deadlines. The browser displays that state and submits actions.

Each run has three shuffled seats labeled Player A, B, and C. The browser receives neither player types nor the configured AI count at any phase. Postgres keeps an ordered, timestamped log of accepted messages, votes, phase changes, joins, and disconnects.

## Experiment rules

- **Join and waiting.** Opening the app claims a human seat in the next open waiting session. Create a new session when none has a free human seat. Ship `config.yml` with two humans and one AI. Also support three humans and one human plus two AI. Edit the backend YAML and restart to switch conditions. Shuffle the role assignments for each run. Display only “Waiting for other participants” in the waiting room. Once all the required humans are present, wait a few random seconds in every condition before starting. The waiting room never expires.
- **Continuity.** A refresh reclaims the same seat. Leaving the waiting room releases it. Use a per-tab seat token in session storage and a short server-side disconnect grace period while waiting so refresh can reconnect. An explicit leave releases the seat immediately. Recheck readiness before starting if someone disconnects or leaves during the start delay. A mid-run disconnect leaves the seat reserved and the experiment continues. Restarting the backend ends unfinished runs and preserves their logs. Document that a restart requires starting a fresh run.
- **Discussion and voting.** The YAML defaults are 60 seconds of chat and 20 seconds of voting per round. Round 1 chat stays visible during round 2. Disable chat during voting and reject chat submitted outside discussion. Players may vote for themselves. A submitted vote is final. During voting, show the total number of ballots cast without identifying voters. Close the vote early when all three cast ballots, otherwise treat missing ballots as abstentions at the deadline. After vote 1, show aggregate vote totals per player.
- **Decision Maker.** Use vote 2 totals. If candidates tie for first, compare their vote 1 totals. If candidates still tie, choose randomly among them and store the choice in the same transaction as completion. Show per-player totals and the winner without exposing individual ballots.
- **AI behavior.** AI seats speak two or three times in each discussion and vote once per round, with randomized delays within the relevant phase. Use a backend LLM API key when available. For chat, give the model the discussion so far and have it write a short, original message in context. For voting, give it the chat so far and ask it to choose one of the three candidates based on that chat. Use scripted lines and a fallback ballot only when the key is missing or the call fails, times out, or returns unusable output. Validate the output before posting, and fall back if it discloses player types or the AI count. Route AI and human actions through the same validation, persistence, and broadcast path. Keep the key, config, and provider metadata on the backend.

## Feature folders

```text
compose.yaml
config.yml
README.md
ai_prompts.md
reviews/             # step-01.md through step-06.md
backend/
  app/
    main.py
    session/        # Config, seat claims, waiting room, reconnects
    experiment/     # Phases, timer, winner
    messaging/
    voting/
    ai/
    realtime/
    event_log/
frontend/
  src/
    app/
    session/
    experiment/
    messaging/
    voting/
    results/
    realtime/
```

## Postgres tables

Create tables at backend startup. Run one backend process and keep active socket connections, seat tokens, and timers in its memory. On startup, mark any unfinished runs abandoned and log that phase change. Keep previous events queryable.

| Table | Store |
| --- | --- |
| `sessions` | Run ID, private config snapshot, current phase and sequence, phase start and deadline, status, creation and completion timestamps, and persisted winner. |
| `participants` | Run ID, participant ID, slot number 1–3, private role, and seat claim state. Enforce one row per run and slot. |
| `experiment_events` | Run ID, monotonically increasing sequence within the run, server UTC timestamp, phase sequence, event type, optional actor, and payload. Store message text, vote target and round, phase change, join, or disconnect as applicable. |

Use one in-memory lock per session to serialize seat claims, accepted messages and votes, phase transitions, and event sequencing. Use a short process-level lock when finding or creating the next open session so simultaneous joins cannot create competing sessions. Keep provider calls and socket sends outside the locks. Commit state changes and their events together, then broadcast. Use the log as the durable source of chat and ballots and enforce one accepted vote per participant per round. Rejected attempts stay out of the log. Inspect events through SQL or `GET /internal/sessions/{session_id}/events`, which returns the ordered JSON events from inside the Compose network. Keep the backend port unpublished and proxy only participant routes, since joins and disconnects in the full log can expose roles.

## WebSocket messages

Page load joins over HTTP. The WebSocket authenticates with the tab’s seat token. Snapshots and updates use neutral labels and viewer-safe fields.

| Direction | Message | Contents |
| --- | --- | --- |
| Server → browser | `session.snapshot` | Own label, current phase and sequence, server time and deadline if timed, and visible chat, own ballot status, vote counts or results as applicable. Sent on connection and reconnect. Send it before live updates for that connection. |
| Server → browser | `phase.changed` | Phase, round, phase sequence, server time, and optional deadline. |
| Browser → server | `message.send` | Text and expected phase sequence. |
| Server → browser | `message.created` | Neutral author, round, text, and server timestamp. |
| Browser → server | `vote.submit` | Target player and expected phase sequence. |
| Server → browser | `vote.recorded` | Private confirmation for the voter. |
| Server → browser | `vote.progress` | Total ballots cast in the active round. |
| Server → browser | `vote.summary` | Round 1 aggregate totals once voting closes. |
| Server → browser | `results.ready` | Persisted winner and final aggregate totals per player. |
| Server → browser | `action.rejected` | Reason for the rejected action. |

The browser uses server time and deadlines to display the countdown. The server advances the phase even with all tabs closed. Waiting-room changes in seat occupancy produce no participant-facing progress updates.

## Decisions

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

## Six build steps

The AI builder agent implements one step at a time. The reviewer agent reruns the checks, reviews the diff, and records findings, evidence, and any blocking fixes in `reviews/step-NN.md` before the next step. Start recording prompts and models as they are used so the final artifact can be checked against the implementation.

**Four-hour cap, including review.** Budget 190 minutes for the builder, 40 for review, and 10 for fixes. This is a timebox for a minimal interface, one LLM provider, and manual checks with short YAML timers. Live provider verification depends on the supplied key and its provider/model.

| Step | Build | Builder + review | Check before moving on |
| --- | --- | --- | --- |
| **1. Compose scaffold** | Create the three services and a readiness page. Follow the handoff below. | 25 + 5 min | Run the single startup command and verify the browser and JSON readiness response. |
| **2. Sessions and storage** | Create tables at startup, load YAML, add automatic HTTP join, shuffled seats, explicit leave, token reuse on refresh, in-memory locks, and the internal JSON log endpoint. | 30 + 5 min | Fill the default run, verify another tab starts a new run, refresh and reclaim a seat, leave and free it, and confirm the log endpoint stays inside Compose. |
| **3. Live phases and chat** | Add the waiting room, WebSocket, server timer, both discussion and voting phases, chat, and disconnect handling. | 45 + 7 min | Use short test timings. Check delayed start with generic waiting text, waiting-seat release on tab close, continuing after a mid-run disconnect, chat history in round 2, and chat rejection during voting. Verify a restart ends the run and preserves logs. |
| **4. Votes and winner** | Add ballots, counts, early close, abstentions, totals, and persisted results. Add exactly three automated tests for the winner logic: a clear vote 2 winner, a vote 2 tie resolved by vote 1, and a tie remaining after vote 1 that invokes a controlled random pick among the tied candidates. | 30 + 8 min | Run the three tests. Manually verify self-votes, final ballots, early close, abstentions, aggregate-only visibility, and the same result on reconnect. All other checks in the plan are manual. |
| **5. AI chat and votes** | Schedule AI actions, integrate one LLM provider for generated chat and chat-based votes, and add scripted fallback. Keep calls within the phase window and reject late actions. | 35 + 7 min | Verify two or three AI messages per discussion and one ballot per AI per round. Check the missing-key and failed-call paths. With the key, verify a generated response and a chat-based vote. Inspect public traffic for role and count leakage. |
| **6. End-to-end review and handoff** | Finish the README and `ai_prompts.md`. The README covers setup, config switches, the tab demo, SQL and JSON log access, and a **Design decisions and tradeoffs** section based on the table above. Explain restart behavior and why several backend processes would need Redis or database row locks. In `ai_prompts.md`, record every application prompt template and model used, plus the task prompts and model IDs used by the builder and reviewer. Omit credentials and participant chat from the artifact. | 25 + 8 min | Complete a short run in each YAML condition, reusing evidence from earlier gates when it was collected on the final build. Match the results and timestamped events against Postgres, check the two documentation files, and restore the default config. |

### Step 1 handoff

Add a Node 22 Vite React and TypeScript frontend with a package lockfile, a Python 3.12 FastAPI backend with pinned dependencies, and Postgres 16 with a named volume. Publish only the frontend on localhost port 5173. Proxy `/api` from Vite to `backend:8000`. Give all three services health checks and start the backend after Postgres is healthy. Implement `GET /api/health` with a real `SELECT 1` and a bounded database timeout. Return HTTP 200 with `{"status":"ok","database":"ok"}` on success or HTTP 503 on failure. The frontend entry page fetches the endpoint and displays readiness. Document the startup command and local URL in the README.

```bash
docker compose up --build -d --wait
curl -fsS http://localhost:5173/api/health
```

Open `http://localhost:5173` and confirm it reports API and database readiness. Step 1 is ready for review once these checks pass. It requires no experiment data or API key.

## Cut order if time runs short

1. Drop visual polish and any custom component setup. Use a single plain page with native controls and the required states.
2. Cut repeated manual runs. Preserve one full run per condition, reuse recorded evidence where the relevant code is unchanged, and keep all three winner tests and all six review notes.
3. If the key is unavailable, finish with the fallback and record the live provider check as pending. Keep the provider integration and exercise its failure path.
4. If the remaining work still cannot fit, the first feature to propose deferring is live LLM integration. Scripted players can still complete all three runs, but this would leave the generated-chat and chat-based-vote requirement unfinished. Get agreement before making that cut.

Production deployment, multi-process operation, dashboards, and an experiment editor are already out of scope.

## Done

Both agents have cleared six gates and the reviewer has saved each step’s findings. One Compose command launches an app that completes all three conditions with blind participant views, a stored Decision Maker, and a timestamped Postgres log. The winner tests pass, and the README and `ai_prompts.md` are complete.
