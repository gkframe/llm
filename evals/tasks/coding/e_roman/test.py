import unittest
from solution import int_to_roman


class T(unittest.TestCase):
    def test_examples(self):
        cases = {1: "I", 3: "III", 4: "IV", 9: "IX", 14: "XIV", 40: "XL", 58: "LVIII",
                 90: "XC", 400: "CD", 444: "CDXLIV", 1994: "MCMXCIV", 2024: "MMXXIV",
                 3999: "MMMCMXCIX"}
        for n, want in cases.items():
            self.assertEqual(int_to_roman(n), want, n)

    def test_round_trip_all(self):
        vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
        seen = set()
        for n in range(1, 4000):
            s = int_to_roman(n)
            total = 0
            for a, b in zip(s, s[1:] + " "):
                v = vals[a]
                total += -v if b != " " and vals[b] > v else v
            self.assertEqual(total, n, s)
            seen.add(s)
        self.assertEqual(len(seen), 3999)

    def test_errors(self):
        for bad in (0, -1, 4000, 10000):
            with self.assertRaises(ValueError):
                int_to_roman(bad)


if __name__ == "__main__":
    unittest.main()
