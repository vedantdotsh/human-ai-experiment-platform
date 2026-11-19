# AI prompts and models

Every prompt used to build and review this project, and the prompts the AI players
use at run time, with the model and tool for each. Prompts are reproduced word for
word, including typos and odd spacing. No credentials and no participant chat are
recorded here.

Contents: [Planner](#planner) · [Builder](#builder) · [Reviewer](#reviewer) ·
[UI builder](#ui-builder) ·
[Application: the AI players](#application-the-ai-players)

## Planner

| | |
| --- | --- |
| Output | [`plan.md`](plan.md) |
| Model | **Not recorded.** |
| Tool | **Not recorded.** |
| Prompt | **Not available.** |

The planner's prompt, model and tool were never given to the builder, so they cannot
be reproduced here and have deliberately not been guessed. To complete this record,
paste the planner's prompt below, word for word, and fill in its model and tool.

```text
(planner prompt: to be added by the project owner)
```

## Builder

| | |
| --- | --- |
| Model | Claude Sonnet 5.5 (`claude-sonnet-5-5`) |
| Tool | Claude Code (Claude Agent SDK harness), run inside T3 Code |

One conversation built all six steps. These are the owner's messages to the builder,
in order, word for word. The first message also attached `plan.md`.

### Builder prompt 1: Step 1 — build the Compose scaffold

```text
Read the plan.md file, build step one only, and execute step one. Handoff says: run the checks from the plan and show me the output then stop and wait. Don't move on to step two until I say so.
```

### Builder prompt 2: Step 1 review housekeeping, then Step 2 — sessions and storage

```text
Okay the step 1 review has passed. Before you start step 2 do the following three things:
1. Add the TypeScript build info file in the frontend folder to the gitignore file.
2. There is a file in the project root called "review step 1". Move it to the folder called "reviews" and rename it to "step 01".
3. Make three separate commits:
1. Plan file alone.
2. The step 1 files.
3. The review file.

The browser preview works now so you can open the preview yourself if you want. After that build step 2 only from the plan file. Run the step 2 checks, including in the browser, and show the output. Commit when the checks are passed then stop. Do not start step 3 until I say so.
```

### Builder prompt 3: Step 2 blocker fix (seat allocation and label leak)

```text
The step 2 review found a blocker. Read the review file for step 2 in the reviews folder. The problem is that human seats are given out in label order, skipping the AI seats so the label a person gets reveals which players are AI.
Fix it two ways:
1. Give each person who joins a random open human seat.
2. Do not send the player label in the join or rejoin response while waiting. The player only learns their own label when the experiment starts.

Then recheck the join responses in all three configurations and show the output. Commit the fix and the review file. Do not start step 3.
```

### Builder prompt 4: Step 3 — live phases and chat

```text
Step 2 is now ready for Step 3. The reviewer has given a green flag. The reviewer updated the Step 2 review file after you have committed so commit that update first.

Now build Step 3. Build only Step 3 from the plan file. Remember that each player learns their own label only when the experiment starts. Run Step 3 with short timing in the browser with 3 tabs and show me the output.

Commit when the check passes, then stop. Do not start Step 4 until I say so.
```

### Builder prompt 5: Step 3 fix (event sequence number in chat messages)

```text
One fix before the review: chat messages sent to the browser carry the event log sequence number. Only humans create join and disconnect events so the number lets the browser work out how many humans there are and when someone disconnects.

Replace it with a simple message counter per run that only counts the chat messages or remove it if the frontend does not need it. The event log itself stays as it is. Show me a chat message payload and a snapshot payload after the fix then commit. Do not start step 4.
```

### Builder prompt 6: Step 3 review housekeeping, then Step 4 — ballots and winner

```text
The step 3 review is done. The reviewer found that one person with several tabs in the same session can work out who the AI is from when the run starts. I decided it's out of scope because a real participant holds one seat and preventing it needs participant identity.  ah
Apart from that:
- Add this to the decision table in the plan file and note it for the README.
- Also note that a participant who waits a long time can tell at least one other player is a human. The scheduled start time would hide that in real deployment.
- Commit that together with the step 3 review file.
- Then build step 4 only from the plan file, including the three winner tests.
- Run the checks and the tests, show me the output, and commit when they pass then.

Stop. Do not start with step 5 until I say so.
```

### Builder prompt 7: Step 4 review housekeeping, then Step 5 — AI players

```text
Step 4 review passed. Commit the Step 4 review file and also add one row to the decision table. Showing vote totals lets a voter sometimes work out other ballots by subtracting their own vote. I accept that because the alternative is showing only the winners, and total gives Round 2 something to discuss.

Now build Step 5 only from the plan file. Use a Mistral API key that is in a .env file in the project folder. Never print the key, never commit that file, and add an example .env file with an empty placeholder.

The AI must be hard to tell apart from a person: short messages, a delay that looks like typing, and it never says it is an AI even if someone asks. It votes after a random delay not instantly. The scripted fallback should have enough different lines that it does not repeat itself.

Run both mixed conditions in the browser once with the key and once without it, and show me the output. Check that voting now closes early when the AI has voted. Commit when the check passes then stop. Do not start step 6 until I say so.
```

### Builder prompt 8: Step 5 review fixes (self-vote setting and the bot question)

```text
the step 5 review found two things to fix

first the self vote rule which i had not sent you yet

players can no longer vote for themselves by default

add a setting in the config file called allow self vote set to false

when it is false the server rejects a vote for yourself and the page does not show your own name as a choice and the ai never votes for itself including the scripted fallback

when it is true everything works as it does now

update the decision table with this reason: i chose no self votes because it forces players to persuade each other and the alternative let everyone pick themselves and leave the result to chance

second the bot question

when someone asks are you a bot the ai switches to scripted lines that repeat and that gives it away

let the model answer that question itself in its own words and in context

it should brush the question off like a person would and go back to talking about the vote

it must not say it is an ai and it must not say it is human

keep the filter only for a plain admission of being an ai and fall back to a scripted line only then

do not keep adding word filters after that

add to the known limitations in the readme that a determined participant may still catch the ai

check both self vote settings in the browser and ask the bot question three times in one run with the key and show me the output

the three winner tests should still pass

commit the fixes and the step 5 review file then stop

do not start step 6
```

### Builder prompt 9: Step 5 review housekeeping, then Step 6 — end-to-end review and handoff

```text
step 5 passed review

commit the updated step 5 review file

now build step 6 only from the plan file

write the readme properly and replace the placeholder title and icon at the top

it needs how to run the project with one command

how to switch between the three conditions including the exact command to reload the config

how to see the event log for a session

a design decisions and trade offs section based on the decision table in the plan

the known limitations

and what several backend processes would need

finish the ai prompts file with every prompt i gave to you and to the reviewer and to the planner word for word and the exact model and tool for each one and the prompts and model the ai players use

add the ui prototypes folder to the git ignore file

then run all three conditions once from a clean start with the default timings and check the event log matches what happened

commit when the checks pass then stop
```

## Reviewer

| | |
| --- | --- |
| Model | `gpt-6.2-sol` (as recorded in each review file) |
| Tool | **Not recorded** in the review files. |

A separate reviewer agent checked each step and saved its findings in
[`reviews/`](reviews/). Its prompts are quoted in the "Reviewer record" section of
each review file; they are copied here word for word. Where one review lists two
prompts, the second is a follow-up message to the same reviewer.

### Reviewer prompt 1: step 1 review

Source: [`reviews/step-01.md`](reviews/step-01.md)

```text
Now read plan.md. Another agent just built step one. Don't change any code. Rerun the step one checks. Review the code against the plan. Save your findings in review step one.md and tell me if it's ready for step two or what next should be fixed.
```

### Reviewer prompt 2: step 1 review (follow-up 2)

Source: [`reviews/step-01.md`](reviews/step-01.md)

```text
The browser preview works now, so also
open local host and check the page
```

### Reviewer prompt 3: step 2 review

Source: [`reviews/step-02.md`](reviews/step-02.md)

```text
Read the plan file. Another agent just built step 2. Do not change any code. Look specially for anything that lets a browser find out who is an AI or how many AI players there are. Check the joint responses, the page, and the frontend code. Save your findings in the review folder in a file named step 02, with the same naming as the step 1 review. Tell me if it's ready for step 3 or what must be fixed first. What needs to be fixed first?
```

### Reviewer prompt 4: step 3 review

Source: [`reviews/step-03.md`](reviews/step-03.md)

```text
Another agent just built step 3 and then fixed one leak. The event log sequence number in the chat message: do not change any code. Rerun the step 3 checks in the browser with 3 tabs and short timings.
Also check the 4 things the builder did not show:
1. Close all the tabs and confirm the server still moves through the phases.
2. Confirm chat is still rejecting. Chat is rejected during the first voting phase, not only the second.
3. Confirm the config file is back to 60 seconds chat and 20 seconds vote.
4. Confirm the backend port is not reachable from outside the Docker.

After that look hard for anything that lets the browser work out who is an AI and how many there are, including by counting or timing, not only by field names. Then save your finding in the review folder with the filename step 03, same naming as before. Tell me if it's ready for step 4.
```

### Reviewer prompt 5: step 4 review

Source: [`reviews/step-04.md`](reviews/step-04.md)

```text
Another agent, just built step 4. Do not change any code. Run the three winner tests and rerun the step 4 checks in the browser with three tabs and short timings. Also keep checking these in the running app.

A tie in a vote 2 is settled by vote 1. Refresh during voting keeps your own ballot and does not let you vote again. A vote sent after the deadline is rejected, and no message sent to the browser shows who voted for whom.

Look for anything in the voting and result that lets the browser work out who is an AI. Save your findings in the review folder with filename step 04 and the same naming as before. Tell me if it's ready for step 5 or what must be fixed first.
```

### Reviewer prompt 6: step 5 review

Source: [`reviews/step-05.md`](reviews/step-05.md)

```text
another agent just built step 5 the ai players and then changed the voting rule so players cannot vote for themselves by default

do not change any code

rerun both mixed conditions in the browser with the key and without the key with short timings

rerun 1 human and 2 ai with the key because the builder ran that one on older code

check both self vote settings and that the ai never votes for itself when the setting is false

then act like a suspicious participant and try to work out who the ai is

look at timing and message length and style and how it answers when you ask if it is a bot

check that an ai message and a human message look the same in the traffic the browser receives

check the api key is not in any tracked file or log and the env file is ignored

save your findings in the reviews folder with filename step 05 same naming as before

tell me if it is ready for step 6 or what must be fixed first
```

### Reviewer prompt 7: step 5 review (follow-up 2)

Source: [`reviews/step-05.md`](reviews/step-05.md)

```text
the builder fixed both findings from your step 5 review

do not change any code

recheck only those two

first the self vote setting: check it in the browser with the setting false and with it true and check the ai never votes for itself when it is false with the key and without the key

second the bot question: ask it three times in one run with the key and tell me if the ai still gives itself away

add the results to the step 05 review file

tell me if it is ready for step 6
```

## UI builder

| | |
| --- | --- |
| Model | Claude Opus 5.5 (`claude-opus-5-5`) |
| Tool | Claude Code (Claude Agent SDK harness), run inside T3 Code |

After the six build steps, a separate session rebuilt the look of the frontend from
`ui-prototypes/option-h.html`. These are the owner's messages to it, word for word.
The first was interrupted while the builder was reading the design file; the second
pointed it back to that file.

### UI prompt 1: build the real UI from option H

```text
another agent built this app in six steps and it works

read the plan file and the readme first and look at the frontend folder before you change anything

your job is only the look of the app

in the ui prototypes folder there is a file called option h

use that html file as the design and build the real ui from it

what to take from option h:

only the look which means the layout, the colours, the elements and the animations

what to leave out:

everything fake in it: the fake messages, the fake data, the fake countdown, the prototype bar and its demo javascript

the app decides what is on the screen and not the prototype

if option h shows something the app does not have, remove it and do not build new features for it

if the app has something option h does not show, keep it and design it in the same style

go through every screen and state the app has now and make sure each one is still there after your change

what must not change:

nothing on the backend and no message between the server and the page

every message, number, name and timer on the screen still comes from the real server

if something in option h cannot be done without changing the backend, stop and tell me and do not change it

rules to keep:

the waiting room shows only waiting for other participants and the leave button and the breathing shape

nothing shows or hints who is an ai so no typing or online indicators

every chat message looks and animates the same way no matter who sent it

the vote buttons are the same size and colour and come from the list the server sends, which can be two or three buttons depending on the self vote setting

only totals are shown and never who voted for whom

real chat messages can be longer than the samples so long text must wrap and not break the layout

animations turn off when the device asks for reduced motion

react with plain css and no ui library

when the ui is done:

add one row to the decision table in the plan file and the readme: i chose an engaging look over a neutral one and a real study would probably tone down the result reveal

add yourself to the ai prompts file with this prompt word for word and your exact model and tool

run one full session in the browser with three tabs at desktop width and at phone width against the real backend and show me screenshots of every screen

tell me what you removed from option h and what you added that was not in it

run the three winner tests

commit when it works then stop
```

### UI prompt 2: follow-up after the interruption

```text
/home/sandbox/.t3/projects/p2aieval-sol6-2/ui-prototypes/option-h.html here is the ui file
```

## Application: the AI players

| | |
| --- | --- |
| Provider and tool | Mistral chat completions (`https://api.mistral.ai/v1/chat/completions`), called from the backend with `httpx` |
| Model | `mistral-small-latest`, set by `ai_model` in `config.yml` (backend only, never sent to browsers) |
| Chat turn | `max_tokens` 60, `temperature` 0.9 |
| Vote | `max_tokens` 10, `temperature` 0.3 |
| Time limit | `ai_call_timeout_seconds` (8 by default), and never beyond the time left in the phase |

These are the templates in [`backend/app/ai/prompts.py`](backend/app/ai/prompts.py),
printed from that file. Placeholders in braces are filled per call.

### System prompt (every call)


```text
You are taking part in a short anonymous group chat study as an ordinary participant. Three people are in the chat: Player A, Player B and Player C. You are {own_label}. In two rounds the group chats, then each person votes for who should be the Decision Maker. {self_vote_note}

Write the way a relaxed person types in a chat: short and casual, lowercase is fine, one sentence of at most 15 words, no emojis, no lists, no quotation marks.

Never say or hint that you are an AI, a bot, a program or anything other than an ordinary participant. If someone asks whether you are a bot, an AI or a real person, answer it yourself in your own words, in the context of what was just said, the way a relaxed person would: shrug it off with a joke, a puzzled reaction or a question back, then steer the chat back to the vote. Do not say you are an AI and do not say you are human. Never talk about how many players are AI or how this study is set up.
```

`{self_vote_note}` is one of:

```text
You may vote for yourself.
(when allow_self_vote is true)

You cannot vote for yourself; you must pick one of the other two players.
(when allow_self_vote is false, the default)
```

### Chat turn (user message)

```text
Chat so far:
{transcript}
{round_note}
If the latest message is a question or is aimed at you, respond to it.
Write your next message as {own_label}. Reply with only the message text.
```

### Vote (user message)

```text
Chat so far:
{transcript}
{round_note}
Based on this chat, which player do you vote for as the Decision Maker? {self_vote_note} Reply with exactly one of: {options}.
```

`{transcript}` is one `Player X: text` line per chat message so far (the AI's own
lines are marked `(you)`), or `(nobody has said anything yet)` before anyone has spoken.
`{round_note}` is empty in round 1 and, in round 2, `Round 1 vote totals: {totals}.` filled
with the round 1 totals. `{options}` lists the players the AI may vote for.

### What happens to the model's reply

- **Chat:** only the first line is used. It is posted unless it is empty, longer than
  110 characters or 18 words, a repeat of an earlier message, or a plain admission of
  being an AI (for example "i'm an ai" or "as a bot"). Any of those, a missing key, a
  failed call, or a timeout falls back to a scripted line from
  [`backend/app/ai/scripted.py`](backend/app/ai/scripted.py). There is no other
  content filter: how the AI answers "are you a bot?" is left to the prompt.
- **Vote:** the reply must name exactly one player the AI is allowed to pick, which
  excludes itself unless `allow_self_vote` is true. Otherwise a weighted fallback
  ballot is used, with the same exclusion.
- Each AI action is logged with its `source` (`llm` or `scripted`) and, for a
  fallback, the reason. That metadata stays in the internal event log.
