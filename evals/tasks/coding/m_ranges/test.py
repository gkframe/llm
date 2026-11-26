import random
import unittest
from solution import compress_ranges, expand_ranges


class T(unittest.TestCase):
    def test_expand(self):
        self.assertEqual(expand_ranges("1-3,5,7-9"), [1, 2, 3, 5, 7, 8, 9])
        self.assertEqual(expand_ranges("-3--1"), [-3, -2, -1])
        self.assertEqual(expand_ranges("-2-2"), [-2, -1, 0, 1, 2])
        self.assertEqual(expand_ranges(" 1, 3-5 ,4"), [1, 3, 4, 5])
        self.assertEqual(expand_ranges("5,5,5"), [5])
        self.assertEqual(expand_ranges("4-4"), [4])
        self.assertEqual(expand_ranges(""), [])
        self.assertEqual(expand_ranges("   "), [])

    def test_expand_errors(self):
        for bad in ("3-1", "1,,2", "a", "1-", "-", "1-2-3", "1 2", "1,", "--1", "1.5", "- 1"):
            with self.assertRaises(ValueError, msg=bad):
                expand_ranges(bad)

    def test_compress(self):
        self.assertEqual(compress_ranges([1, 2, 3, 5, 6, 8]), "1-3,5,6,8")
        self.assertEqual(compress_ranges([]), "")
        self.assertEqual(compress_ranges([3, 1, 2, 2]), "1-3")
        self.assertEqual(compress_ranges([-3, -2, -1, 1]), "-3--1,1")
        self.assertEqual(compress_ranges(iter([0, 1])), "0,1")

    def test_round_trip(self):
        rng = random.Random(3)
        for _ in range(300):
            nums = [rng.randint(-15, 15) for _ in range(rng.randint(0, 20))]
            want = sorted(set(nums))
            self.assertEqual(expand_ranges(compress_ranges(nums)), want, nums)


if __name__ == "__main__":
    unittest.main()
