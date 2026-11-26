import copy
import random
import unittest
from solution import merge


def reference(intervals):
    xs = sorted([min(a, b), max(a, b)] for a, b in intervals)
    out = []
    for a, b in xs:
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


class T(unittest.TestCase):
    def test_examples(self):
        self.assertEqual(merge([[1, 3], [2, 6], [8, 10], [15, 18]]), [[1, 6], [8, 10], [15, 18]])
        self.assertEqual(merge([[1, 2], [2, 3]]), [[1, 3]])
        self.assertEqual(merge([[5, 3], [1, 2]]), [[1, 2], [3, 5]])
        self.assertEqual(merge([]), [])
        self.assertEqual(merge([[1, 10], [2, 3]]), [[1, 10]])

    def test_input_untouched(self):
        data = [[4, 1], [0, 0], [2, 9]]
        before = copy.deepcopy(data)
        merge(data)
        self.assertEqual(data, before)

    def test_random(self):
        rng = random.Random(7)
        for _ in range(300):
            data = [[rng.randint(-20, 20), rng.randint(-20, 20)] for _ in range(rng.randint(0, 12))]
            self.assertEqual([list(x) for x in merge(copy.deepcopy(data))], reference(data))


if __name__ == "__main__":
    unittest.main()
