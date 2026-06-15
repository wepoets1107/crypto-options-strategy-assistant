from __future__ import annotations

from typing import Any

from app.market_data.deribit import closest_expiry
from app.strategy.contracts import leg, option_rows, pick_by_delta, pick_by_strike
from app.strategy.payoff import build_payoff, premium_summary


def choose_strategy_name(intent: dict[str, Any], market_view: dict[str, Any]) -> str:
    direction = intent["direction"]
    iv_view = market_view["volatility_view"]
    income = bool(intent.get("income_preference"))
    risk = intent.get("risk_profile", "beginner")
    target = intent.get("target_price")
    note = str(intent.get("notes") or "")

    if "铁蝶" in note or "iron butterfly" in note.lower():
        return "Iron Butterfly"
    if "比例" in note or "ratio" in note.lower():
        return "Call Ratio Spread" if direction == "bullish" else "Put Ratio Spread"
    if direction == "range":
        return "Iron Condor" if risk != "advanced" else "Short Strangle"
    if direction == "volatile":
        return "Long Strangle" if iv_view != "cheap" else "Long Straddle"
    if direction == "bullish":
        if income:
            return "Bull Put Spread"
        if target or iv_view in {"expensive", "normal"}:
            return "Bull Call Spread"
        return "Long Call"
    if direction == "bearish":
        if income:
            return "Bear Call Spread"
        if target or iv_view in {"expensive", "normal"}:
            return "Bear Put Spread"
        return "Long Put"
    return "Iron Condor"


def build_legs(strategy: str, options: list[dict[str, Any]], spot: float, expiry: str, target_price: float | None) -> list[dict[str, Any]]:
    calls = option_rows(options, expiry, "call")
    puts = option_rows(options, expiry, "put")
    target_up = target_price if target_price and target_price > spot else spot * 1.08
    target_down = target_price if target_price and target_price < spot else spot * 0.92

    if strategy == "Long Call":
        return [leg(pick_by_delta(calls, 0.45, "buy"), "buy")]
    if strategy == "Long Put":
        return [leg(pick_by_delta(puts, -0.45, "buy"), "buy")]
    if strategy == "Bull Call Spread":
        buy = pick_by_delta(calls, 0.45, "buy")
        sell = pick_by_strike(calls, target_up, "sell", minimum=buy["strike"] + 1)
        return [leg(buy, "buy"), leg(sell, "sell")]
    if strategy == "Bear Put Spread":
        buy = pick_by_delta(puts, -0.45, "buy")
        sell = pick_by_strike(puts, target_down, "sell", maximum=buy["strike"] - 1)
        return [leg(buy, "buy"), leg(sell, "sell")]
    if strategy == "Bull Put Spread":
        sell = pick_by_delta(puts, -0.25, "sell")
        buy = pick_by_strike(puts, sell["strike"] * 0.94, "buy", maximum=sell["strike"] - 1)
        return [leg(sell, "sell"), leg(buy, "buy")]
    if strategy == "Bear Call Spread":
        sell = pick_by_delta(calls, 0.25, "sell")
        buy = pick_by_strike(calls, sell["strike"] * 1.06, "buy", minimum=sell["strike"] + 1)
        return [leg(sell, "sell"), leg(buy, "buy")]
    if strategy == "Long Straddle":
        call = pick_by_strike(calls, spot, "buy")
        put = pick_by_strike(puts, spot, "buy")
        return [leg(call, "buy"), leg(put, "buy")]
    if strategy == "Long Strangle":
        call = pick_by_delta(calls, 0.25, "buy")
        put = pick_by_delta(puts, -0.25, "buy")
        return [leg(call, "buy"), leg(put, "buy")]
    if strategy == "Short Strangle":
        call = pick_by_delta(calls, 0.18, "sell")
        put = pick_by_delta(puts, -0.18, "sell")
        return [leg(call, "sell"), leg(put, "sell")]
    if strategy == "Iron Butterfly":
        short_call = pick_by_strike(calls, spot, "sell")
        short_put = pick_by_strike(puts, spot, "sell")
        long_call = pick_by_strike(calls, spot * 1.08, "buy", minimum=short_call["strike"] + 1)
        long_put = pick_by_strike(puts, spot * 0.92, "buy", maximum=short_put["strike"] - 1)
        return [leg(short_call, "sell"), leg(short_put, "sell"), leg(long_call, "buy"), leg(long_put, "buy")]
    if strategy == "Call Ratio Spread":
        buy = pick_by_delta(calls, 0.45, "buy")
        sell = pick_by_strike(calls, target_up, "sell", minimum=buy["strike"] + 1)
        return [leg(buy, "buy"), leg(sell, "sell", 2)]
    if strategy == "Put Ratio Spread":
        buy = pick_by_delta(puts, -0.45, "buy")
        sell = pick_by_strike(puts, target_down, "sell", maximum=buy["strike"] - 1)
        return [leg(buy, "buy"), leg(sell, "sell", 2)]

    put_sell = pick_by_delta(puts, -0.18, "sell")
    call_sell = pick_by_delta(calls, 0.18, "sell")
    put_buy = pick_by_strike(puts, put_sell["strike"] * 0.94, "buy", maximum=put_sell["strike"] - 1)
    call_buy = pick_by_strike(calls, call_sell["strike"] * 1.06, "buy", minimum=call_sell["strike"] + 1)
    return [leg(put_sell, "sell"), leg(put_buy, "buy"), leg(call_sell, "sell"), leg(call_buy, "buy")]


def risk_notes(strategy: str) -> list[str]:
    notes = ["本工具用于研究和教育，不构成投资建议。"]
    if strategy in {"Short Strangle", "Short Straddle", "Call Ratio Spread", "Put Ratio Spread"}:
        notes.append("该策略含高级卖方或比例风险，不适合不了解尾部风险的新手直接交易。")
    return notes


def select_strategy(market: dict[str, Any], intent: dict[str, Any], market_view: dict[str, Any]) -> dict[str, Any]:
    spot = float(market["spot"])
    expiry = closest_expiry(market["options"], int(intent["horizon_days"]))
    strategy = choose_strategy_name(intent, market_view)
    legs = build_legs(strategy, market["options"], spot, expiry, intent.get("target_price"))
    payoff = build_payoff(legs, spot, intent.get("target_price"))
    premium = premium_summary(legs, spot)
    return {
        "strategy_name": strategy,
        "asset": "BTC",
        "expiry": expiry,
        "expiry_label": legs[0]["expiry_label"] if legs else "",
        "spot": spot,
        "target_price": intent.get("target_price"),
        "legs": legs,
        "premium": premium,
        "payoff": payoff,
        "risk_notes": risk_notes(strategy),
    }
