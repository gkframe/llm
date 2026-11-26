MEMBER_RATE = 0.95


def _line(item, member):
    amount = item["price"] * item["qty"]
    if member and item["category"] != "food":
        amount = amount * MEMBER_RATE
    return amount


def invoice_total(items, coupon=None, member=False):
    live = [i for i in items if i["qty"] > 0]
    total = 0
    for item in live:
        total = total + _line(item, member)
    if coupon is not None:
        if coupon == "SAVE5":
            if total >= 50:
                total = total - 5
        elif coupon == "HALFFOOD":
            food = 0
            for item in live:
                if item["category"] == "food":
                    food = food + item["price"] * item["qty"]
            total = total - food / 2
        elif coupon == "BULK10":
            if sum(i["qty"] for i in live) >= 10:
                total = total * 0.9
        else:
            raise ValueError("unknown coupon")
    return round(max(total, 0), 2)
