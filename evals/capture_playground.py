#!/usr/bin/env python3
"""Capture real agent-playground prompts for the eval suite.

Runs the playground's own game code on a scratch copy of its data folder, with the model
call (`playground.llm.ask`) replaced by a recorder. Every call's system prompt, prompt and
JSON schema is written to a JSONL file, so the eval asks local models exactly what a game
would. Nothing is written to the playground's real data.

    capture_playground.py outlast <data dir> <game id> <out.jsonl> [--calls N]
        Resume a copy of an unfinished Outlast game from its saved state.
    capture_playground.py werewolf <data dir> <out.jsonl> [--calls N]
        Start a Werewolf game with the copied cast and memories.

Answers come from a Claude model (--model, default haiku) through the playground's own
`claude -p` path, so later prompts carry a believable history. That uses the Claude plan,
about one call per record. --fake answers with the playground's canned lines instead:
free, but the canned lines then show up in later prompts.

Standard library only. The playground checkout is ~/src/agent-playground, or
PLAYGROUND_SRC.
"""
import argparse
import json
import os
import shutil
import sys
import tempfile
import threading
import time

PLAYGROUND_SRC = os.environ.get("PLAYGROUND_SRC", os.path.expanduser("~/src/agent-playground"))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("game", choices=["outlast", "werewolf"])
    ap.add_argument("data", help="the playground's data folder (copied, never written)")
    ap.add_argument("rest", nargs="+", help="outlast: <game id> <out>; werewolf: <out>")
    ap.add_argument("--calls", type=int, default=120, help="stop after this many calls")
    ap.add_argument("--model", default="haiku", help="Claude model that answers")
    ap.add_argument("--fake", action="store_true", help="answer with canned lines")
    args = ap.parse_args(argv)
    if args.game == "outlast" and len(args.rest) != 2:
        ap.error("outlast needs <game id> <out.jsonl>")
    if args.game == "werewolf" and len(args.rest) != 1:
        ap.error("werewolf needs <out.jsonl>")
    out_path = os.path.abspath(args.rest[-1])

    scratch = tempfile.mkdtemp(prefix="pg-capture-")
    data = os.path.join(scratch, "data")
    shutil.copytree(args.data, data)
    os.environ["PLAYGROUND_DATA"] = data
    os.environ["PLAYGROUND_PACE"] = "0"
    os.environ.pop("PLAYGROUND_FAKE", None)
    sys.path.insert(0, PLAYGROUND_SRC)
    from playground import llm                      # noqa: E402
    from playground.server import Playground        # noqa: E402

    real_ask = llm.ask
    lock = threading.Lock()
    count = [0]
    done = threading.Event()
    out = open(out_path, "w", encoding="utf-8")

    def recorder(model, system, prompt, schema, effort="low", timeout=120):
        with lock:
            if count[0] >= args.calls:
                done.set()
                raise llm.LLMError("error", "capture finished")
            count[0] += 1
            out.write(json.dumps({"game": args.game, "seat": model, "system": system,
                                  "prompt": prompt, "schema": schema}) + "\n")
            out.flush()
        if not args.fake:
            return real_ask(args.model, system, prompt, schema, effort=effort,
                            timeout=timeout)
        return llm._fake(schema), {"model": model, "seconds": 0.0, "cost": 0.0}

    llm.ask = recorder
    pg = Playground(PLAYGROUND_SRC)
    if args.game == "outlast":
        pg.resume_game(args.rest[0])
    else:
        pg.start_game("werewolf")
    while not done.is_set() and pg.active():
        time.sleep(1)
    out.close()
    shutil.rmtree(scratch, ignore_errors=True)
    print(f"{count[0]} calls recorded to {out_path}")
    os._exit(0)   # the game thread is a daemon; don't wait for it


if __name__ == "__main__":
    main()
