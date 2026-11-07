"""Agent Hire Kit v26.10.31: undiscounted replacement payback model."""
import argparse
import json
import math


def calculate_payback(exit_cost_per_role, roles_cut, loaded_annual_cost_per_role,
                      agent_annual_run_cost, residual_share,
                      residual_staffing_cost=None, implementation_cost=0,
                      human_unit_cost=None, annual_units=None):
    """Costs are total-scope except the two explicitly per-role inputs.

    residual_staffing_cost is annual human cost at 100% residual workload,
    NOT an already share-adjusted bill. Alternatively supply human_unit_cost
    and annual_units for the full annual workload. Residual cost scales linearly.
    """
    values = dict(exit_cost_per_role=exit_cost_per_role, roles_cut=roles_cut,
                  loaded_annual_cost_per_role=loaded_annual_cost_per_role,
                  agent_annual_run_cost=agent_annual_run_cost,
                  residual_share=residual_share, implementation_cost=implementation_cost)
    for name, value in values.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError(name + " must be a finite nonnegative number")
    if not isinstance(roles_cut, int) or roles_cut < 1:
        raise ValueError("roles_cut must be a positive integer")
    if residual_share > 1:
        raise ValueError("residual_share must be between 0 and 1")
    unit_mode = human_unit_cost is not None or annual_units is not None
    if unit_mode:
        if residual_staffing_cost is not None or human_unit_cost is None or annual_units is None:
            raise ValueError("use staffing cost OR both unit cost and annual units")
        costs = (human_unit_cost, annual_units)
    else:
        if residual_staffing_cost is None:
            raise ValueError("supply residual_staffing_cost or unit inputs")
        costs = (residual_staffing_cost,)
    for value in costs:
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
            raise ValueError("residual cost inputs must be finite and nonnegative")
    full_human_cost = human_unit_cost * annual_units if unit_mode else residual_staffing_cost
    baseline = roles_cut * loaded_annual_cost_per_role
    upfront = roles_cut * exit_cost_per_role + implementation_cost

    def scenario(share):
        residual = share * full_human_cost
        monthly = (baseline - agent_annual_run_cost - residual) / 12
        position = monthly * 24 - upfront
        if not all(math.isfinite(x) for x in (residual, monthly, position, upfront)):
            raise ValueError("inputs exceed finite model range")
        payback = upfront / monthly if monthly > 0 else None
        if payback is not None and not math.isfinite(payback):
            raise ValueError("payback exceeds finite model range")
        return dict(residual_share=share, residual_annual_cost=residual,
                    net_monthly_saving=monthly, payback_months=payback,
                    net_position_24_months=position,
                    status="payback" if monthly > 0 else "no payback")
    result = scenario(residual_share)
    result.update(upfront_cost=upfront, baseline_annual_cost=baseline,
                  sensitivity=[scenario(s) for s in (0.05, 0.10, 0.20, 0.30)])
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("exit-cost-per-role", "loaded-annual-cost-per-role", "agent-annual-run-cost", "residual-share"):
        parser.add_argument("--" + name, type=float, required=True)
    parser.add_argument("--roles-cut", type=int, required=True)
    parser.add_argument("--implementation-cost", type=float, default=0)
    parser.add_argument("--residual-staffing-cost", type=float, help="annual total-scope human cost at 100%% residual workload")
    parser.add_argument("--human-unit-cost", type=float)
    parser.add_argument("--annual-units", type=float)
    args = parser.parse_args()
    try:
        result = calculate_payback(**vars(args))
    except ValueError as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
