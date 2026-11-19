import random
import re

# Used only when there is no API key or a model call fails or is unusable. Lines are
# short and casual, never mention what the speaker is, and {p} is filled with another
# player's label. Pools are large so a run does not repeat itself.

OPENERS = [
    "hey all", "hi everyone", "hello! so how are we doing this", "hey, not sure what to expect here",
    "hi, anyone got a plan for who we pick?", "hey hey", "hi! this is a weird setup", "hello, hope this goes quick",
    "hey, so we just chat then vote?", "hi there, what's everyone thinking", "hey, first time doing something like this",
    "morning all, or whatever time it is", "hi, ready when you are", "hello folks", "hey, so who's going first",
]

ROUND_ONE = [
    "i guess we pick whoever seems most sensible", "does anyone have a strategy or are we winging it",
    "honestly i'd go with whoever's been most active", "i don't really mind who it is",
    "i'm leaning towards picking someone random tbh",
    "let's not overthink this", "i'll just go with my gut when voting", "anyone else find the timer stressful",
    "{p} you've been quiet, what do you think", "what's your reasoning so far {p}", "i kind of like {p}'s approach",
    "{p} seems pretty sensible so far", "not sure yet who i'll pick", "what makes someone a good decision maker anyway",
    "fair point", "yeah that makes sense", "ha good point", "same here", "i was thinking something similar",
    "hmm hard to say", "can't decide yet", "waiting to see what others say", "keeping an open mind for now",
    "i'm open to anyone really", "maybe we should each say who we're leaning towards", "i'd rather not rush it",
    "anyone have a favourite so far", "{p} what would you do", "i think {p} makes a fair point",
    "this is going faster than i thought", "i'll wait and see how the chat goes",
]

ROUND_TWO = [
    "so the totals are interesting", "didn't expect those numbers", "so {p} got some votes, why do you think",
    "i voted based on the chat honestly", "anyone changing their mind after seeing the totals",
    "good to see where everyone stands", "i might stick with my first pick", "interesting split",
    "that wasn't what i expected", "let's see how this round goes", "i'll think about who talked the most sense",
    "{p} what made you pick who you picked", "the totals make this harder to call", "same plan as before for me",
    "i'll try to be consistent", "this round feels more serious somehow", "i could be swayed if someone makes a good case",
    "still undecided honestly", "{p} are you sticking with your vote", "those numbers are closer than i thought",
    "i don't think the totals settle it", "let's hear some reasons then", "i'm still weighing it up",
    "someone convince me", "kind of surprised by the first round", "i'd like to hear from {p} again",
    "not changing my mind yet", "{p} do the totals change anything for you",
]

REPLIES = [
    "good question, not sure", "hm what do you think", "no idea honestly", "maybe, depends", "probably",
    "hard to tell", "ha you tell me", "i'd say so", "could be", "not sure, you?",
]

DEFLECTIONS = [
    "lol why does that matter", "ha does it matter? let's just pick someone", "that's a weird thing to ask",
    "not getting into that, let's focus on the vote", "haha what makes you ask", "doesn't change who we vote for does it",
    "ok that's random, anyway", "i could ask you the same", "let's just stick to the decision",
    "ha nice try, back to the vote", "why are you asking that", "that's not really the point here",
    "uh, random. anyway who are we picking", "you ask the strangest things", "lol is that your strategy",
    "can we talk about the vote instead", "what would that change though", "ok but who are you voting for",
    "haha you first", "pretty sure that isn't in the rules", "weird question but sure, whatever",
    "i came here to vote not to be interrogated", "right, so about the vote", "ha what, no. who do you like",
]

# A message asking about what someone is, however it is worded.
ASKS_ABOUT_TYPE = re.compile(
    r"\b(ais?|bots?|robots?|humans?|real person|real people|chatgpt|gpt|machines?|computers?|programs?|fake|"
    r"artificial|language model)\b|are (you|either|any|none|all)\b[^?]*\b(real|person|people)",
    re.IGNORECASE,
)


def pick_line(
    round_number: int,
    own_label: str,
    others: list[str],
    last_other_text: str | None,
    nobody_spoke: bool,
    used: set[str],
    previous: list[str],
    rng: random.Random,
) -> str:
    """Choose a line not yet used in this run, matched loosely to the moment.
    `used` records both the raw template and the filled line, so a template with a
    {p} slot is not reused under another name; `previous` is the chat so far."""
    if last_other_text and ASKS_ABOUT_TYPE.search(last_other_text):
        pools = [DEFLECTIONS]
    elif last_other_text and last_other_text.rstrip().endswith("?") and rng.random() < 0.5:
        pools = [REPLIES, ROUND_TWO if round_number == 2 else ROUND_ONE]
    elif nobody_spoke and round_number == 1:
        pools = [OPENERS]
    else:
        pools = [ROUND_TWO if round_number == 2 else ROUND_ONE]
    pools.append(ROUND_TWO if round_number == 2 else ROUND_ONE)
    pools.append(REPLIES)

    seen = {p.lower() for p in previous}
    for pool in pools:
        fresh = [raw for raw in pool if raw not in used]
        rng.shuffle(fresh)
        for raw in fresh:
            line = _fill(raw, others, rng)
            if line not in used and line.lower() not in seen:
                used.update((raw, line))
                return line
    raw = rng.choice(ROUND_ONE + ROUND_TWO)  # every pool is exhausted
    return _fill(raw, others, rng)


def _fill(line: str, others: list[str], rng: random.Random) -> str:
    return line.replace("{p}", rng.choice(others)) if "{p}" in line else line


def fallback_ballot(
    own_label: str, message_authors: list[str], allow_self_vote: bool, rng: random.Random
) -> str:
    """A ballot weighted toward whoever has spoken more, so it follows the chat a
    little. Never names the voter when self-voting is off."""
    labels = [l for l in ("Player A", "Player B", "Player C") if allow_self_vote or l != own_label]
    weights = [1 + message_authors.count(label) for label in labels]
    return rng.choices(labels, weights=weights, k=1)[0]
