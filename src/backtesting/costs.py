"""Phase 4: trade cost modeling — slippage, fees, and degradation.

Costs are applied POST-HOC to an already-decided schedule, not built into
the MILP's objective. This is a real simplification: a fully cost-aware
optimiser would choose fewer, more selective trades once costs are priced
in, so this likely UNDERSTATES the true impact of costs (some marginal
trades included here wouldn't have been made at all under a cost-aware
objective). Flagged as a known limitation, not fixed in this version.
"""

CAPITAL_BASE_GBP = 3_000_000
CELL_COST_FRACTION = 0.5   # only cell replacement cost degrades with cycling,
                             # not inverters/land/BOS - the rest of capex
RATED_CYCLES = 8000          # plausible modern LFP cycle life assumption
THROUGHPUT_PER_CYCLE_MWH = 20  # charge + discharge = one full cycle, for a 10 MWh battery

DEGRADATION_PER_MWH = (CAPITAL_BASE_GBP * CELL_COST_FRACTION) / (RATED_CYCLES * THROUGHPUT_PER_CYCLE_MWH)


def compute_trade_costs(schedule: list, slippage_pct: float = 0.0025,
                         fee_per_mwh: float = 1.0,
                         degradation_per_mwh: float = DEGRADATION_PER_MWH) -> dict:
    total_mwh_traded = sum(r["charge"] + r["discharge"] for r in schedule)
    traded_value = sum(r["price"] * (r["charge"] + r["discharge"]) for r in schedule)

    slippage_cost = traded_value * slippage_pct
    fee_cost = total_mwh_traded * fee_per_mwh
    degradation_cost = total_mwh_traded * degradation_per_mwh
    total_cost = slippage_cost + fee_cost + degradation_cost

    return {
        "total_mwh_traded": total_mwh_traded,
        "slippage_cost": slippage_cost,
        "fee_cost": fee_cost,
        "degradation_cost": degradation_cost,
        "total_cost": total_cost,
    }