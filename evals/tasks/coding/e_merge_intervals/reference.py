def merge(intervals):
    out = []
    for a, b in sorted([min(x), max(x)] for x in intervals):
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out
