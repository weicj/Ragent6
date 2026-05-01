from billing import discount_cents, final_total

assert discount_cents(101, 10) == 10
assert discount_cents(105, 10) == 10
assert discount_cents(106, 10) == 11
assert final_total(106, 10) == 95
print("PASS")
