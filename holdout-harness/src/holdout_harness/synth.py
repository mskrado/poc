"""Synthetic data generators. Output is synthetic test data, not carrier data.

Route panel: markets hold 1-3 competing routes; every route has a pre period and
a test period. The test period carries a network-wide fare move (think fuel) that
hits both arms, plus the true engine lift on treated routes only. Pre/post on the
treated arm sees both; the holdout sees only the lift.
"""
import math
import random

DOW = [0.92, 0.95, 1.00, 1.02, 1.10, 1.08, 0.93]


def make_routes(seed, n_markets=48):
    rng = random.Random(seed)
    route_to_market, base = {}, {}
    for m in range(1, n_markets + 1):
        market = f"MKT{m:02d}"
        k = rng.choices([1, 2, 3], weights=[0.45, 0.35, 0.20])[0]
        for r in range(1, k + 1):
            route = f"{market}-R{r}"
            route_to_market[route] = market
            base[route] = math.exp(rng.gauss(math.log(30000), 0.6))
    return route_to_market, base


def route_panel(seed, route_to_market, base, route_arm, pre_days=28, test_days=28,
                lift=0.02, macro=0.10, steal=0.04, noise=0.12):
    """Daily revenue per route (synthetic USD).

    `steal`: in a market where treated and control routes coexist, the treated
    route takes this share of its control siblings' daily revenue. That's the
    spillover a market-level split prevents.
    Returns list of dict rows: route, market, arm, day, period, revenue.
    """
    rng = random.Random(seed + 1)
    siblings = {}
    for r, m in route_to_market.items():
        siblings.setdefault(m, []).append(r)
    rows = []
    for day in range(pre_days + test_days):
        test = day >= pre_days
        daily = {}
        for r in sorted(route_to_market):
            v = base[r] * DOW[day % 7] * math.exp(rng.gauss(0, noise))
            if test:
                v *= 1 + macro
                if route_arm[r] == "treatment":
                    v *= 1 + lift
            daily[r] = v
        if test and steal:
            for m, rs in siblings.items():
                t = [r for r in rs if route_arm[r] == "treatment"]
                c = [r for r in rs if route_arm[r] == "control"]
                if t and c:
                    pool = sum(daily[r] * steal for r in c)
                    for r in c:
                        daily[r] *= 1 - steal
                    for r in t:
                        daily[r] += pool / len(t)
        for r in sorted(route_to_market):
            rows.append({"route": r, "market": route_to_market[r], "arm": route_arm[r], "day": day,
                         "period": "test" if test else "pre", "revenue": round(daily[r], 2)})
    return rows


def booking_sessions(seed, salt, n_customers=60000, n_routes=30, price_lift=0.04,
                     conv_drop=0.015, base_conv=0.08, repeat_share=0.25):
    """Booking-cohort data: arm is hashed per session, revenue per session.

    A quarter of customers search more than once, so some see both arms. Those
    who do book in the cheaper (control) session: the contamination the
    cross-bucket guard flags.
    """
    from .bucketing import assign
    rng = random.Random(seed + 2)
    fares = {f"RT{i:02d}": math.exp(rng.gauss(math.log(220), 0.4)) for i in range(n_routes)}
    routes = sorted(fares)
    sessions = []
    sid = 0
    for c in range(n_customers):
        cust = f"C{c:05d}"
        route = rng.choice(routes)
        k = rng.choice([2, 3]) if rng.random() < repeat_share else 1
        mine = []
        for _ in range(k):
            sid += 1
            s_id = f"S{sid:06d}"
            mine.append({"session_id": s_id, "customer_id": cust, "route": route,
                         "arm": assign(s_id, salt), "revenue": 0.0})
        arms = {s["arm"] for s in mine}
        fare = fares[route] * math.exp(rng.gauss(0, 0.15))
        u = rng.random()
        if len(arms) > 1:
            # saw both prices: books the control (cheaper) session if they book at all
            if u < base_conv:
                pick = next(s for s in mine if s["arm"] == "control")
                pick["revenue"] = round(fare, 2)
        else:
            s = rng.choice(mine)
            treated = s["arm"] == "treatment"
            conv = base_conv * (1 - conv_drop if treated else 1)
            if u < conv:
                s["revenue"] = round(fare * (1 + price_lift if treated else 1), 2)
        sessions.extend(mine)
    return sessions
