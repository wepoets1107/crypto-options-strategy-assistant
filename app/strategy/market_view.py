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


def iv_label(iv_view: str) -> str:
    return {"cheap": "偏低", "normal": "中性", "expensive": "偏高"}.get(iv_view, "未知")


def flow_label(flow: str) -> str:
    return {"call_heavy": "大额成交偏 Call", "put_heavy": "大额成交偏 Put", "balanced": "大额成交相对均衡"}.get(flow, "大额成交不明确")


def build_market_view(market: dict[str, Any], intent: dict[str, Any]) -> dict[str, Any]:
    spot = float(market["spot"])
    features = market_features(market["options"], spot, int(intent["horizon_days"]))
    atm_iv = features.get("atm_iv")
    iv_view = classify_iv(atm_iv)
    skew = features.get("skew_25d")
    trade_bias = market.get("trade_bias", {}).get("bias", "balanced")
    target_price = intent.get("target_price")
    target_range = intent.get("target_range") or {}
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
    diagnostics = [
        f"到期选择：选择 {features['selected_expiry_label']}，约 {features['selected_expiry_days']:.1f} 天，覆盖用户的 {intent['horizon_days']} 天观点周期。",
    ]
    if atm_iv is not None:
        diagnostics.append(f"波动率：ATM IV 约 {atm_iv:.1f}%，系统判断为{iv_label(iv_view)}。IV 偏低时，买期权成本相对不贵；IV 偏高时，更适合谨慎考虑收权利金结构。")
    if skew is not None:
        if skew < -1:
            diagnostics.append(f"偏度：25D Skew 为 {skew:.2f}，Put 相对 Call 更贵，说明市场仍愿意为下跌保护付费。")
        elif skew > 1:
            diagnostics.append(f"偏度：25D Skew 为 {skew:.2f}，Call 相对 Put 更贵，说明上行需求更强。")
        else:
            diagnostics.append(f"偏度：25D Skew 为 {skew:.2f}，两边定价比较接近，没有明显单边情绪。")
    flow = market.get("trade_bias", {})
    diagnostics.append(
        f"大额成交：{flow_label(trade_bias)}；24小时大额 Call 数量约 {flow.get('large_call_amount', 0):.0f}，Put 数量约 {flow.get('large_put_amount', 0):.0f}。"
    )
    if expected_move is not None:
        diagnostics.append(f"隐含波动范围：按当前 IV 粗略估算，{intent['horizon_days']} 天一倍隐含波动约为 ${expected_move:,.0f}。")
    if target_z is not None:
        diagnostics.append(f"目标难度：用户目标距离现货约 {target_z:.2f} 倍隐含波动；数值越高，越偏向小概率事件。")
    if target_range.get("lower") and target_range.get("upper"):
        diagnostics.append(
            f"用户区间：用户给出的主要波动区间是 ${target_range['lower']:,.0f} 到 ${target_range['upper']:,.0f}。系统会优先围绕这个区间设计收权利金结构。"
        )
    if max_gamma:
        diagnostics.append(f"Gamma 位置：30D 内最大 Gamma 敞口在 ${max_gamma['strike']:,.0f} 附近，价格接近该区域时可能更容易反复。")
    return {
        "features": features,
        "alignment": alignment,
        "volatility_view": iv_view,
        "skew_view": "call_rich" if skew and skew > 0 else "put_rich" if skew and skew < 0 else "balanced",
        "trade_flow_view": trade_bias,
        "expected_move_usd": expected_move,
        "target_z_score": target_z,
        "reasons": reasons[:6],
        "diagnostics": diagnostics,
    }
