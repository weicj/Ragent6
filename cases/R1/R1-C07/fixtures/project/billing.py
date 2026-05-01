def discount_cents(cents, pct):
    return int(cents * pct / 100)


def final_total(cents, pct):
    return cents - discount_cents(cents, pct)
