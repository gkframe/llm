import re

_ITEM = re.compile(r"(-?[0-9]+)(?:-(-?[0-9]+))?")


def expand_ranges(s):
    if not s.strip():
        return []
    out = set()
    for item in s.split(","):
        m = _ITEM.fullmatch(item.strip())
        if not m:
            raise ValueError(item)
        a = int(m.group(1))
        b = int(m.group(2)) if m.group(2) is not None else a
        if a > b:
            raise ValueError(item)
        out.update(range(a, b + 1))
    return sorted(out)


def compress_ranges(nums):
    xs = sorted(set(nums))
    parts, i = [], 0
    while i < len(xs):
        j = i
        while j + 1 < len(xs) and xs[j + 1] == xs[j] + 1:
            j += 1
        if j - i >= 2:
            parts.append(f"{xs[i]}-{xs[j]}")
        else:
            parts.extend(str(x) for x in xs[i:j + 1])
        i = j + 1
    return ",".join(parts)
