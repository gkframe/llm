#!/usr/bin/env python3
"""Blind judging of the open-ended answers (creative, playground, chat).

    evals/blind.py export  evals/results/2026-11-26 [--seed N]
        Writes one packet per task to <results>/blind/<task>.md: the task, what a good
        answer looks like, and every model's answers under shuffled labels (A, B, ...).
        The label-to-model key goes to <results>/blind/key.json; the judge must not read
        it. Thinking is left out: only the final answers are judged.
    evals/blind.py unblind evals/results/2026-11-26
        Reads <results>/judgments.json ({task: {label: {criterion: 1-5, ...}}}), maps
        labels back to models and writes <results>/summary.json: mean score per model,
        overall and per category, plus every judged answer's scores.

Standard library only.
"""
import argparse
import json
import os
import random
import string
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run import load_tasks  # noqa: E402

JUDGED = ("creative", "playground", "chat")
CONTEXT_CHARS = 6000   # how much of a playground prompt's history the packet shows


def read_rows(results):
    rows = {}
    for name in sorted(os.listdir(results)):
        if name.endswith(".jsonl"):
            with open(os.path.join(results, name), encoding="utf-8") as fh:
                for line in fh:
                    row = json.loads(line)
                    if not row.get("error"):
                        rows.setdefault(row["task"], []).append(row)
    return rows


def task_text(task):
    if task["category"] == "playground":
        system, prompt = task["system"], task["prompt"]
        history, _, now = prompt.rpartition("== Now ==")
        return ("**Character sheet (end of the system prompt):**\n\n"
                + system[-2500:].strip()
                + "\n\n**Recent history (end of what the character sees):**\n\n"
                + history[-CONTEXT_CHARS:].strip()
                + "\n\n**Now:**\n\n" + now.strip()
                + "\n\n**Required JSON keys:** " + ", ".join(task["schema"].get("required", [])))
    if "messages" in task:
        return "\n\n".join(f"**{m['role']}:** {m['content']}" for m in task["messages"])
    return task["prompt"]


def labels(n):
    out = list(string.ascii_uppercase)
    return out[:n] if n <= 26 else [f"{a}{b}" for a in out for b in out][:n]


def export(results, seed):
    tasks = {t["id"]: t for t in load_tasks()}
    rows = read_rows(results)
    rng = random.Random(seed)
    outdir = os.path.join(results, "blind")
    os.makedirs(outdir, exist_ok=True)
    key = {}
    for tid, task in tasks.items():
        if task["category"] not in JUDGED or tid not in rows:
            continue
        answers = rows[tid][:]
        rng.shuffle(answers)
        names = labels(len(answers))
        key[tid] = {lab: {"model": a["model"], "sample": a["sample"]}
                    for lab, a in zip(names, answers)}
        parts = [f"# {tid} ({task['category']})", "## Task", task_text(task),
                 "## What a good answer does", task.get("check", ""), "## Answers"]
        for lab, a in zip(names, answers):
            note = " (cut off by max_tokens)" if a.get("finish_reason") == "length" else ""
            parts.append(f"### {lab}{note}\n\n{a['content'].strip() or '(empty)'}")
        with open(os.path.join(outdir, f"{tid}.md"), "w", encoding="utf-8") as fh:
            fh.write("\n\n".join(parts) + "\n")
    with open(os.path.join(outdir, "key.json"), "w", encoding="utf-8") as fh:
        json.dump(key, fh, indent=1)
    print(f"{len(key)} packets in {outdir}")


def unblind(results):
    tasks = {t["id"]: t for t in load_tasks()}
    with open(os.path.join(results, "blind", "key.json"), encoding="utf-8") as fh:
        key = json.load(fh)
    with open(os.path.join(results, "judgments.json"), encoding="utf-8") as fh:
        judgments = json.load(fh)
    answers, totals = [], {}
    for tid, by_label in judgments.items():
        cat = tasks[tid]["category"]
        for lab, scores in by_label.items():
            who = key[tid][lab]
            nums = [v for k, v in scores.items() if isinstance(v, (int, float))
                    and not isinstance(v, bool)]
            mean = sum(nums) / len(nums) if nums else None
            answers.append({"task": tid, "category": cat, "label": lab, **who,
                            "scores": scores, "mean": mean})
            if mean is not None:
                for bucket in ("all", cat):
                    totals.setdefault(who["model"], {}).setdefault(bucket, []).append(mean)
    summary = {model: {b: round(sum(v) / len(v), 2) for b, v in buckets.items()}
               for model, buckets in totals.items()}
    with open(os.path.join(results, "summary.json"), "w", encoding="utf-8") as fh:
        json.dump({"by_model": summary, "answers": answers}, fh, indent=1)
    cats = ["all", *JUDGED]
    print("model".ljust(22) + "".join(c.ljust(12) for c in cats))
    for model, s in sorted(summary.items()):
        print(model.ljust(22) + "".join(str(s.get(c, "-")).ljust(12) for c in cats))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("action", choices=["export", "unblind"])
    ap.add_argument("results")
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args(argv)
    if args.action == "export":
        export(args.results, args.seed)
    else:
        unblind(args.results)


if __name__ == "__main__":
    main()
