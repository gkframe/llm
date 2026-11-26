import unittest
from solution import parse_csv_line


class T(unittest.TestCase):
    def test_plain(self):
        self.assertEqual(parse_csv_line("a,b,c"), ["a", "b", "c"])
        self.assertEqual(parse_csv_line(""), [""])
        self.assertEqual(parse_csv_line(","), ["", ""])
        self.assertEqual(parse_csv_line("a,"), ["a", ""])
        self.assertEqual(parse_csv_line(" a , b "), [" a ", " b "])

    def test_quoted(self):
        self.assertEqual(parse_csv_line('"a,b",c'), ["a,b", "c"])
        self.assertEqual(parse_csv_line('"say ""hi""",x'), ['say "hi"', "x"])
        self.assertEqual(parse_csv_line('""'), [""])
        self.assertEqual(parse_csv_line('"",""'), ["", ""])
        self.assertEqual(parse_csv_line('""""'), ['"'])
        self.assertEqual(parse_csv_line('x,"y"'), ["x", "y"])
        self.assertEqual(parse_csv_line('"a,",'), ["a,", ""])

    def test_quotes_in_unquoted(self):
        self.assertEqual(parse_csv_line('a"b,c'), ['a"b', "c"])
        self.assertEqual(parse_csv_line(' "a",b'), [' "a"', "b"])
        self.assertEqual(parse_csv_line('ab""'), ['ab""'])

    def test_errors(self):
        for bad in ('"abc', '"a"b,c', 'x,"unterminated', '"a" ,b', '"a""'):
            with self.assertRaises(ValueError, msg=bad):
                parse_csv_line(bad)


if __name__ == "__main__":
    unittest.main()
