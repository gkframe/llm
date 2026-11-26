#!/usr/bin/env bash
# Quality run: for each model pause the playground, wait for idle slots, run, resume, rest 20 min.
set -u
cd /home/gavin/src/llm
R=evals/results/2026-11-26
CTL=127.0.0.1:8701/api/games
game() { curl -s 127.0.0.1:8701/api/state | python3 -c "import json,sys; print(json.load(sys.stdin).get('active') or '')"; }
control() { g=$(game); [ -n "$g" ] && curl -s -X POST $CTL/$g/control -H 'Content-Type: application/json' -d "{\"action\":\"$1\"}"; echo; }
idle() {
  for i in $(seq 1 120); do
    busy=0
    for m in $(curl -s 127.0.0.1:8741/models | python3 -c "import json,sys; print(' '.join(m['id'] for m in json.load(sys.stdin)['data'] if m['status']['value']!='unloaded'))"); do
      b=$(curl -s "127.0.0.1:8741/slots?model=$m" | python3 -c "import json,sys; print(sum(1 for s in json.load(sys.stdin) if s.get('is_processing')))"); busy=$((busy+b))
    done
    [ $busy = 0 ] && return 0; sleep 5
  done
}
first=1
for m in "$@"; do
  [ $first = 1 ] || { echo "$(date +%T) game resumed for 20 min"; sleep 1200; }
  first=0
  echo "$(date +%T) pausing for $m"; control pause; idle
  python3 evals/run.py --model $m --out $R
  python3 evals/run.py --model $m --out $R    # retry any failed rows once
  control resume; echo "$(date +%T) $m done"
done
echo "$(date +%T) all done"
