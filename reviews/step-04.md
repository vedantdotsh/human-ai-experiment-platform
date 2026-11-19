# Step Four review

**Ready for Step Five.** All three winner tests and the browser voting checks passed. Participant traffic keeps ballot receipts private and publishes only counts, aggregate totals, and the winner. The inference limits below remain relevant when AI voting is added.

## Checks rerun

- `cd backend && python3 -m unittest -v tests.test_winner` passed all three tests. They cover a clear Vote Two winner, a Vote Two tie resolved by Vote One, and a remaining tie resolved by a controlled random pick among the tied candidates.
- Used three independent human tabs in an isolated Compose stack with five-second discussion phases and 15-second voting phases. The tracked configuration and application code were untouched.

| Browser check | Result |
| --- | --- |
| Self-vote and final ballot | Player C voted for themselves in Vote One. The page showed the private final ballot. Refresh kept the seat token and choice, with all three vote buttons disabled. A direct replacement submission returned `already_voted`. |
| Progress and early close | Other tabs saw the ballot count tick from one to three. Vote One ended about 9.7 seconds before the published deadline after the third valid ballot. |
| Vote One summary | Round Two showed Vote One totals of A 0, B 1, C 2. |
| Abstention and late vote | Only A and C voted in Vote Two. It closed at its deadline, with B's ballot absent. B sent a direct submission after the deadline and after the results transition. The server returned `not_running` and Postgres retained exactly two Vote Two ballots. This exercised rejection after the phase closed. |
| Vote Two tie and persisted result | Vote Two totals were A 1, B 0, C 1. All tabs received Player C as the Decision Maker. Postgres stored winner slot 3 and the completion event recorded `decided_by: vote1`. Refresh after completion returned the same winner and both rounds' totals. |
| Participant traffic and internal log | Compared each tab's received WebSocket frames. Only the submitting seat got its `vote.recorded` receipt. Reconnect snapshots contained only that seat's own vote, or null. Progress contained only a round and count, while summaries and results contained candidate totals and the winner. No frame exposed another voter's ballot, actor IDs, or role fields. The internal log returned HTTP 404 through the frontend. |

## Privacy findings

- **Aggregates allow ballot deductions in some outcomes.** In this run, Player B could subtract their own Vote One ballot for B from the published totals and deduce that both A and C voted for C. This follows from publishing per-candidate totals in a three-seat run. The frames contain no explicit mappings from other voters to their targets, and the deduction alone says nothing about their roles.
- **Step Four's ballot counts can reveal a bound on the human count.** Only humans can vote in this build because AI voting lands in Step Five. A participant who knows that limitation and sees three ballots, or an early close, can infer three humans and zero AI. Seeing fewer ballots establishes a lower bound on the number of humans, since a human can abstain. Counts alone do not identify a particular seat as AI when fewer than three ballots arrive.
- **Recheck timing once AI voting exists.** The arrival time of each count increment is observable, as is the exact early close. These signals can expose automated voting if AI ballots follow a distinct schedule or consistently appear without human activity. Step Five should verify that AI and human ballots use the same validation, persistence, and broadcast path, and inspect count and timing behavior alongside the payloads. The accepted Step Three limitation for one person controlling several seats still applies.

## Reviewer record

Reviewer model: `gpt-6.2-sol`.

> Another agent, just built step 4. Do not change any code. Run the three winner tests and rerun the step 4 checks in the browser with three tabs and short timings. Also keep checking these in the running app.
>
> A tie in a vote 2 is settled by vote 1. Refresh during voting keeps your own ballot and does not let you vote again. A vote sent after the deadline is rejected, and no message sent to the browser shows who voted for whom.
>
> Look for anything in the voting and result that lets the browser work out who is an AI. Save your findings in the review folder with filename step 04 and the same naming as before. Tell me if it's ready for step 5 or what must be fixed first.
