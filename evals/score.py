#!/usr/bin/env python3
"""Score what can be scored automatically, for every model in a results folder.

    evals/score.py evals/results/2026-11-26

- coding: the last ```python block of each answer is saved as solution.py and the task's
  hidden test.py is run against it, in a fresh temporary folder, with no network when
  `unshare` allows it, a time limit and memory and CPU limits.
- playground: whether the reply is a JSON object with every required key.
- a few chat and creative tasks with checkable constraints (word counts, a JSON-only
  reply), noted in the task's "auto" field or implied by its id.

Writes <results>/auto.json and prints a table. Standard library only.
"""
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from run import load_tasks  # noqa: E402

FENCE = re.compile(r"```([A-Za-z0-9_+-]*)[ \t]*\n(.*?)```", re.S)


def extract_code(answer: str) -> str:
    """The last ```python block, else the last fenced block, else the whole answer."""
    blocks = FENCE.findall(answer)
    py = [body for lang, body in blocks if lang.lower() in ("python", "py", "python3")]
    if py:
        return py[-1]
    if blocks:
        return blocks[-1][1]
    return answer


def _limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 << 30, 2 << 30))
    resource.setrlimit(resource.RLIMIT_CPU, (120, 120))


def _no_network_prefix():
    if shutil.which("unshare"):
        probe = subprocess.run(["unshare", "-rn", "true"], capture_output=True)
        if probe.returncode == 0:
            return ["unshare", "-rn"]
    return []


_PREFIX = None


def run_tests(task_dir: str, code: str, timeout: int = 180) -> dict:
    """Run a coding task's hidden tests against `code`. Returns passed, ran, failed."""
    global _PREFIX
    if _PREFIX is None:
        _PREFIX = _no_network_prefix()
    work = tempfile.mkdtemp(prefix="eval-code-")
    try:
        with open(os.path.join(work, "solution.py"), "w", encoding="utf-8") as fh:
            fh.write(code)
        shutil.copy(os.path.join(task_dir, "test.py"), work)
        try:
            p = subprocess.run(_PREFIX + [sys.executable, "-E", "-s", "test.py"], cwd=work,
                               capture_output=True, text=True, timeout=timeout,
                               preexec_fn=_limits, env={"PATH": "/usr/bin:/bin"})
            out = p.stdout + p.stderr
            code_ = p.returncode
        except subprocess.TimeoutExpired:
            return {"passed": False, "ran": 0, "failed": 0, "note": "timed out"}
    finally:
        shutil.rmtree(work, ignore_errors=True)
    ran = re.search(r"Ran (\d+) tests?", out)
    bad = re.search(r"FAILED \(([^)]*)\)", out)
    failed = sum(int(n) for n in re.findall(r"=(\d+)", bad.group(1))) if bad else 0
    note = "" if code_ == 0 else out.strip().splitlines()[-1][:200] if out.strip() else "no output"
    return {"passed": code_ == 0, "ran": int(ran.group(1)) if ran else 0,
            "failed": failed, "note": note}


def words(text: str) -> int:
    return len(re.findall(r"\b[\w'’-]+\b", text))


def auto_checks(task: dict, content: str) -> dict:
    """Checkable constraints for chat, creative and playground answers."""
    tid, out = task["id"], {}
    if task["category"] == "playground":
        try:
            obj = json.loads(content)
            req = task["schema"].get("required", [])
            out["valid_json"] = isinstance(obj, dict) and all(k in obj for k in req)
        except ValueError:
            out["valid_json"] = False
    elif task.get("auto") == "json_array_5":
        try:
            arr = json.loads(content.strip())
            out["json_only_5"] = (isinstance(arr, list) and len(arr) == 5 and all(
                isinstance(o, dict) and set(o) == {"tip", "why"} for o in arr))
        except ValueError:
            out["json_only_5"] = False
    limits = {"explain_public_key": (0, 200), "email_decline_offer": (0, 150),
              "flash_lighthouse": (200, 300), "blurb_bike_lock": (60, 80),
              "world_walking_city": (0, 300)}
    if tid in limits:
        lo, hi = limits[tid]
        n = words(content)
        out["words"] = n
        out["length_ok"] = lo <= n <= hi * 1.05     # a 5% allowance for counting differences
    if tid == "poem_server_room":
        lines = [l for l in content.strip().splitlines() if l.strip() and not l.startswith("#")
                 and not l.strip().startswith("**")]
        low = content.lower()
        out["lines"] = len(lines)
        out["constraints_ok"] = (len(lines) == 14 and len(re.findall(r"\blantern\b", low)) == 1
                                 and "silence" not in low)
    if tid == "blurb_bike_lock":
        out["no_exclamation"] = "!" not in content
    if tid == "summarise_minutes":
        bullets = [l for l in content.splitlines() if re.match(r"\s*([-*•]|\d+[.)])\s", l)]
        out["three_bullets"] = len(bullets) == 3
    return out


def main(argv=None):
    results = (argv or sys.argv[1:])[0]
    tasks = {t["id"]: t for t in load_tasks()}
    report = {}
    for name in sorted(os.listdir(results)):
        if not name.endswith(".jsonl"):
            continue
        model = name[:-6]
        rows = []
        with open(os.path.join(results, name), encoding="utf-8") as fh:
            for line in fh:
                row = json.loads(line)
                if row.get("error"):
                    continue
                task = tasks[row["task"]]
                scored = {"task": row["task"], "sample": row["sample"],
                          "category": row["category"], "level": row.get("level"),
                          "finish_reason": row.get("finish_reason")}
                if task["category"] == "coding":
                    scored.update(run_tests(task["dir"], extract_code(row["content"])))
                scored.update(auto_checks(task, row["content"]))
                rows.append(scored)
        report[model] = rows
        coding = [r for r in rows if r["category"] == "coding"]
        by_level = {}
        for r in coding:
            by_level.setdefault(r["level"], []).append(r["passed"])
        parts = [f"{lvl} {sum(v)}/{len(v)}" for lvl, v in sorted(by_level.items())]
        pg = [r["valid_json"] for r in rows if "valid_json" in r]
        cut = sum(1 for r in rows if r.get("finish_reason") == "length")
        print(f"{model}: coding {', '.join(parts)}; playground JSON {sum(pg)}/{len(pg)}; "
              f"cut off by max_tokens {cut}")
    with open(os.path.join(results, "auto.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1)


if __name__ == "__main__":
    main()
