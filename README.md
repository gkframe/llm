# llm

A self-hosted open-weight LLM on **Minerva**: a chat page on the tailnet and an
OpenAI-compatible API for other Minerva services. It is llama.cpp's `llama-server` in one
Docker container, running on the Radeon 780M iGPU through Vulkan. There is no code of ours
in the request path. This repo holds the configuration, the model list and a download
script.

## How it works

```
 browser (tailnet) ──https :8740──> tailscale serve ──> 127.0.0.1:8741
 Minerva services ─────────── http://127.0.0.1:8741/v1 ─────────┘
                                                                 │
                         container "llm": llama-server in router mode
                           · models.ini lists the models; one is in memory at a time
                           · a model loads on its first request and unloads after
                             15 min without requests
                           · Llama Chat page, OpenAI and Anthropic APIs, /health
                           · /dev/dri (the iGPU) and data/models (read-only) mounted
```

- **Router mode.** The main `llama-server` process loads no model itself. On a request it
  starts a child process for the model named in the request, and forwards to it. With
  `--models-max 1`, asking for the other model unloads the first.
- **Sleeping.** After `--sleep-idle-seconds 900` without requests the model is unloaded
  and its memory (about 21 GB for Qwen, 14 GB for Gemma) goes back to the machine. The
  next request reloads it, which takes a few seconds while the file is still in the page
  cache and longer after a reboot. `/health`, `/props`, `/models` and `/metrics` don't
  count as requests, so the status page doesn't keep a model awake.
- **Alongside the games.** Every layer runs on the iGPU, and the container is capped at 4
  CPUs and 4 threads. Generating text still competes with the game servers for memory
  bandwidth, so expect some effect on them while it runs. It hasn't been measured with
  players online yet.
- **After the 04:30 reboot** the container starts with no model loaded.

## Models

| Name (the API's `model`) | File | Size | Speed on Minerva |
| --- | --- | --- | --- |
| `qwen3.6-35b-a3b` | Qwen3.6 35B-A3B, unsloth UD-Q4_K_M | 20.6 GiB | 465 tok/s reading, 23.7 tok/s writing (llama-bench); through the server 22.7 tok/s, or 17 tok/s each with two requests at once; 12.8 s for a cold request from the page cache; ~23 GB of iGPU memory loaded (2026-11-21) |
| `gemma-4-26b-a4b` | Gemma 4 26B-A4B-it, Google's QAT Q4_0 | 13.4 GiB | 27.1 tok/s writing through the server; 6 s for a cold request (2026-11-21) |

Both are mixture-of-experts models: large in total, but only 3–4B parameters work on each
token, which is what makes them quick on this machine. Memory speed (dual-channel DDR5,
about 70 GB/s in practice) is the limit; a dense model of similar quality (e.g. a 27B)
manages about 4 tok/s.

Each request can use **32k tokens of context**, and two requests are served at once (64k
in total, split between two slots). A full 32k prompt takes over a minute to read.

Both models **think before answering** by default. The thinking comes back in
`reasoning_content`, separately from `content`. If `max_tokens` is too small the answer can
be empty because the limit ran out while thinking. For quick jobs, turn thinking off per
request with `"chat_template_kwargs": {"enable_thinking": false}`.

### Adding or changing a model

1. Find the GGUF on Hugging Face. Pick the repo's current commit and the file's size and
   sha256 from `https://huggingface.co/api/models/<repo>/tree/main` (the `lfs.oid`).
2. Add a `live` line to `models.list`, with a URL of the form
   `https://huggingface.co/<repo>/resolve/<commit>/<file>`.
3. Add a `[name]` section to `models.ini` with `model = /models/<file>` and the model
   card's recommended sampling settings.
4. `bin/test`, commit, push, `deploy llm`. The deploy downloads the file before restarting
   (`pre_apply = bin/fetch-models`), which can take half an hour. If the download or the
   checksum fails, nothing changes.

A model removed from `models.list` leaves its file in `/srv/llm/data/models`. Deleting it
is a step for the user: `sudo -u deploy rm /srv/llm/data/models/<file>
/srv/llm/data/models/.verified/<file>`. Memory limits: the iGPU can address about 33 GB,
and the game servers need their share, so stay under about 25 GB per model file.

## Everyday use

**Chat:** `https://minerva.beluga-brill.ts.net:8740/` on the tailnet. Pick a model at the
top. Conversations are kept in your browser, not on the server, so they don't follow you
between devices. Anyone on the tailnet can use it; there is no login.

**API, from a Minerva service:** base URL `http://127.0.0.1:8741/v1`, OpenAI's chat
completions format, no key. `model` is required and picks the model. Standard-library
example:

```python
import json, urllib.request
req = urllib.request.Request(
    "http://127.0.0.1:8741/v1/chat/completions",
    data=json.dumps({
        "model": "qwen3.6-35b-a3b",
        "messages": [{"role": "user", "content": "Summarise: ..."}],
        "chat_template_kwargs": {"enable_thinking": False},
    }).encode(),
    headers={"Content-Type": "application/json"},
)
reply = json.load(urllib.request.urlopen(req, timeout=300))["choices"][0]["message"]["content"]
```

- **Timeouts:** allow at least a minute. The first request after a sleep loads the model,
  and a third request waits until one of the two slots is free.
- **Switching models** unloads the other one, so a service should stick to one model and
  leave the other for chat when it can.
- **Containers:** a service running in Docker reaches the host through
  `extra_hosts: ["host.docker.internal:host-gateway"]`, but the port is bound to
  127.0.0.1 only, so that also needs a change here. Not set up yet.
- The Anthropic Messages API is at `/v1/messages` as well.

## Operations

| Task | Command |
| --- | --- |
| Deploy a change | Push to `main`, then `deploy llm` |
| Status, logs | `docker ps --filter name=llm`, `docker logs llm` (as gavin) |
| Which model is loaded | `curl -s 127.0.0.1:8741/models` (each model's `status`) |
| Unload now | `curl -s -X POST 127.0.0.1:8741/models/unload -d '{"model":"qwen3.6-35b-a3b"}'` |
| Download missing models by hand | `deploy llm` (deploy runs `bin/fetch-models`) |
| Tests | `bin/test` |
| Dev instance | `bin/dev up`: the same image on `127.0.0.1:8841` with a 0.8B model in `data-dev/` (`models-dev.ini`). `bin/dev down` stops it |
| Benchmark a model | `docker run --rm --device /dev/dri --group-add 993 -v /srv/llm/data/models:/models:ro --entrypoint /app/llama-bench ghcr.io/ggml-org/llama.cpp:full-vulkan -m /models/<file> -ngl 99 -fa 1 -p 512 -n 128` (only while the live model is unloaded) |
| Update llama.cpp | Change the image tag in `docker-compose.yml`, try it with `bin/dev up`, then deploy |

Monitoring: Gatus has `apps / llm` (`/health`), `portals / llm-8740` and `deploys / llm`.
Beszel shows the container's CPU and memory.

## Layout

```
docker-compose.yml   the container; bin/dev reuses it via LLM_* variables
models.ini           live presets: global settings, then one [section] per model
models-dev.ini       the dev instance's presets
models.list          files to download: set, file, bytes, sha256, pinned URL
bin/fetch-models     downloads and verifies models.list (deploy's pre_apply)
bin/dev, bin/test    dev instance on 8841; the tests (no network or Docker)
tests/               unittest: presets match models.list; fetch-models against file:// URLs
data/models/         (not in git) live model files, owned by deploy; .verified/ holds checksums
data-dev/models/     (not in git) the dev model
```

## Rules for agents

The `minerva` repo's README rules apply. In addition:

- **Deploy after a push without asking**, like the other services. A deploy restarts the
  container, which cuts off a chat or a service request in progress. If one is likely to
  be running (check `curl -s 127.0.0.1:8741/slots?model=<name>` for busy slots), wait.
- **Don't load a second large model beside the live one.** Use `bin/dev` (0.8B model) to
  test changes. Benchmark a large model only while the live one is unloaded, and never
  while players are on a game server without asking.
- **Model files are data:** never commit them. They live in `/srv/llm/data/models`
  (owned by deploy) and arrive only through `models.list` and `deploy llm`.
- **Prompts can be private.** Don't turn on prompt logging (`--log-prompts-dir`,
  verbose logs) or read other services' requests out of logs.
- Ask before adding an API key, opening the port beyond localhost, or making a model load
  at startup.
