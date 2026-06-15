from __future__ import annotations

import math
from typing import Any

from app.market_data.deribit import market_features


def classify_iv(atm_iv: float | None) -> str:
    if atm_iv is None:
        return "unknown"
    if atm_iv >= 65:
        return "expensive"
    if atm_iv <= 45:
        return "cheap"
    return "normal"


def build_market_view(market: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    spot = float(market["spot"])
    features = market_features(market["options"], spot, int(intent["horizon_days"]))
    atm_iv = features.get("atm_iv")
    iv_view = classify_iv(atm_iv)
    skew = features.get("skew_25d")
    trade_bias = market.get("trade_bias", {}).get("bias", "balanced")
    target_price = intent.get("target_price")
    expected_move = None
    target_z = None
    if atm_iv:
        expected_move = spot * (atm_iv / 100) * math.sqrt(intent["horizon_days"] / 365)
        if target_price:
            target_z = abs(target_price - spot) / expected_move if expected_move else None

    score = 0.5
    reasons = []
    direction = intent["direction"]
    if direction == "bullish":
        if skew is not None and skew > 0:
            score += 0.08
            reasons.append("25D skew 偏正，Call 相对更贵，市场有一定上行定价。")
        if trade_bias == "call_heavy":
            score += 0.08
            reasons.append("最近 24 小时大额成交偏 Call。")
    elif direction == "bearish":
        if skew is not None and skew < 0:
            score += 0.08
            reasons.append("25D skew 偏负，Put 保护需求更强。")
        if trade_bias == "put_heavy":
            score += 0.08
            reasons.append("最近 24 小时大额成交偏 Put。")
    elif direction == "range":
        if iv_view == "expensive":
            score += 0.12
            reasons.append("当前 IV 偏贵，更适合考虑有限风险的收权利金结构。")

    if target_z is not None and target_z > 1.5:
        score -= 0.12
        reasons.append("用户目标价距离当前价格超过约 1.5 倍隐含波动，胜率假设需要保守。")
    elif target_z is not None:
        score += 0.04
        reasons.append("目标价格在隐含波动范围内，路径假设相对可讨论。")

    max_gamma = features.get("max_gamma")
    if max_gamma and target_price:
        distance = abs(max_gamma["strike"] - target_price) / spot
        if distance < 0.03:
            score -= 0.05
            reasons.append("目标价附近存在较大的 30D Gamma 敞口，价格可能在该区域反复。")

    score = max(0.05, min(0.95, score))
    alignment = "supports" if score >= 0.65 else "partially_supports" if score >= 0.45 else "does_not_support"
    if not reasons:
        reasons.append("市场信号较均衡，策略需要以控制亏损为优先。")
    return {
        "features": features,
        "direction_confidence": round(score, 2),
        "alignment": alignment,
        "volatility_view": iv_view,
        "skew_view": "call_rich" if skew and skew > 0 else "put_rich" if skew and skew < 0 else "balanced",
        "trade_flow_view": trade_bias,
        "expected_move_usd": expected_move,
        "target_z_score": target_z,
        "reasons": reasons[:4],
    }
