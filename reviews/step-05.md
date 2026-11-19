# Step Five review

**Blocked before Step Six.** The available revision, `84b7419`, still allows self-votes unconditionally. The browser trials also reproduced a role clue that a participant can trigger from one seat by asking a direct bot question.

## Fixes required

1. **Make the self-vote rule available in the reviewed build.** The browser offered the self-vote button and returned a private confirmation after a human self-vote in all four mixed runs. Three scripted AI ballots were self-votes. The YAML loader has no self-vote option and rejected the trial key `allow_self_vote` with either Boolean value. An enabled setting therefore could not be tested independently of the existing unconditional behavior, and the disabled path could not be tested at all. Default the rule to false, enforce it in the shared server validation, and exclude the AI's own label from both provider ballot choices and scripted fallback when disabled. Retest both settings, including the provider and fallback paths, on that revision. [Configuration](../backend/app/session/config.py) · [AI ballot selection](../backend/app/ai/players.py#L213) · [Scripted ballot](../backend/app/ai/scripted.py#L103)
2. **Remove the predictable behavioral response to the bot question.** The same prompt repeatedly switched live-key AI seats from model-generated chat to a small pool of scripted deflections, for multiple turns and even for both seats at once. In the browser, the casual human response and the AI seats' repeated evasions were visibly different. Keep protections against role disclosure, but avoid a separate fixed response pattern that a participant can trigger. Retest the question in ordinary and targeted conversations, with and without the key. [Question-triggered branch](../backend/app/ai/players.py#L145) · [Scripted deflections](../backend/app/ai/scripted.py)

## Browser runs

I ran four independent Compose stacks with 30-second discussions and 12-second votes, with a browser tab per human. All four reached a Decision Maker. The one-human/two-AI live-key run used a freshly built image of the same revision as the other runs.

| Configuration | AI chat in Rounds 1 and 2 | AI ballots | Evidence |
| --- | --- | --- | --- |
| 2 humans, 1 AI, key present | 3 and 2 | 1 each round | Round One was model-generated. Both Round Two lines took the question-triggered scripted path. Both ballots were model-generated. |
| 1 human, 2 AI, key present | 2 and 2 per AI | 1 per AI per round | Four model-generated chat turns, four model-generated ballots, and four Round Two deflections recorded as `type_question`. |
| 2 humans, 1 AI, no key | 2 and 2 | 1 each round | All AI actions used the `no_key` fallback. One AI self-vote. |
| 1 human, 2 AI, no key | 2 and 3 for one AI, 3 and 2 for the other | 1 per AI per round | All AI actions used the `no_key` fallback. Two AI self-votes. |

A separate browser-started run with an intentionally invalid test credential recorded `http_401` and accepted scripted chat and ballots. The four main runs each reached three total ballots in both rounds.

## What a suspicious participant could see

- I made a substantive decision prompt in Round One and asked both seats directly whether they were bots in Round Two. The live-key AI seats moved from contextual responses to repeated evasions. In the one-human/two-AI run, both other labels produced two scripted deflections. One 42-character deflection recurred across three independent runs. Nobody explicitly disclosed their role. This is a repeatable clue that does not require the participant to control several seats.
- Across the browser samples, AI lines were 12–66 characters and 3–12 words. The deliberately varied human controls were 35–113 characters. Their lengths overlapped, but the AI turns were consistently brief and had lower-case, stock phrasing in scripted mode. The source caps model chat at 110 characters and 18 words. A single short line is weak evidence. Repeated short, evasive lines from the same label after a specific trigger are more informative.
- AI lines in these 30-second rounds appeared about 7–25 seconds after the start, in two or three turns per AI per round, even after other participants stopped speaking. AI ballots landed about 3.5–8.9 seconds into the 12-second vote. The protocol exposes chat timestamps and live ballot count changes. Timing by itself does not identify the voter, and human and AI ballot timings overlapped. The combination of cadence, brevity, and probe responses was more informative than any one signal.
- Live AI, fallback AI, and human messages all used the same browser frame keys, `type`, `author`, `number`, `round`, `text`, and `ts`. I saw no roles, AI counts, source, provider, model, key, or fallback fields in the captured frames. I used Postgres afterward to verify the actual sources and ballots.

## Credential check

`.env` is ignored and untracked, and the checked-in example uses an empty placeholder. I compared the configured credential in memory against current tracked files, 130 reachable Git blobs, logs from 18 app and review containers, temporary operator logs, and six Postgres data dumps. There were zero exact matches. The frontend containers had no injected Mistral key. The credential was not printed.

## Reviewer record

Reviewer model: `gpt-6.2-sol`. No application code or tracked configuration changed. The review used temporary overrides and left the existing default stack in place.

> another agent just built step 5 the ai players and then changed the voting rule so players cannot vote for themselves by default
>
> do not change any code
>
> rerun both mixed conditions in the browser with the key and without the key with short timings
>
> rerun 1 human and 2 ai with the key because the builder ran that one on older code
>
> check both self vote settings and that the ai never votes for itself when the setting is false
>
> then act like a suspicious participant and try to work out who the ai is
>
> look at timing and message length and style and how it answers when you ask if it is a bot
>
> check that an ai message and a human message look the same in the traffic the browser receives
>
> check the api key is not in any tracked file or log and the env file is ignored
>
> save your findings in the reviews folder with filename step 05 same naming as before
>
> tell me if it is ready for step 6 or what must be fixed first
