from __future__ import annotations

import math
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


def build_legs(
    strategy: str,
    options: list[dict[str, Any]],
    spot: float,
    expiry: str,
    target_price: float | None,
    target_range: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    calls = option_rows(options, expiry, "call")
    puts = option_rows(options, expiry, "put")
    target_up = target_price if target_price and target_price > spot else spot * 1.08
    target_down = target_price if target_price and target_price < spot else spot * 0.92
    range_low = float(target_range["lower"]) if target_range and target_range.get("lower") else None
    range_high = float(target_range["upper"]) if target_range and target_range.get("upper") else None

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

    put_sell = pick_by_strike(puts, range_low, "sell", maximum=spot - 1) if range_low and range_low < spot else pick_by_delta(puts, -0.18, "sell")
    call_sell = pick_by_strike(calls, range_high, "sell", minimum=spot + 1) if range_high and range_high > spot else pick_by_delta(calls, 0.18, "sell")
    put_buy = pick_by_strike(puts, put_sell["strike"] * 0.94, "buy", maximum=put_sell["strike"] - 1)
    call_buy = pick_by_strike(calls, call_sell["strike"] * 1.06, "buy", minimum=call_sell["strike"] + 1)
    return [leg(put_sell, "sell"), leg(put_buy, "buy"), leg(call_sell, "sell"), leg(call_buy, "buy")]


def risk_notes(strategy: str) -> list[str]:
    notes = ["本工具用于研究和教育，不构成投资建议。"]
    if strategy in {"Short Strangle", "Short Straddle", "Call Ratio Spread", "Put Ratio Spread"}:
        notes.append("该策略含高级卖方或比例风险，不适合不了解尾部风险的新手直接交易。")
    return notes


MIN_BTC_OPTION_QUANTITY = 0.1
DEFAULT_BTC_OPTION_QUANTITY = 0.1


def round_down_quantity(value: float) -> float:
    if value < MIN_BTC_OPTION_QUANTITY:
        return 0.0
    return max(MIN_BTC_OPTION_QUANTITY, math.floor(value * 10) / 10)


def apply_position_sizing(legs: list[dict[str, Any]], payoff: dict[str, Any], capital_usd: float | None) -> dict[str, Any]:
    max_loss = abs(float(payoff.get("estimated_min_pnl_usd") or 0))
    if not capital_usd or capital_usd <= 0:
        for item in legs:
            item["quantity"] = DEFAULT_BTC_OPTION_QUANTITY * float(item.get("quantity") or 1)
        return {
            "capital_usd": None,
            "base_max_loss_usd": max_loss,
            "recommended_quantity": DEFAULT_BTC_OPTION_QUANTITY,
            "adjusted": True,
            "insufficient": False,
            "message": "用户没有提供资金规模；BTC 期权最小交易单位为 0.1，因此默认按 0.1 份策略展示。",
        }

    if max_loss <= 0 or max_loss <= capital_usd:
        default_loss = max_loss * DEFAULT_BTC_OPTION_QUANTITY
        for item in legs:
            item["quantity"] = DEFAULT_BTC_OPTION_QUANTITY * float(item.get("quantity") or 1)
        return {
            "capital_usd": capital_usd,
            "base_max_loss_usd": max_loss,
            "recommended_quantity": DEFAULT_BTC_OPTION_QUANTITY,
            "adjusted": True,
            "insufficient": False,
            "message": f"按 1 份策略估算最大亏损约 ${max_loss:,.0f}；BTC 期权最小交易单位为 0.1，默认建议 0.1 份，对应最大亏损约 ${default_loss:,.0f}。",
        }

    quantity = round_down_quantity(capital_usd / max_loss)
    if quantity <= 0:
        for item in legs:
            item["quantity"] = MIN_BTC_OPTION_QUANTITY * float(item.get("quantity") or 1)
        return {
            "capital_usd": capital_usd,
            "base_max_loss_usd": max_loss,
            "recommended_quantity": MIN_BTC_OPTION_QUANTITY,
            "adjusted": True,
            "insufficient": True,
            "message": f"按 1 份策略估算最大亏损约 ${max_loss:,.0f}；即使用最小 0.1 份，估算最大亏损也约 ${max_loss * MIN_BTC_OPTION_QUANTITY:,.0f}，高于你提供的 ${capital_usd:,.0f} 资金。",
        }
    for item in legs:
        item["quantity"] = quantity * float(item.get("quantity") or 1)
    return {
        "capital_usd": capital_usd,
        "base_max_loss_usd": max_loss,
        "recommended_quantity": quantity,
        "adjusted": True,
        "insufficient": False,
        "message": f"按 1 份策略估算最大亏损约 ${max_loss:,.0f}，超过你提供的 ${capital_usd:,.0f} 资金；因此建议把数量降到 {quantity:g} 份。",
    }


def select_strategy(market: dict[str, Any], intent: dict[str, Any], market_view: dict[str, Any]) -> dict[str, Any]:
    spot = float(market["spot"])
    expiry = closest_expiry(market["options"], int(intent["horizon_days"]))
    strategy = choose_strategy_name(intent, market_view)
    legs = build_legs(strategy, market["options"], spot, expiry, intent.get("target_price"), intent.get("target_range"))
    payoff = build_payoff(legs, spot, intent.get("target_price"))
    position_sizing = apply_position_sizing(legs, payoff, intent.get("capital_usd"))
    if position_sizing["adjusted"]:
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
        "position_sizing": position_sizing,
        "risk_notes": risk_notes(strategy),
    }
