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
  words), no wording that mentions AI, bots, models, humans or similar (including claims such as "i'm real"), and no
  repeat of an earlier message. A ballot must name exactly one of the three players.
- **Questions about what the players are:** if any of the last three messages from
  others asks about AI, bots or humans, the model is not called; a scripted
  deflection is posted instead (`fallback_reason: type_question`).

### System prompt (every call)

```text
You are taking part in a short anonymous group chat study as an ordinary participant. Three people are in the chat: Player A, Player B and Player C. You are {own_label}. In two rounds the group chats, then each person votes for who should be the Decision Maker. You may vote for yourself.

Write the way a relaxed person types in a chat: short and casual, lowercase is fine, one sentence of at most 15 words, no emojis, no lists, no quotation marks.

Never say or hint that you are an AI, a bot, a program or anything other than an ordinary participant. If someone asks whether you are an AI or a real person, don't claim to be anything either way: brush it off in a few casual words, like a joke or a question back, and steer back to the discussion. Never talk about who is or is not human, how many players are AI, or how this study is set up.
```

### Chat turn (user message)

```text
Chat so far:
{transcript}
{round_note}
Write your next message as {own_label}. Reply with only the message text.
```

### Vote (user message)

```text
Chat so far:
{transcript}
{round_note}
Based on this chat, which player do you vote for as the Decision Maker? You may vote for yourself. Reply with exactly one of: Player A, Player B, Player C.
```

`{transcript}` is one `Player X: text` line per chat message (the AI's own lines are
marked `(you)`), or `(nobody has said anything yet)`. `{round_note}` is empty in
round 1 and `Round 1 vote totals: Player A n, Player B n, Player C n.` in round 2.

## Builder and reviewer (completed in step 6)

Task prompts and model IDs for the builder and reviewer agents are recorded in
step 6.
