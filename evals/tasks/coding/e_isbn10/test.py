import unittest
from solution import is_isbn10


class T(unittest.TestCase):
    def test_valid(self):
        for s in ("0306406152", "0-306-40615-2", "080442957X", "0-8044-2957-X",
                  "--0306406152--", "3-598-21508-8"):
            self.assertTrue(is_isbn10(s), s)

    def test_invalid(self):
        for s in ("0306406153", "080442957x", "0 306 40615 2", "030640615", "03064061522",
                  "X306406152", "0306X06152", "", "----", "3-598-21508-9", "0306406152\n"):
            self.assertFalse(is_isbn10(s), repr(s))


if __name__ == "__main__":
    unittest.main()
