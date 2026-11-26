import re

_TOKEN = re.compile(r"\s*(?:(\d+\.\d*|\.\d+|\d+)|(\*\*|//|[-+*/%()]))")


def _tokens(expr):
    pos, out = 0, []
    expr = expr.rstrip()
    while pos < len(expr):
        m = _TOKEN.match(expr, pos)
        if not m:
            raise ValueError(f"bad input at {pos}")
        pos = m.end()
        if m.group(1) is not None:
            out.append(("num", m.group(1)))
        else:
            out.append(("op", m.group(2)))
    for (k1, _), (k2, _) in zip(out, out[1:]):
        if k1 == k2 == "num":
            raise ValueError("two numbers in a row")
    return out


def evaluate(expr):
    toks = _tokens(expr)
    i = 0

    def peek():
        return toks[i] if i < len(toks) else (None, None)

    def take():
        nonlocal i
        if i >= len(toks):
            raise ValueError("unexpected end")
        i += 1
        return toks[i - 1]

    def sum_():
        v = term()
        while peek() in (("op", "+"), ("op", "-")):
            op = take()[1]
            r = term()
            v = v + r if op == "+" else v - r
        return v

    def term():
        v = unary()
        while peek()[0] == "op" and peek()[1] in ("*", "/", "//", "%"):
            op = take()[1]
            r = unary()
            v = {"*": lambda a, b: a * b, "/": lambda a, b: a / b,
                 "//": lambda a, b: a // b, "%": lambda a, b: a % b}[op](v, r)
        return v

    def unary():
        if peek() in (("op", "-"), ("op", "+")):
            op = take()[1]
            v = unary()
            return -v if op == "-" else +v
        return power()

    def power():
        v = atom()
        if peek() == ("op", "**"):
            take()
            return v ** unary()
        return v

    def atom():
        kind, val = take()
        if kind == "num":
            return float(val) if "." in val else int(val)
        if val == "(":
            v = sum_()
            if take() != ("op", ")"):
                raise ValueError("expected )")
            return v
        raise ValueError(f"unexpected {val}")

    v = sum_()
    if i != len(toks):
        raise ValueError("trailing input")
    return v
