from __future__ import annotations

from typing import Any


def intrinsic(price: float, strike: float, option_type: str) -> float:
    if option_type == "call":
        return max(price - strike, 0.0)
    return max(strike - price, 0.0)


def leg_pnl_usd(leg: dict[str, Any], expiry_price: float, spot: float) -> float:
    qty = int(leg.get("quantity") or 1)
    premium = float(leg.get("price_btc") or 0) * spot * qty
    value = intrinsic(expiry_price, float(leg["strike"]), leg["option_type"]) * qty
    if leg["side"] == "buy":
        return value - premium
    return premium - value


def build_payoff(legs: list[dict[str, Any]], spot: float, target_price: float | None) -> dict[str, Any]:
    strikes = [float(leg["strike"]) for leg in legs]
    low = min(strikes + [spot, target_price or spot]) * 0.82
    high = max(strikes + [spot, target_price or spot]) * 1.18
    step = (high - low) / 80
    points = []
    for index in range(81):
        price = low + step * index
        pnl = sum(leg_pnl_usd(leg, price, spot) for leg in legs)
        points.append({"price": price, "pnl": pnl})

    breakevens = []
    for prev, curr in zip(points, points[1:]):
        if prev["pnl"] == 0:
            breakevens.append(prev["price"])
        if (prev["pnl"] < 0 <= curr["pnl"]) or (prev["pnl"] > 0 >= curr["pnl"]):
            span = curr["price"] - prev["price"]
            denom = abs(prev["pnl"]) + abs(curr["pnl"])
            if denom:
                breakevens.append(prev["price"] + span * abs(prev["pnl"]) / denom)

    pnl_values = [point["pnl"] for point in points]
    target_pnl = None
    if target_price:
        target_pnl = sum(leg_pnl_usd(leg, target_price, spot) for leg in legs)

    return {
        "points": points,
        "markers": {"spot": spot, "target": target_price, "breakevens": breakevens[:4]},
        "estimated_min_pnl_usd": min(pnl_values),
        "estimated_max_pnl_usd": max(pnl_values),
        "target_pnl_usd": target_pnl,
    }


def premium_summary(legs: list[dict[str, Any]], spot: float) -> dict[str, Any]:
    net = 0.0
    for item in legs:
        value = float(item.get("price_btc") or 0) * spot * int(item.get("quantity") or 1)
        net += -value if item["side"] == "buy" else value
    return {
        "net_premium_usd": net,
        "net_premium_type": "credit" if net > 0 else "debit" if net < 0 else "flat",
        "net_premium_btc_est": net / spot if spot else 0,
    }
