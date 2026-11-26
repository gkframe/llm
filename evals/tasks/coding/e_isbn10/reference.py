import re


def is_isbn10(s):
    s = s.replace("-", "")
    if not re.fullmatch(r"[0-9]{9}[0-9X]", s):
        return False
    vals = [10 if c == "X" else int(c) for c in s]
    return sum(v * w for v, w in zip(vals, range(10, 0, -1))) % 11 == 0
