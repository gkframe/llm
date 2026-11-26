import heapq


def build_order(deps):
    nodes = set(deps)
    for ds in deps.values():
        nodes.update(ds)
    need = {n: set() for n in nodes}
    users = {n: set() for n in nodes}
    for t, ds in deps.items():
        for d in ds:
            need[t].add(d)
            users[d].add(t)
    ready = sorted(n for n in nodes if not need[n])
    out = []
    while ready:
        n = heapq.heappop(ready)
        out.append(n)
        for u in users[n]:
            need[u].discard(n)
            if not need[u]:
                heapq.heappush(ready, u)
    if len(out) != len(nodes):
        raise ValueError("cycle")
    return out
