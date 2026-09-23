"""Phase 3 toy MILP: 3-period battery dispatch, verifying the model against
a known-by-hand answer before scaling to the full 48-period problem."""

import pyomo.environ as pyo

# --- Toy problem setup: 3 periods, known-by-hand answer ---
prices = {1: 30, 2: 50, 3: 90}
CAPACITY = 2.0        # MWh
MAX_POWER = 2.0        # MW
ETA_C = 1.0             # lossless, for the toy
ETA_D = 1.0
INITIAL_SOC = 0.0

model = pyo.ConcreteModel()
model.T = pyo.RangeSet(1, 3)

model.charge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
model.discharge = pyo.Var(model.T, domain=pyo.NonNegativeReals)
model.soc = pyo.Var(model.T, domain=pyo.NonNegativeReals, bounds=(0, CAPACITY))
model.b = pyo.Var(model.T, domain=pyo.Binary)

#State-of-charge balance: soc[t] = soc[t-1] + charged energy - discharged energy
def soc_balance_rule(m, t):
    prev_soc = INITIAL_SOC if t == 1 else m.soc[t - 1]
    return m.soc[t] == prev_soc + ETA_C * m.charge[t] - m.discharge[t] / ETA_D


model.soc_balance = pyo.Constraint(model.T, rule=soc_balance_rule)

#Charge/discharge capped by MAX_POWER, gated by binary b[t] so both can't be active at once.
def charge_limit_rule(m, t):
    return m.charge[t] <= MAX_POWER * m.b[t]


model.charge_limit = pyo.Constraint(model.T, rule=charge_limit_rule)

#Charge/discharge capped by MAX_POWER, gated by binary b[t] so both can't be active at once.
def discharge_limit_rule(m, t):
    return m.discharge[t] <= MAX_POWER * (1 - m.b[t])


model.discharge_limit = pyo.Constraint(model.T, rule=discharge_limit_rule)

#Maximize profit: sell high (discharge), buy low (charge), same price series both ways
def objective_rule(m):
    return sum(prices[t] * m.discharge[t] - prices[t] * m.charge[t] for t in m.T)


model.objective = pyo.Objective(rule=objective_rule, sense=pyo.maximize)


if __name__ == "__main__":
    solver = pyo.SolverFactory('appsi_highs')
    result = solver.solve(model, tee=False)

    print("Solver status:", result.solver.status, result.solver.termination_condition)
    print(f"\nProfit: £{pyo.value(model.objective):.2f}\n")
    for t in model.T:
        print(f"Period {t}: price=£{prices[t]}  charge={pyo.value(model.charge[t]):.2f}  "
              f"discharge={pyo.value(model.discharge[t]):.2f}  soc={pyo.value(model.soc[t]):.2f}  "
              f"b={pyo.value(model.b[t]):.0f}")