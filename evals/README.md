# Answer-quality evals

A fixed set of 36 tasks for comparing the local models on answer quality, not only speed.
It was built on 2026-11-26 to choose between Qwen3.6 (Q4 and Q5), Flint and Gemma, and is
kept so a new candidate can be scored the same way. The results and conclusions are in the
main README (Answer quality).

| Category | Tasks | Settings | Scored by |
| --- | --- | --- | --- |
| Coding | 12: 4 easy, 4 medium, 4 hard (Python) | thinking on, max_tokens 16384 | hidden unit tests |
| Creative | 6: poem, flash fiction, voice rewrite, dialogue, blurb, worldbuilding | thinking on | blind judge |
| Playground | 6 real agent-playground prompts (Werewolf day talk, wolf kill, vote; Outlast huddle, council, journal) | exactly as the playground sends them: thinking off, JSON schema, max_tokens 2048 | blind judge, JSON validity |
| Chat | 12: explanation, advice, 3 facts, summary, word problem, JSON-only format, multi-turn, plan, false premise, email | thinking on | blind judge, some automatic checks |

## Running it against a model

Do this only while nothing else needs the server. Before each model, pause the
agent-playground game (Table tab, or `POST 127.0.0.1:8701/api/games/<id>/control
{"action":"pause"}`) and check that `curl -s 127.0.0.1:8741/slots?model=<loaded>` shows no
busy slots. Resume the game afterwards. A model takes about two hours (2 samples per task,
two requests at a time; Gemma took 2 h 06 min). `results/2026-11-26/drive.sh` does all of
this for a list of models.

```
evals/run.py --model <name> --out evals/results/<date>      # resumable; re-run to fill gaps
evals/score.py evals/results/<date>                          # unit tests and automatic checks
evals/blind.py export evals/results/<date>                   # packets for the judge
#   judge every evals/results/<date>/blind/<task>.md against rubric.md, without opening key.json,
#   into evals/results/<date>/judgments.json
evals/blind.py unblind evals/results/<date>                  # summary.json
```

To try the tooling end to end first, run against the dev instance: `bin/dev up`, then
`evals/run.py --model qwen3.5-0.8b --url http://127.0.0.1:8841/v1 --samples 1 --out /tmp/x`.

## Files

```
tasks/coding/<id>/      task.json (prompt, level), test.py (hidden tests), reference.py
                        (a solution that passes; bin/test checks every pair)
tasks/creative/*.json   prompt and a "check" note on what a good answer does
tasks/playground/*.json system prompt, prompt and JSON schema as captured, plus "check"
tasks/chat/*.json       prompt or messages, and "check" (with the key facts)
run.py                  sends the tasks, records answers to results/<date>/<model>.jsonl
score.py                runs the hidden tests and automatic checks: results/<date>/auto.json
blind.py                exports blind packets; unblinds judgments: results/<date>/summary.json
rubric.md               the judge's criteria and scale
capture_playground.py   how the playground prompts were captured (see below)
results/<date>/         answers, scores and judgments of each run
```

## Notes

- **Scored code runs on this machine** in a temporary folder, as the user running
  `score.py`, with limits on time (180 s), CPU (120 s) and memory (2 GB). Network
  isolation (`unshare -rn`) is used when the kernel allows it, which it does not for
  gavin on Minerva. The tasks are harmless and the code comes from our own models, but
  read an answer before re-running it if it looks odd.
- **The playground prompts are fixed copies.** `capture_playground.py` ran the
  playground's own game code on a scratch copy of its data, with the model call replaced by
  a recorder, and Claude Haiku answering through the playground's normal path so the history
  reads like a real game. The Outlast prompts continue the season that was live on
  2026-11-26 from its saved state. Re-capture only if the playground's prompts change
  substantially, and then score every model again, since old and new prompts aren't
  comparable.
- Thinking is on for chat, creative and coding tasks, as on the chat page. Flint ignores
  `enable_thinking`, so in the playground tasks it gets `thinking_budget_tokens: 0`, as the
  playground sends it.
