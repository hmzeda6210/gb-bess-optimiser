import json

with open("backtest_results.json") as f:
    results = json.load(f)

for r in results:
    r["trade_cost"] = r["trade_cost"] * 0.5
    r["real_profit_after_costs"] = r["real_profit"] - r["trade_cost"]

with open("backtest_results.json", "w") as f:
    json.dump(results, f)

print(f"Updated {len(results)} days to halved cost assumptions.")
print(f"New total profit after costs: £{sum(r['real_profit_after_costs'] for r in results):,.2f}")