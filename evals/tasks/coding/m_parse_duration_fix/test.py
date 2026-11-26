import unittest
from solution import parse_duration


class T(unittest.TestCase):
    def test_valid(self):
        cases = {"1h30m": 5400, "45s": 45, "2h5s": 7205, "90m": 5400, "1h2m3s": 3723,
                 "0s": 0, "100h": 360000, "007m": 420}
        for s, want in cases.items():
            self.assertEqual(parse_duration(s), want, s)

    def test_invalid(self):
        for bad in ("", "15", "1h1h", "30m1h", "h", "1d", "1h 30m", "1h30", "m5", "1s2m",
                    "1h2m3s4s", " 1h", "1H", "1.5h", "-1h", "1h\n"):
            with self.assertRaises(ValueError, msg=repr(bad)):
                parse_duration(bad)


if __name__ == "__main__":
    unittest.main()
