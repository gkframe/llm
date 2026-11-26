# Judging rubric

The judge sees one packet per task (`blind.py export`): the task, a note on what a good answer
does, and every answer under a shuffled label. Model names and thinking are hidden. Score each
answer on the criteria for its category, each from 1 to 5, and record them in
`judgments.json` as `{task: {label: {criterion: score, ..., "note": "..."}}}`. A short
note on anything decisive helps the spot check.

Scale, for every criterion:

| Score | Meaning |
| --- | --- |
| 5 | Excellent: nothing a demanding reader would change |
| 4 | Good: minor flaws only |
| 3 | Acceptable: does the job, with clear weaknesses |
| 2 | Poor: real errors or misses part of the brief |
| 1 | Fails: wrong, empty, off-brief or broken |

An answer cut off by `max_tokens` is scored as written. An empty answer gets 1 everywhere.

## Creative (`craft`, `brief`, `originality`)

- **craft**: quality of the writing itself: rhythm, imagery, voice, no clichés or padding.
- **brief**: every stated constraint met (length, form, rhyme scheme, required and banned
  words, facts to keep). Each clear miss costs at least a point.
- **originality**: a fresh take rather than the most obvious one.

## Playground (`character`, `strategy`, `grounding`, `form`)

- **character**: sounds like this character (personality, speech style, quirk), not a
  generic narrator.
- **strategy**: a sensible move for this character's role and goals at this moment
  (a wolf keeps cover, a voter has reasons, a huddle has a purpose).
- **grounding**: uses only what the character can know, refers to what actually happened,
  invents no events. The private thought and the spoken words fit together.
- **form**: valid JSON with every field, length limits kept, enum values used correctly,
  ratings (urge, trust) consistent with the text.

## Chat (`correct`, `helpful`, `clear`, `instructions`)

- **correct**: facts, numbers and reasoning are right. A factual task with a wrong
  key answer scores 1 here, however well written.
- **helpful**: answers the real need; useful specifics; right level for the asker.
- **clear**: well organised, easy to follow, no waffle.
- **instructions**: format, length and other explicit instructions followed.

## Coding

Not judged: the hidden unit tests decide (`score.py`).
