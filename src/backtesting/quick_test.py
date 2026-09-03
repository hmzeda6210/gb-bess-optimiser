from src.optimisation.dispatch import load_day_ahead_prices

actual = load_day_ahead_prices("2026-07-22")

schedule = [
    (28, 102.14, "charge", 5.0),
    (29, 102.14, "charge", 0.846),
    (30, 101.66, "charge", 5.0),
    (42, 138.68, "discharge", 4.22),
    (43, 138.68, "discharge", 5.0),
]

print(f"{'Period':>6} {'Action':>10} {'MWh':>6} {'Forecast':>10} {'Actual':>10} {'Diff':>8}")
for period, forecast_price, action, mwh in schedule:
    actual_price = actual[period]
    diff = actual_price - forecast_price
    print(f"{period:>6} {action:>10} {mwh:>6.2f} £{forecast_price:>8.2f} £{actual_price:>8.2f} £{diff:>+6.2f}")