import unittest
from solution import top_words


class T(unittest.TestCase):
    def test_basic(self):
        self.assertEqual(top_words("the cat and the hat and the bat", 2),
                         [("the", 3), ("and", 2)])

    def test_case_and_ties(self):
        self.assertEqual(top_words("Beta alpha BETA Alpha gamma", 3),
                         [("alpha", 2), ("beta", 2), ("gamma", 1)])

    def test_apostrophes(self):
        self.assertEqual(top_words("'Hello' don't DON'T ''' hello, world!", 5),
                         [("don't", 2), ("hello", 2), ("world", 1)])

    def test_punctuation_and_digits(self):
        self.assertEqual(top_words("a1b-c a.b", 10), [("a", 2), ("b", 2), ("c", 1)])

    def test_fewer_than_k(self):
        self.assertEqual(top_words("one", 5), [("one", 1)])
        self.assertEqual(top_words("", 3), [])
        self.assertEqual(top_words("x y", 0), [])


if __name__ == "__main__":
    unittest.main()
