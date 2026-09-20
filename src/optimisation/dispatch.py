"""Phase 3: reusable battery dispatch MILP. Pulls real day-ahead prices from
the database, builds and solves the optimisation, and runs physical sanity
checks. Designed to be called repeatedly by Phase 4's backtester."""

import sqlite3
import pyomo.environ as pyo
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "gb_prices.db")

def load_day_ahead_prices(settlement_date: str) -> dict:
    """Returns {settlement_period: price} for one settlement date."""
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute(
        "SELECT settlement_period, value FROM price_series "
        "WHERE series_id = 'gb_day_ahead_price' AND settlement_date = ? "
        "ORDER BY settlement_period",
        (settlement_date,)
    ).fetchall()
    conn.close()

    prices = {period: value for period, value in rows}
    missing = set(range(1, 49)) - set(prices.keys())
    if missing:
        print(f"Warning: {settlement_date} is missing periods {sorted(missing)}")
    return prices


def build_dispatch_model(prices: dict, capacity: float, max_power: float,
                          eta_c: float, eta_d: float, initial_soc: float = 0.0) -> pyo.ConcreteModel:
    """Builds (but does not solve) a battery dispatch MILP for the given prices."""
    periods = sorted(prices.keys())

    model = pyo.ConcreteModel()
    model.T = pyo.Set(initialize=periods, ordered=True)

    model.charge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.discharge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
    model.soc = pyo.Var(model.T, domain=pyo.NonNegativeReals, bounds=(0, capacity))
    model.b = pyo.Var(model.T, domain=pyo.Binary)

    def soc_balance_rule(m, t):
        idx = periods.index(t)
        prev_soc = initial_soc if idx == 0 else m.soc[periods[idx - 1]]
        return m.soc[t] == prev_soc + eta_c * m.charge[t] - m.discharge[t] / eta_d
    model.soc_balance = pyo.Constraint(model.T, rule=soc_balance_rule)

    def charge_limit_rule(m, t):
        return m.charge[t] <= max_power * m.b[t]
    model.charge_limit = pyo.Constraint(model.T, rule=charge_limit_rule)

    def discharge_limit_rule(m, t):
        return m.discharge[t] <= max_power * (1 - m.b[t])
    model.discharge_limit = pyo.Constraint(model.T, rule=discharge_limit_rule)

    def objective_rule(m):
        return sum(prices[t] * m.discharge[t] - prices[t] * m.charge[t] for t in m.T)
    model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)

    return model


def solve_dispatch(model: pyo.ConcreteModel, prices: dict) -> tuple[float, list[dict]]:
    """Solves a built model, returns (profit, schedule)."""
    solver = pyo.SolverFactory('appsi_highs')
    result = solver.solve(model, tee=False)

    if result.solver.termination_condition != pyo.TerminationCondition.optimal:
        raise RuntimeError(f"Solver did not find an optimal solution: {result.solver.termination_condition}")

    profit = pyo.value(model.objective)
    schedule = []
    for t in model.T:
        schedule.append({
            "period": t,
            "price": prices[t],
            "charge": pyo.value(model.charge[t]),
            "discharge": pyo.value(model.discharge[t]),
            "soc": pyo.value(model.soc[t]),
        })
    return profit, schedule


def run_dispatch(prices: dict, capacity: float, max_power: float,
                  eta_c: float, eta_d: float, initial_soc: float = 0.0) -> tuple[float, list[dict]]:
    """One-call convenience wrapper: build + solve. This is what Phase 4's
    backtester should call, once per day, across many days."""
    model = build_dispatch_model(prices, capacity, max_power, eta_c, eta_d, initial_soc)
    return solve_dispatch(model, prices)


def check_schedule(schedule: list[dict], capacity: float, max_power: float,
                    eta_c: float, eta_d: float, tol: float = 0.01) -> dict:
    """Runs physical sanity checks against a solved schedule."""
    simultaneous = [r["period"] for r in schedule if r["charge"] > tol and r["discharge"] > tol]
    soc_breach = [r["period"] for r in schedule if r["soc"] < -tol or r["soc"] > capacity + tol]
    power_breach = [r["period"] for r in schedule
                     if r["charge"] > max_power + tol or r["discharge"] > max_power + tol]

    charge_prices = [r["price"] for r in schedule if r["charge"] > tol]
    discharge_prices = [r["price"] for r in schedule if r["discharge"] > tol]

    return {
        "simultaneous_charge_discharge": simultaneous,
        "soc_out_of_bounds": soc_breach,
        "power_limit_breaches": power_breach,
        "charge_price_range": (min(charge_prices), max(charge_prices)) if charge_prices else None,
        "discharge_price_range": (min(discharge_prices), max(discharge_prices)) if discharge_prices else None,
        "breakeven_multiplier": 1 / (eta_c * eta_d),
        "all_clean": not simultaneous and not soc_breach and not power_breach,
    }


if __name__ == "__main__":
    prices = load_day_ahead_prices("2026-07-20")

    profit, schedule = run_dispatch(prices, capacity=10.0, max_power=5.0, eta_c=0.922, eta_d=0.922)
    print(f"Profit: £{profit:.2f}\n")

    for r in schedule:
        action = "CHARGE" if r["charge"] > 0.01 else ("DISCHARGE" if r["discharge"] > 0.01 else "idle")
        print(f"P{r['period']:2d}  price=£{r['price']:6.2f}  {action:9s}  soc={r['soc']:5.2f}")

    checks = check_schedule(schedule, capacity=10.0, max_power=5.0, eta_c=0.922, eta_d=0.922)
    print(f"\nAll checks clean: {checks['all_clean']}")
    print(f"Charge range: £{checks['charge_price_range'][0]:.2f}-£{checks['charge_price_range'][1]:.2f}")
    print(f"Discharge range: £{checks['discharge_price_range'][0]:.2f}-£{checks['discharge_price_range'][1]:.2f}")