import os
import random
import re
import unittest
from solution import evaluate


def same(a, b):
    return type(a) is type(b) and (a == b or (a != a and b != b))


def gen(rng, depth=0):
    """A random expression string, kept small enough to evaluate quickly."""
    if depth > 3 or rng.random() < 0.3:
        n = rng.choice(["0", "1", "2", "3", "7", "10", "0.5", "2.", ".25", "4"])
        return n
    kind = rng.random()
    if kind < 0.15:
        return rng.choice(["-", "+", "- "]) + gen(rng, depth + 1)
    if kind < 0.3:
        return "(" + gen(rng, depth + 1) + ")"
    if kind < 0.4:
        # keep powers tame: a small literal (maybe negated) as the exponent
        return gen(rng, depth + 2) + " ** " + rng.choice(["2", "3", "-1", "0", "(1)", "-2"])
    op = rng.choice(["+", "-", "*", "/", "//", "%"])
    sp = rng.choice(["", " "])
    return gen(rng, depth + 1) + sp + op + sp + gen(rng, depth + 1)


class T(unittest.TestCase):
    def check(self, text):
        try:
            want = eval(text)
        except ZeroDivisionError:
            with self.assertRaises(ZeroDivisionError, msg=text):
                evaluate(text)
            return
        got = evaluate(text)
        self.assertTrue(same(got, want), f"{text!r}: got {got!r}, want {want!r}")

    def test_examples(self):
        for text in ("1+2*3", "(1+2)*3", "-2**2", "2**-1", "2**3**2", "7//2", "-7//2",
                     "7%-3", "-7%3", "1/2", "2.*3", ".5+.5", "10-4-3", "2*-3", "--1",
                     "-(-(2))", " 3 ", "(((4)))", "2**-2**-1", "-2**-2", "8/4/2",
                     "0**0", "1+-+-1", "3*.5**2", "100//7%3", "2.5//1"):
            self.check(text)

    def test_random(self):
        rng = random.Random(42)
        for _ in range(1500):
            self.check(gen(rng))

    def test_errors(self):
        for bad in ("", "   ", "(", ")", "(1", "1)", "1 2", "1+", "*1", "1.2.3", "2x",
                    "1++", "()", "1(2)", "(1)(2)", "1 ** ", "3 // ", "1..2", ".", "1,2",
                    "**2", "1 */ 2", "abs(1)", "1e5", "0x10"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                evaluate(bad)

    def test_zero_division(self):
        for text in ("1/0", "1//0", "1%0", "1/(2-2)", "0.0/0"):
            with self.assertRaises(ZeroDivisionError, msg=text):
                evaluate(text)

    def test_no_eval(self):
        src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "solution.py")).read()
        code = re.sub(r"#.*", "", src)
        # the built-ins themselves, not methods such as re.compile
        self.assertIsNone(re.search(r"(?<![\w.])(eval|exec|compile)\s*\(", code))
        for banned in ("import ast", "from ast", "__import__"):
            self.assertNotIn(banned, code)


if __name__ == "__main__":
    unittest.main()
