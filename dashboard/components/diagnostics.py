"""'Why did the optimiser do this' panel logic. Every field here is derived
directly from the schedule and known battery parameters - nothing is
invented. Fields that can't be honestly derived (e.g. a true per-period
profit split) are deliberately left out; see the module docstring in
components/diagnostics.py for what's shown instead.
"""


def derive_diagnostics(schedule: list, period: int, capacity: float, max_power: float,
                        eta_c: float, eta_d: float, tol: float = 0.01) -> dict:
    idx = period - 1
    row = schedule[idx]
    soc_before = schedule[idx - 1]["soc"] if idx > 0 else 0.0
    soc_after = row["soc"]

    if row["charge"] > tol:
        action = "CHARGE"
    elif row["discharge"] > tol:
        action = "DISCHARGE"
    else:
        action = "IDLE"

    binding = None
    if action == "CHARGE" and abs(row["charge"] - max_power) < tol:
        binding = "Max charge power"
    elif action == "DISCHARGE" and abs(row["discharge"] - max_power) < tol:
        binding = "Max discharge power"
    elif abs(soc_after - capacity) < tol:
        binding = "SoC ceiling (full)"
    elif abs(soc_after - 0) < tol:
        binding = "SoC floor (empty)"

    prev_charge_price = None
    if action == "DISCHARGE":
        for j in range(idx - 1, -1, -1):
            if schedule[j]["charge"] > tol:
                prev_charge_price = schedule[j]["price"]
                break

    spread = (row["price"] - prev_charge_price) if prev_charge_price is not None else None

    return {
        "period": period,
        "action": action,
        "price": row["price"],
        "soc_before": soc_before,
        "soc_after": soc_after,
        "binding_constraint": binding or "None (interior solution)",
        "previous_charge_price": prev_charge_price,
        "spread_vs_last_charge": spread,
        "round_trip_efficiency": round(eta_c * eta_d, 3),
    }
