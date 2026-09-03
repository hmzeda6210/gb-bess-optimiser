import json

with open("backtest_results.json") as f:
    results = json.load(f)

total_real = sum(r["real_profit"] for r in results)
total_after_costs = sum(r["real_profit_after_costs"] for r in results)
total_costs = sum(r["trade_cost"] for r in results)

print(f"Total profit before costs: £{total_real:,.2f}")
print(f"Total costs: £{total_costs:,.2f}")
print(f"Total profit after costs: £{total_after_costs:,.2f}")
print(f"Costs as % of gross profit: {total_costs/total_real:.1%}")

# recompute headline metrics on the after-costs series
CAPACITY_MW = 5.0
profit_per_mw_year_after_costs = (total_after_costs / CAPACITY_MW / len(results)) * 365
print(f"\n£/MW/year BEFORE costs: £{(total_real/CAPACITY_MW/len(results))*365:,.0f}")
print(f"£/MW/year AFTER costs:  £{profit_per_mw_year_after_costs:,.0f}")

negative_after_costs = sum(1 for r in results if r["real_profit_after_costs"] < 0)
print(f"\nDays profitable before costs: {sum(1 for r in results if r['real_profit'] > 0)}/{len(results)}")
print(f"Days profitable after costs:  {sum(1 for r in results if r['real_profit_after_costs'] > 0)}/{len(results)}")