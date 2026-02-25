def project_revenue(volume: int, avg_revenue: float, growth: float):
    projected_volume = volume * (1 + growth)
    return projected_volume * avg_revenue