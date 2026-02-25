def calculate_roi(revenue: float, cost: float):
    if cost == 0:
        return 0
    return (revenue - cost) / cost