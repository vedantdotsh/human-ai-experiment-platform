# Step Two review

**Ready for Step Three.** The waiting-room label leak was fixed in `114bf7b` and passed a targeted recheck in all three configurations.

## Targeted recheck

The join endpoint and frontend response type now expose only `seat_token` and `phase`. The service chooses randomly among open human seats. I tested through the Vite participant proxy in a separate Compose stack for each configuration and verified each mix against the saved Postgres configuration.

| Configured mix | Fresh joins | Same-token reclaims | Result |
| --- | ---: | ---: | --- |
| 3 humans, 0 AI | 4 | 4 | Pass |
| 2 humans, 1 AI | 3 | 3 | Pass |
| 1 human, 2 AI | 2 | 2 | Pass |

Every response was HTTP 200 with exactly an opaque seat token and the `waiting` phase. New claims returned distinct tokens, and reclaims returned the original response. Each sample filled one run and included the first claim in a second run. No responses included player labels, roles, counts, occupancy, or run identifiers. The recheck covered the original blocker only. The tracked configuration and application code were untouched.

## Original blocking finding (resolved)

- [The join route](../backend/app/session/routes.py#L17) returns `seat_token`, `label`, and `phase`. [Seat allocation](../backend/app/session/service.py#L153) filters for open human seats and takes the lowest numbered slot. On a fresh run, a first response of Player B proves Player A is AI. A first response of Player C proves both Player A and Player B are AI, revealing an exact count of two. Shuffling the roles when the run is created does not prevent this inference.
- Reproduced on the default configuration. One fresh run returned Player B and then Player C. Another fresh run also returned Player B first, and its Postgres participant rows confirmed Player A was AI and Players B and C were human. The two-AI case follows from the allocation rule and was reviewed in code.
- Remove the label from waiting-phase join and reclaim responses. The waiting page only needs the opaque seat token. Reveal the participant's own label in the authenticated snapshot once play starts. Randomize selection among available human seats to remove the ordered allocation signal. Before clearing this gate, check fresh joins and reclaims in each configuration and confirm their waiting responses contain no labels, role or count fields, occupancy, or run-grouping identifiers.

## Original review checks

| Check | Result |
| --- | --- |
| Load the waiting page in browser preview | Displayed “Waiting for other participants” and a Leave button. No roles, player labels, AI counts, or seat occupancy appeared on the page. |
| Inspect frontend source and actual join responses | The frontend type and HTTP response contain the three fields above. The code stores the seat token in session storage and shows generic waiting copy. No role or count fields or YAML config imports appeared in the frontend. |
| Fill a default run and join again | Matched the HTTP join sequence against Postgres events. Two fresh claims filled a run, and the next fresh claim entered a different run. |
| Refresh and explicitly leave | A real browser refresh preserved the token. A token reclaim returned the same label and phase. The Leave button returned HTTP 204 and cleared the stored token. A separate API check confirmed that the released seat became open and could be claimed again. |
| Check the internal log boundary | The same known run's event URL returned HTTP 404 through the published frontend and HTTP 200 with ordered events inside Compose. The published `/config.yml` path served the SPA HTML and no YAML. Only the frontend port was published. |

The review used the running default Compose stack. No application code changed.

## Reviewer record

Reviewer model: `gpt-6.2-sol`.

> Read the plan file. Another agent just built step 2. Do not change any code. Look specially for anything that lets a browser find out who is an AI or how many AI players there are. Check the joint responses, the page, and the frontend code. Save your findings in the review folder in a file named step 02, with the same naming as the step 1 review. Tell me if it's ready for step 3 or what must be fixed first. What needs to be fixed first?
