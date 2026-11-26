import random
import unittest
from solution import TTLCache


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


class Reference:
    """Straightforward model of the spec, used for random comparisons."""

    def __init__(self, capacity, ttl, clock):
        self.cap, self.ttl, self.clock = capacity, ttl, clock
        self.items = {}      # key -> (value, expires, last_used)
        self.tick = 0

    def _live(self):
        now = self.clock()
        self.items = {k: v for k, v in self.items.items() if now < v[1]}

    def set(self, k, v):
        self._live()
        self.tick += 1
        if k not in self.items and len(self.items) >= self.cap:
            old = min(self.items, key=lambda x: self.items[x][2])
            del self.items[old]
        self.items[k] = (v, self.clock() + self.ttl, self.tick)

    def get(self, k, default=None):
        self._live()
        if k not in self.items:
            return default
        self.tick += 1
        v, exp, _ = self.items[k]
        self.items[k] = (v, exp, self.tick)
        return v

    def delete(self, k):
        self._live()
        return self.items.pop(k, None) is not None

    def __len__(self):
        self._live()
        return len(self.items)

    def __contains__(self, k):
        self._live()
        return k in self.items


class T(unittest.TestCase):
    def setUp(self):
        self.clock = Clock()

    def test_bad_args(self):
        for cap, ttl in ((0, 1), (-1, 1), (1, 0), (1, -5)):
            with self.assertRaises(ValueError):
                TTLCache(cap, ttl, clock=self.clock)

    def test_expiry_boundary(self):
        c = TTLCache(3, 10, clock=self.clock)
        c.set("a", 1)
        self.clock.t += 9.999
        self.assertEqual(c.get("a"), 1)
        self.clock.t += 0.001
        self.assertIsNone(c.get("a"))
        self.assertEqual(c.get("a", "x"), "x")
        self.assertNotIn("a", c)
        self.assertEqual(len(c), 0)

    def test_get_does_not_extend(self):
        c = TTLCache(3, 10, clock=self.clock)
        c.set("a", 1)
        self.clock.t += 6
        c.get("a")
        self.clock.t += 5
        self.assertNotIn("a", c)

    def test_set_restarts_expiry(self):
        c = TTLCache(3, 10, clock=self.clock)
        c.set("a", 1)
        self.clock.t += 6
        c.set("a", 2)
        self.clock.t += 6
        self.assertEqual(c.get("a"), 2)

    def test_lru_eviction(self):
        c = TTLCache(2, 100, clock=self.clock)
        c.set("a", 1)
        c.set("b", 2)
        c.get("a")
        c.set("c", 3)
        self.assertIn("a", c)
        self.assertNotIn("b", c)
        self.assertIn("c", c)

    def test_contains_and_len_do_not_touch_recency(self):
        c = TTLCache(2, 100, clock=self.clock)
        c.set("a", 1)
        c.set("b", 2)
        self.assertIn("a", c)
        self.assertEqual(len(c), 2)
        c.set("c", 3)
        self.assertNotIn("a", c)

    def test_expired_entries_free_space_first(self):
        c = TTLCache(2, 10, clock=self.clock)
        c.set("old", 1)
        self.clock.t += 5
        c.set("b", 2)
        self.clock.t += 6        # "old" expired, "b" still live
        c.set("c", 3)
        self.assertIn("b", c)
        self.assertIn("c", c)

    def test_update_existing_at_capacity(self):
        c = TTLCache(2, 100, clock=self.clock)
        c.set("a", 1)
        c.set("b", 2)
        c.set("a", 10)
        self.assertEqual(len(c), 2)
        self.assertEqual(c.get("b"), 2)
        c.set("c", 3)
        self.assertNotIn("a", c)

    def test_delete(self):
        c = TTLCache(2, 10, clock=self.clock)
        c.set("a", 1)
        self.assertTrue(c.delete("a"))
        self.assertFalse(c.delete("a"))
        c.set("b", 2)
        self.clock.t += 10
        self.assertFalse(c.delete("b"))

    def test_none_values(self):
        c = TTLCache(2, 10, clock=self.clock)
        c.set("n", None)
        self.assertIn("n", c)
        self.assertIsNone(c.get("n", "default"))

    def test_random_against_reference(self):
        rng = random.Random(5)
        for _ in range(60):
            clock = Clock()
            cap, ttl = rng.randint(1, 4), rng.choice([1, 2.5, 5])
            c, r = TTLCache(cap, ttl, clock=clock), Reference(cap, ttl, clock)
            for step in range(150):
                op = rng.random()
                k = rng.choice("abcdef")
                if op < 0.35:
                    c.set(k, step)
                    r.set(k, step)
                elif op < 0.65:
                    self.assertEqual(c.get(k, "-"), r.get(k, "-"))
                elif op < 0.72:
                    self.assertEqual(c.delete(k), r.delete(k))
                elif op < 0.8:
                    self.assertEqual(len(c), len(r))
                elif op < 0.87:
                    self.assertEqual(k in c, k in r)
                else:
                    clock.t += rng.choice([0.5, 1, 2])


if __name__ == "__main__":
    unittest.main()
