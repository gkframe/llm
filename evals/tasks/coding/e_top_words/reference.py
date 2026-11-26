import re
from collections import Counter


def top_words(text, k):
    words = [w.strip("'").lower() for w in re.findall(r"[A-Za-z']+", text)]
    counts = Counter(w for w in words if w)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:max(k, 0)]
