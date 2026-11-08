def calculate_compound_interest(principal: float, rate: float, time_years: int) -> float:
    """Calculates compound interest for a given principal, rate and time."""
    if principal < 0 or rate < 0 or time_years < 0:
        raise ValueError("Inputs must be non-negative")
    amount = principal * ((1 + rate / 100) ** time_years)
    return round(amount, 2)
