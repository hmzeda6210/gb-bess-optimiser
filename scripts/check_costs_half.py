import json

with open("backtest_results.json") as f:
    results = json.load(f)

total_real = sum(r["real_profit"] for r in results)
total_original_cost = sum(r["trade_cost"] for r in results)

# Costs scale linearly with slippage_pct, fee_per_mwh, degradation_per_mwh -
# halving all three assumptions halves the total cost exactly, since the
# schedule itself doesn't depend on these cost parameters (not yet built
# into the MILP objective)
total_cost_halved = total_original_cost * 0.5
total_after_halved_costs = total_real - total_cost_halved

print(f"Total profit before costs: £{total_real:,.2f}")
print(f"Total costs (original): £{total_original_cost:,.2f}")
print(f"Total costs (halved): £{total_cost_halved:,.2f}")
print(f"Total profit after HALVED costs: £{total_after_halved_costs:,.2f}")

CAPACITY_MW = 5.0
profit_per_mw_year_halved = (total_after_halved_costs / CAPACITY_MW / len(results)) * 365
print(f"\n£/MW/year AFTER halved costs: £{profit_per_mw_year_halved:,.0f}")

# recompute per-day profitability with halved costs
after_halved_per_day = [r["real_profit"] - (r["trade_cost"] * 0.5) for r in results]
profitable_days = sum(1 for p in after_halved_per_day if p > 0)
print(f"Days profitable after halved costs: {profitable_days}/{len(results)}")