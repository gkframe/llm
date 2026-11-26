import random
import unittest
from solution import invoice_total


def legacy(items, coupon=None, member=False):
    t = 0
    for i in items:
        if i["qty"] > 0:
            if i["category"] == "food":
                t = t + i["price"] * i["qty"]
            else:
                if member:
                    t = t + i["price"] * i["qty"] * 0.95
                else:
                    t = t + i["price"] * i["qty"]
    if coupon != None:  # noqa: E711
        if coupon == "SAVE5":
            if t >= 50:
                t = t - 5
        elif coupon == "HALFFOOD":
            f = 0
            for i in items:
                if i["qty"] > 0 and i["category"] == "food":
                    f = f + i["price"] * i["qty"]
            t = t - f / 2
        else:
            raise ValueError("unknown coupon")
    if t < 0:
        t = 0
    return round(t, 2)


def items_for(rng):
    return [{"sku": f"s{n}", "price": rng.choice([0.99, 2.5, 10, 19.99, 0, 33.33]),
             "qty": rng.randint(-2, 6), "category": rng.choice(["food", "tools", "toys"])}
            for n in range(rng.randint(0, 6))]


class T(unittest.TestCase):
    def close(self, a, b, msg=None):
        self.assertLessEqual(abs(a - b), 0.0101, msg)

    def test_unchanged_behaviour(self):
        rng = random.Random(9)
        for _ in range(2000):
            items = items_for(rng)
            coupon = rng.choice([None, "SAVE5", "HALFFOOD"])
            member = rng.random() < 0.5
            self.close(invoice_total(items, coupon, member), legacy(items, coupon, member),
                       (items, coupon, member))

    def test_unknown_coupon(self):
        with self.assertRaises(ValueError):
            invoice_total([], "NOPE")
        with self.assertRaises(ValueError):
            invoice_total([{"sku": "a", "price": 1, "qty": 1, "category": "food"}], "save5")

    def test_empty_string_coupon_is_unknown(self):
        with self.assertRaises(ValueError):
            invoice_total([], "")

    def test_bulk10(self):
        tools = {"sku": "t", "price": 10.0, "qty": 10, "category": "tools"}
        self.close(invoice_total([tools], "BULK10"), 90.0)
        self.close(invoice_total([tools], "BULK10", member=True), 85.5)
        nine = dict(tools, qty=9)
        self.close(invoice_total([nine], "BULK10"), 90.0)
        mixed = [dict(tools, qty=4), {"sku": "f", "price": 2.0, "qty": 6, "category": "food"},
                 {"sku": "x", "price": 100.0, "qty": -3, "category": "toys"}]
        self.close(invoice_total(mixed, "BULK10"), (40 + 12) * 0.9)
        self.close(invoice_total(mixed, "BULK10", member=True), (38 + 12) * 0.9)
        self.close(invoice_total([], "BULK10"), 0.0)


if __name__ == "__main__":
    unittest.main()
