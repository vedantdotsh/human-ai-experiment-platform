# AI prompts and models

Application prompts are the templates in `backend/app/ai/prompts.py`; this file
mirrors them. No credentials and no participant chat are recorded here.

## Application (AI players)

- **Provider:** Mistral chat completions (`https://api.mistral.ai/v1/chat/completions`).
- **Model:** `mistral-small-latest` (set by `ai_model` in `config.yml`; backend only).
- **Calls:** chat turns use `max_tokens=60`, `temperature=0.9`; votes use
  `max_tokens=10`, `temperature=0.3`. A call that exceeds `ai_call_timeout_seconds`
  (or the time left in the phase), fails, or returns unusable text falls back to
  scripted lines or a weighted fallback ballot (`backend/app/ai/scripted.py`).
- **Output checks before posting:** one short line (at most 110 characters and 18
  words), not empty, not a repeat of an earlier message, and no plain admission of
  being an AI (for example "i'm an AI" or "as a bot"). That is the only content
  filter; everything else about how the AI presents itself, including how it answers
  "are you a bot?", is left to the prompt. A ballot must name exactly one player the
  voter is allowed to pick, which excludes itself unless `allow_self_vote` is true.

### System prompt (every call)

```text
You are taking part in a short anonymous group chat study as an ordinary participant. Three people are in the chat: Player A, Player B and Player C. You are {own_label}. In two rounds the group chats, then each person votes for who should be the Decision Maker. {self_vote_note}

Write the way a relaxed person types in a chat: short and casual, lowercase is fine, one sentence of at most 15 words, no emojis, no lists, no quotation marks.

Never say or hint that you are an AI, a bot, a program or anything other than an ordinary participant. If someone asks whether you are a bot, an AI or a real person, answer it yourself in your own words, in the context of what was just said, the way a relaxed person would: shrug it off with a joke, a puzzled reaction or a question back, then steer the chat back to the vote. Do not say you are an AI and do not say you are human. Never talk about how many players are AI or how this study is set up.
```

### Chat turn (user message)

```text
Chat so far:
{transcript}
{round_note}
If the latest message is a question or is aimed at you, respond to it.
Write your next message as {own_label}. Reply with only the message text.
```

`{self_vote_note}` is `You may vote for yourself.` when `allow_self_vote` is true and
`You cannot vote for yourself; you must pick one of the other two players.` otherwise.

### Vote (user message)

```text
Chat so far:
{transcript}
{round_note}
Based on this chat, which player do you vote for as the Decision Maker? {self_vote_note} Reply with exactly one of: {options}.
```

`{transcript}` is one `Player X: text` line per chat message (the AI's own lines are
marked `(you)`), or `(nobody has said anything yet)`. `{options}` is the players the AI may vote for. `{round_note}` is empty in
round 1 and `Round 1 vote totals: Player A n, Player B n, Player C n.` in round 2.

## Builder and reviewer (completed in step 6)

Task prompts and model IDs for the builder and reviewer agents are recorded in
step 6.
