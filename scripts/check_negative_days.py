from src.backtesting.walk_forward import WalkForwardBacktester

bt = WalkForwardBacktester("2025-06-01", "2026-07-23", 10.0, 5.0, 0.922, 0.922, retrain_every=30)
results = bt.run()

negative_days = [r for r in results if r["real_profit"] < 0]
print(f"Negative-profit days: {len(negative_days)} out of {len(results)}")
print(f"Total loss on negative days: £{sum(r['real_profit'] for r in negative_days):.2f}")