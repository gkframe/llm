#!/usr/bin/env python3
"""Run the eval tasks against one model on the llm server and record the answers.

    evals/run.py --model qwen3.6-35b-a3b [--samples 2] [--out evals/results/2026-11-26]
                 [--url http://127.0.0.1:8741/v1] [--only id,id] [--concurrency 2]

Settings match how each kind of task is used for real:
- coding, creative and chat: the model's own sampling settings and its default thinking
  (on), as the chat page sends them, with room for long thinking (max_tokens 16384);
- playground: exactly what agent-playground sends (playground/llm.py `_run_local`):
  thinking off, a zero thinking budget, max_tokens 2048, the reply held to a JSON schema.

Answers go to <out>/<model>.jsonl, one row per task and sample. A run that is stopped
picks up where it left off: rows already recorded without an error are skipped.
Standard library only.
"""
import argparse
import concurrent.futures
import datetime
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = os.path.join(HERE, "tasks")
CODING_SUFFIX = ("\n\nReply with the complete solution in a single ```python code block, "
                 "using only the standard library. Keep any explanation short.")


def load_tasks(root=TASKS):
    """Every task, as dicts with id, category and the rest of the task file."""
    tasks = []
    for cat in ("coding", "creative", "playground", "chat"):
        base = os.path.join(root, cat)
        for name in sorted(os.listdir(base)):
            path = os.path.join(base, name)
            if cat == "coding":
                with open(os.path.join(path, "task.json"), encoding="utf-8") as fh:
                    t = json.load(fh)
                t["dir"] = path
            elif name.endswith(".json"):
                with open(path, encoding="utf-8") as fh:
                    t = json.load(fh)
            else:
                continue
            assert t["category"] == cat, path
            tasks.append(t)
    return tasks


def request_body(task, model):
    """The chat-completions request for one task."""
    if task["category"] == "playground":
        return {
            "model": model,
            "messages": [{"role": "system", "content": task["system"]},
                         {"role": "user", "content": task["prompt"]}],
            "response_format": {"type": "json_schema", "json_schema": {
                "name": "reply", "schema": task["schema"], "strict": True}},
            "chat_template_kwargs": {"enable_thinking": False},
            "thinking_budget_tokens": 0,
            "max_tokens": 2048,
        }
    if "messages" in task:
        messages = task["messages"]
    else:
        prompt = task["prompt"] + (CODING_SUFFIX if task["category"] == "coding" else "")
        messages = [{"role": "user", "content": prompt}]
    return {"model": model, "messages": messages, "max_tokens": 16384}


def call(url, body, timeout):
    req = urllib.request.Request(url.rstrip("/") + "/chat/completions",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as exc:
        return {"error": f"HTTP {exc.code}: {exc.read().decode(errors='replace')[:300]}",
                "seconds": round(time.time() - started, 1)}
    except Exception as exc:   # timeouts, refused connections, cut-off replies
        return {"error": repr(exc)[:300], "seconds": round(time.time() - started, 1)}
    choice = data["choices"][0]
    msg = choice.get("message") or {}
    timings = data.get("timings") or {}
    usage = data.get("usage") or {}
    return {
        "content": msg.get("content") or "",
        "reasoning": msg.get("reasoning_content") or "",
        "finish_reason": choice.get("finish_reason"),
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "write_tok_s": round(timings["predicted_per_second"], 1)
        if timings.get("predicted_per_second") else None,
        "read_tok_s": round(timings["prompt_per_second"], 1)
        if timings.get("prompt_per_second") else None,
        "seconds": round(time.time() - started, 1),
    }


def done_rows(path):
    """(task id, sample) pairs already recorded without an error."""
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if not row.get("error"):
                    done.add((row["task"], row["sample"]))
    return done


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--model", required=True)
    ap.add_argument("--samples", type=int, default=2)
    ap.add_argument("--out", default=os.path.join(HERE, "results",
                                                  datetime.date.today().isoformat()))
    ap.add_argument("--url", default="http://127.0.0.1:8741/v1")
    ap.add_argument("--only", default="", help="comma-separated task ids")
    ap.add_argument("--concurrency", type=int, default=2)
    ap.add_argument("--timeout", type=int, default=1800)
    args = ap.parse_args(argv)

    tasks = load_tasks()
    if args.only:
        wanted = set(args.only.split(","))
        tasks = [t for t in tasks if t["id"] in wanted]
    os.makedirs(args.out, exist_ok=True)
    path = os.path.join(args.out, f"{args.model}.jsonl")
    done = done_rows(path)
    jobs = [(t, s) for s in range(args.samples) for t in tasks if (t["id"], s) not in done]
    print(f"{args.model}: {len(jobs)} to run, {len(done)} already recorded", flush=True)
    lock = threading.Lock()
    failures = 0

    def one(job):
        task, sample = job
        result = call(args.url, request_body(task, args.model), args.timeout)
        row = {"task": task["id"], "category": task["category"], "level": task.get("level"),
               "sample": sample, "model": args.model,
               "at": datetime.datetime.now().isoformat(timespec="seconds"), **result}
        with lock, open(path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        for n, row in enumerate(pool.map(one, jobs), 1):
            if row.get("error"):
                failures += 1
            note = row.get("error") or (
                f"{row['finish_reason']}, {row['completion_tokens']} tokens, "
                f"{row['write_tok_s']} tok/s")
            print(f"[{n}/{len(jobs)}] {row['task']} #{row['sample']}: {row['seconds']}s, {note}",
                  flush=True)
    print(f"{args.model}: finished, {failures} failed", flush=True)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
