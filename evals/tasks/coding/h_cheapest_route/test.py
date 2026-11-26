import random
import time
import unittest
from solution import cheapest_route


def brute(flights, src, dst, max_stops):
    if src == dst:
        return (0, [src])
    out = {}
    for a, b, p in flights:
        out.setdefault(a, []).append((b, p))
    best = None

    def walk(node, path, cost):
        nonlocal best
        if node == dst:
            key = (cost, len(path), path)
            if best is None or key < best:
                best = key
            return
        if len(path) - 1 > max_stops:
            return
        for b, p in out.get(node, []):
            if b not in path:
                walk(b, path + [b], cost + p)

    walk(src, [src], 0)
    return None if best is None else (best[0], best[2])


class T(unittest.TestCase):
    def test_example(self):
        flights = [("A", "B", 100), ("B", "C", 100), ("A", "C", 500), ("C", "D", 100),
                   ("B", "D", 600)]
        self.assertEqual(cheapest_route(flights, "A", "D", 2), (300, ["A", "B", "C", "D"]))
        self.assertEqual(cheapest_route(flights, "A", "D", 1), (600, ["A", "C", "D"]))
        self.assertEqual(cheapest_route(flights, "A", "D", 0), None)
        self.assertEqual(cheapest_route(flights, "A", "A", 0), (0, ["A"]))
        self.assertEqual(cheapest_route(flights, "D", "A", 5), None)

    def test_ties(self):
        flights = [("S", "X", 5), ("X", "T", 5), ("S", "T", 10), ("S", "B", 5), ("B", "T", 5)]
        self.assertEqual(cheapest_route(flights, "S", "T", 3), (10, ["S", "T"]))
        flights = [("S", "X", 5), ("X", "T", 5), ("S", "B", 5), ("B", "T", 5)]
        self.assertEqual(cheapest_route(flights, "S", "T", 3), (10, ["S", "B", "T"]))
        flights = [("S", "A", 0), ("A", "T", 0), ("S", "T", 0)]
        self.assertEqual(cheapest_route(flights, "S", "T", 3), (0, ["S", "T"]))

    def test_parallel_flights_and_cycles(self):
        flights = [("A", "B", 9), ("A", "B", 2), ("B", "A", 0), ("B", "C", 1)]
        self.assertEqual(cheapest_route(flights, "A", "C", 1), (3, ["A", "B", "C"]))

    def test_random_small(self):
        rng = random.Random(1)
        names = list("ABCDEFG")
        for _ in range(400):
            flights = [(rng.choice(names), rng.choice(names), rng.randint(0, 6))
                       for _ in range(rng.randint(0, 18))]
            flights = [f for f in flights if f[0] != f[1]]
            src, dst = rng.choice(names), rng.choice(names)
            k = rng.randint(0, 5)
            self.assertEqual(cheapest_route(flights, src, dst, k), brute(flights, src, dst, k),
                             (flights, src, dst, k))

    def test_speed(self):
        rng = random.Random(2)
        names = [f"P{i:03d}" for i in range(300)]
        flights = [(rng.choice(names), rng.choice(names), rng.randint(1, 1000))
                   for _ in range(3000)]
        start = time.time()
        for _ in range(3):
            cheapest_route(flights, names[0], names[1], 6)
        self.assertLess(time.time() - start, 10)


if __name__ == "__main__":
    unittest.main()
