def calculate_claim_amount(base_rate: float, modifiers: list):
    total = base_rate
    for m in modifiers:
        total += m
    return total