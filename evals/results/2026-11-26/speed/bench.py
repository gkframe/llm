#!/usr/bin/env python3
"""Throwaway benchmark helper for the 2026-11-26 Gemma / Qwen Q5 measurements.

    bench.py players            exit 1 and list players if anyone is on a game server
    bench.py mem                iGPU memory in use (GTT + VRAM), GB
    bench.py unload             unload every model on the live server
    bench.py server <model>     the server measurements, as JSON on stdout
"""
import concurrent.futures
import json
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone

URL = "http://127.0.0.1:8741"
TASK = "/home/gavin/src/llm/evals/tasks/playground/ww_vote.json"


def get(path):
    with urllib.request.urlopen(URL + path, timeout=30) as r:
        return json.load(r)


def post(path, body, timeout=900):
    req = urllib.request.Request(URL + path, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def players():
    with urllib.request.urlopen("http://127.0.0.1:8090/api/summary", timeout=15) as r:
        summary = json.load(r)
    now, online = datetime.now(timezone.utc), []
    for server in summary["servers"]:
        for s in server.get("online") or []:
            start = datetime.fromisoformat(s["start"].replace("Z", "+00:00"))
            if start.tzinfo is None:
                start = start.replace(tzinfo=timezone.utc)
            if now - start <= timedelta(hours=24):
                online.append(f"{s.get('name') or s.get('player')} on {server.get('game')}")
    print("players online: " + ", ".join(online) if online else "nobody online")
    return 1 if online else 0


def mem():
    base = "/sys/class/drm/card0/device/"
    total = sum(int(open(base + f).read()) for f in ("mem_info_gtt_used", "mem_info_vram_used"))
    return round(total / 1e9, 2)


def loaded():
    return [m["id"] for m in get("/models")["data"] if m["status"]["value"] != "unloaded"]


def unload():
    for m in loaded():
        post("/models/unload", {"model": m})
    for _ in range(60):
        if not loaded():
            return
        time.sleep(1)
    raise SystemExit("models did not unload: " + ", ".join(loaded()))


def chat(model, messages, max_tokens, thinking=False, **extra):
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, **extra}
    if not thinking:
        body["chat_template_kwargs"] = {"enable_thinking": False}
    t = time.time()
    d = post("/v1/chat/completions", body)
    msg = d["choices"][0]["message"]
    return {"seconds": round(time.time() - t, 1),
            "tok_s": round(d["timings"]["predicted_per_second"], 1),
            "tokens": d["usage"]["completion_tokens"],
            "finish": d["choices"][0]["finish_reason"],
            "content": msg.get("content") or "",
            "reasoning_chars": len(msg.get("reasoning_content") or "")}


CODE = [{"role": "user", "content": "Write a Python module that parses ISO 8601 durations "
         "such as P3DT4H5M into seconds, with docstrings, error handling and unittest tests."}]
PROSE = [{"role": "user", "content": "Write a 500-word short story about a night ferry "
          "crossing in fog, told by the ship's cook."}]
BAT = [{"role": "user", "content": "A bat and a ball cost $1.10 in total. The bat costs $1.00 "
        "more than the ball. How much does the ball cost?"}]


def server(model):
    unload()
    idle = mem()
    out = {"model": model}
    t = time.time()
    chat(model, [{"role": "user", "content": "Say hi."}], 8)
    out["cold_s"] = round(time.time() - t, 1)
    out["mem_loaded_gb"] = round(mem() - idle, 1)
    out["code"] = {k: v for k, v in chat(model, CODE, 600).items() if k != "content"}
    out["prose"] = {k: v for k, v in chat(model, PROSE, 600).items() if k != "content"}
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        pair = list(pool.map(lambda m: chat(model, m, 600), [CODE, PROSE]))
    out["two_at_once_tok_s"] = [p["tok_s"] for p in pair]
    task = json.load(open(TASK))
    msgs = [{"role": "system", "content": task["system"]},
            {"role": "user", "content": task["prompt"]}]
    rf = {"type": "json_schema", "json_schema": {"name": "reply", "schema": task["schema"],
                                                 "strict": True}}
    js = []
    for _ in range(4):
        r = chat(model, msgs, 400, response_format=rf)
        try:
            ok = isinstance(json.loads(r["content"]), dict) and r["finish"] == "stop"
        except ValueError:
            ok = False
        js.append({"valid": ok, "tokens": r["tokens"]})
    out["json_schema_400"] = js
    bat = chat(model, BAT, 8000, thinking=True)
    out["bat_ball"] = {"seconds": bat["seconds"], "reasoning_chars": bat["reasoning_chars"],
                       "right": "0.05" in bat["content"] or "5 cents" in bat["content"],
                       "answer": bat["content"][-200:]}
    out["mem_peak_gb"] = round(mem() - idle, 1)
    return out


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "players":
        sys.exit(players())
    if cmd == "mem":
        print(mem())
    elif cmd == "unload":
        unload()
    elif cmd == "server":
        print(json.dumps(server(sys.argv[2]), indent=1))
