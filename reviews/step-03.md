# Step Three review

**Ready for Step Four.** The functional checks passed and the chat sequence leak is fixed. The experiment owner accepted the multi-seat timing inference as outside the current privacy scope.

## Known limitation and scope decision

- **The start transition reveals when all human seats are occupied.** The server waits for every human seat to be claimed and connected, then starts after 3–8 seconds. Independent tabs can claim separate seats without any participant-level enrollment check. A participant who controls enrollment in a fresh run can open tabs one at a time and wait longer than the maximum start delay between tabs. The number of tabs needed to trigger discussion is the human count. At the start, each of those tabs receives its own label, so the remaining labels identify the AI seats. [Readiness and start delay](../backend/app/experiment/engine.py#L125) · [Seat claims](../backend/app/session/service.py#L64)
- Reproduced with the default mix on a fresh test stack. One tab was still waiting after nine seconds. The second tab joined, both entered discussion, and their labels were Player C and Player A. From the browser observations alone, I inferred one AI in Player B. Postgres confirmed that assignment. In the three-human browser run, all three tabs entered the same discussion and exposed all three human labels.
- The experiment assumes one seat per participant in real sessions. Enforcing that would require participant identification, which the current app does not have. The demo requires several tabs on one machine, so the owner chose to keep multi-tab enrollment and accept this inference when one person controls multiple seats. No code change is required for Step Three to pass.

## Browser and runtime checks

| Check | Result |
| --- | --- |
| Three tabs with short timings | Used three humans with 25-second chat and vote phases. The waiting screen showed generic copy and Leave. With two tabs the run stayed waiting. The third tab initially showed the same screen, then all three entered Round One discussion and received distinct labels. |
| Close a waiting tab | Closed a tab before the run started. Postgres recorded the socket close and grace expiry, and all three seats were open again. |
| Close a tab mid-run and retain chat | Closed the third tab during Round One. Its seat remained claimed. The remaining tabs advanced, and Round Two displayed the Round One message alongside a new Round Two message. |
| Reject chat during both voting phases | The Round One voting form was disabled. A direct WebSocket submission with the current phase sequence returned `action.rejected` with `chat_closed` during each voting phase. The log contained only the two accepted discussion messages. |
| Close every tab | Closed the last two tabs during Round Two voting. Postgres logged both disconnects before the transition to results and marked the run completed. In a separate run with five-second chat and four-second votes, I closed both tabs during Round One discussion. Postgres then recorded Vote One, Discussion Two, Vote Two, and results in order with no intervening joins. |
| Restart during discussion | Restarted the isolated two-human/one-AI backend while a run was in Round One discussion. The browser displayed “This run is no longer available.” Postgres kept the earlier events and appended a phase change to `abandoned` with reason `backend_restart`. |
| Default timing restored | The repository `config.yml` and the running default backend's mounted config both had 60-second chat and 20-second voting. Short timings were supplied through temporary overrides on separate Compose stacks. |
| Backend port isolation | No Docker host port binding for the backend. From the host, loopback port 8000 refused the connection and reaching the backend container IP directly timed out. From inside Compose, `backend:8000/api/health` returned HTTP 200. The published frontend returned HTTP 404 for a known run's internal log URL. |

## Chat traffic review

- The two captured `message.created` frames carried public numbers 1 and 2. Their private log sequence numbers were 9 and 13. A disconnect and phase changes between the messages did not create a gap. Snapshot history uses the same chat-only numbering. [Chat broadcast](../backend/app/messaging/service.py) · [Snapshot serialization](../backend/app/experiment/engine.py)
- The waiting snapshot used `own_label: null`, empty chat, and no occupancy, role, or count. Join returned the opaque token and phase. Phase frames used a phase counter and deadlines. The browser received neutral chat author labels and timestamps, with no observed private event IDs or join/disconnect broadcasts.
- Current chat silence alone does not identify AI seats. Step Three has no AI chat implementation, and humans may stay silent. The planned AI speech counts and delays still need privacy review when AI chat is implemented.

## Reviewer record

Reviewer model: `gpt-6.2-sol`. No application code or tracked configuration changed.

> Another agent just built step 3 and then fixed one leak. The event log sequence number in the chat message: do not change any code. Rerun the step 3 checks in the browser with 3 tabs and short timings.
> Also check the 4 things the builder did not show:
> 1. Close all the tabs and confirm the server still moves through the phases.
> 2. Confirm chat is still rejecting. Chat is rejected during the first voting phase, not only the second.
> 3. Confirm the config file is back to 60 seconds chat and 20 seconds vote.
> 4. Confirm the backend port is not reachable from outside the Docker.
>
> After that look hard for anything that lets the browser work out who is an AI and how many there are, including by counting or timing, not only by field names. Then save your finding in the review folder with the filename step 03, same naming as before. Tell me if it's ready for step 4.
