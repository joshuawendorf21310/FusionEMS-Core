def calculate_claim_amount(base_rate: float, modifiers: list):
    return base_rate + sum(modifiers)