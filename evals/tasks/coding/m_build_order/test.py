import heapq
import random
import unittest
from solution import build_order


def reference(deps):
    nodes = set(deps)
    for ds in deps.values():
        nodes.update(ds)
    need = {n: set() for n in nodes}
    users = {n: set() for n in nodes}
    for t, ds in deps.items():
        for d in ds:
            need[t].add(d)
            users[d].add(t)
    ready = [n for n in nodes if not need[n]]
    heapq.heapify(ready)
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


class T(unittest.TestCase):
    def test_example(self):
        deps = {"app": ["lib", "utils"], "lib": ["utils"], "tests": ["app"]}
        self.assertEqual(build_order(deps), ["utils", "lib", "app", "tests"])

    def test_alphabetical_choice(self):
        self.assertEqual(build_order({"c": [], "b": [], "a": ["c"]}), ["b", "c", "a"])
        self.assertEqual(build_order({}), [])
        self.assertEqual(build_order({"x": ["y", "y"]}), ["y", "x"])

    def test_cycles(self):
        for deps in ({"a": ["a"]}, {"a": ["b"], "b": ["a"]},
                     {"a": ["b"], "b": ["c"], "c": ["a"], "d": []}):
            with self.assertRaises(ValueError):
                build_order(deps)

    def test_random(self):
        rng = random.Random(11)
        names = [chr(ord("a") + i) for i in range(10)]
        for _ in range(300):
            deps = {}
            for n in rng.sample(names, rng.randint(0, 10)):
                deps[n] = [rng.choice(names) for _ in range(rng.randint(0, 3))]
            try:
                want = reference(deps)
            except ValueError:
                with self.assertRaises(ValueError, msg=deps):
                    build_order(deps)
                continue
            self.assertEqual(build_order(deps), want, deps)


if __name__ == "__main__":
    unittest.main()
