def cheapest_route(flights, src, dst, max_stops):
    if src == dst:
        return (0, [src])
    out = {}
    for a, b, p in flights:
        if a != b:
            out.setdefault(a, {})
            if b not in out[a] or p < out[a][b]:
                out[a][b] = p
    # best[node] = (cost, path) using exactly `step` flights; keep the best per node.
    frontier = {src: (0, [src])}
    best = None
    for step in range(1, max_stops + 2):
        nxt = {}
        for node, (cost, path) in frontier.items():
            for b, p in out.get(node, {}).items():
                if b in path:
                    continue
                cand = (cost + p, path + [b])
                if b not in nxt or cand < nxt[b]:
                    nxt[b] = cand
        if dst in nxt:
            cand = (nxt[dst][0], step, nxt[dst][1])
            if best is None or cand < best:
                best = cand
            del nxt[dst]
        frontier = nxt
    return None if best is None else (best[0], best[2])
