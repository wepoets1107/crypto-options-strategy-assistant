from __future__ import annotations

import re
from typing import Any

from app.config import Settings
from app.llm.client import chat_json
from app.llm.prompts import INTENT_SYSTEM_PROMPT


def _target_move_from_text(text: str) -> float | None:
    text = text.replace(",", "")
    patterns = [
        r"(上涨|涨|上行|上冲|突破)\s*(\d+(?:\.\d+)?)\s*万",
        r"(下跌|跌|回落|跌破)\s*(\d+(?:\.\d+)?)\s*万",
        r"(上涨|涨|上行|上冲|突破)\s*(\d+(?:\.\d+)?)\s*(?:美元|美金|刀|u|U|USDT|usdt)",
        r"(下跌|跌|回落|跌破)\s*(\d+(?:\.\d+)?)\s*(?:美元|美金|刀|u|U|USDT|usdt)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        number = float(match.groups()[-1])
        return number * 10000 if "万" in match.group(0) else number
    return None


def _target_price_from_text(text: str) -> float | None:
    text = text.replace(",", "")
    patterns = [
        r"(?:涨到|涨至|升到|升至|上看|看到|达到|到达|目标价(?:是|为|到)?|目标(?:是|为|到)?)\s*(\d+(?:\.\d+)?)\s*(万)?\s*(?:美元|美金|刀|u|U|USDT|usdt)?",
        r"(?:跌到|跌至|回落到|回落至|下看)\s*(\d+(?:\.\d+)?)\s*(万)?\s*(?:美元|美金|刀|u|U|USDT|usdt)?",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            number = float(match.group(1))
            return number * 10000 if match.group(2) else number
    return None


def _capital_from_text(text: str) -> float | None:
    text = text.replace(",", "")
    capital_patterns = [
        r"(?:我有|本金|资金|预算|仓位|账户|投入|投|拿出|计划投入)\s*(\d+(?:\.\d+)?)\s*(万)?\s*(?:u|U|USDT|usdt|美元|美金|刀)",
        r"(?:我有|本金|资金|预算|仓位|账户|投入|投|拿出|计划投入)\D{0,8}?(\d+(?:\.\d+)?)\s*(万)?\s*(?:u|U|USDT|usdt|美元|美金|刀)",
    ]
    for pattern in capital_patterns:
        match = re.search(pattern, text)
        if match:
            number = float(match.group(1))
            return number * 10000 if match.group(2) else number

    patterns = [
        r"(?:我有|本金|资金|预算|仓位|账户|投入|投|拿出|计划投入)\s*(\d+(?:\.\d+)?)\s*(?:u|U|USDT|usdt|美元|美金|刀)",
        r"(\d+(?:\.\d+)?)\s*(?:u|U|USDT|usdt)\b",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def _position_quantity_from_text(text: str, asset: str) -> float | None:
    asset_pattern = rf"(?:{asset.upper()}|{asset.lower()}|{'以太坊' if asset.upper() == 'ETH' else '比特币'})"
    patterns = [
        rf"(?:我有|持有|手里有|仓位)\s*(\d+(?:\.\d+)?)\s*(?:个|枚|张|份)?\s*{asset_pattern}",
        rf"(\d+(?:\.\d+)?)\s*(?:个|枚|张|份)?\s*{asset_pattern}",
    ]
    normalized = text.replace(",", "")
    for pattern in patterns:
        match = re.search(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return float(match.group(1))
    return None


def _position_avg_cost_from_text(text: str) -> float | None:
    normalized = text.replace(",", "")
    patterns = [
        r"(?:均价|成本价|持仓成本|买入成本|成本)\s*(\d+(?:\.\d+)?)\s*(?:美元|美金|刀|u|U|USDT|usdt)?",
        r"(?:均价|成本价|持仓成本|买入成本|成本)\D{0,4}?(\d+(?:\.\d+)?)",
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return float(match.group(1))
    return None


def _hedge_intent_from_text(text: str) -> bool:
    return any(word in text for word in ["买保险", "保险", "保护", "锁住盈利", "锁定盈利", "对冲", "防跌", "保住利润"])


def _number_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _money_amount(value: str, unit: str | None) -> float:
    number = float(value)
    return number * 10000 if unit == "万" else number


def _target_range_from_text(text: str) -> dict[str, float] | None:
    text = text.replace(",", "")
    patterns = [
        r"(\d+(?:\.\d+)?)\s*(万)?\s*(?:到|至|-|~)\s*(\d+(?:\.\d+)?)\s*(万)?\s*(?:之间|区间|附近|内)?",
        r"(\d+(?:\.\d+)?)\s*(万)?\s*(?:和|与)\s*(\d+(?:\.\d+)?)\s*(万)?\s*(?:之间|区间|附近|内)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        first = _money_amount(match.group(1), match.group(2) or match.group(4))
        second = _money_amount(match.group(3), match.group(4) or match.group(2))
        low, high = sorted([first, second])
        if high > low > 0:
            return {"lower": low, "upper": high}
    return None


def parse_intent_rules(text: str, quick: dict[str, Any] | None, spot: float, asset: str = "BTC") -> dict[str, Any]:
    lower = text.lower()
    target_range = _target_range_from_text(text)
    direction = (quick or {}).get("direction") or "unknown"
    if direction == "unknown":
        if any(word in text for word in ["看涨", "上涨", "涨", "暴涨", "突破", "牛市"]):
            direction = "bullish"
        elif any(word in text for word in ["看跌", "下跌", "跌", "回落", "熊市"]):
            direction = "bearish"
        elif target_range or any(word in text for word in ["横盘", "震荡", "区间", "不涨不跌", "做空波动", "空波动率", "卖波动率", "之间波动", "范围内"]):
            direction = "range"
        elif any(word in text for word in ["大波动", "波动很大", "方向不确定", "暴涨暴跌"]):
            direction = "volatile"

    horizon_days = int((quick or {}).get("horizon_days") or 30)
    if any(word in text for word in ["一周", "7天", "七天", "week"]):
        horizon_days = 7
    elif any(word in text for word in ["一个月", "1个月", "30天", "month"]):
        horizon_days = 30
    elif any(word in text for word in ["三个月", "3个月", "90天", "quarter"]):
        horizon_days = 90

    target_price = _target_price_from_text(text)
    target_move = None if target_price else _target_move_from_text(text)
    if target_move:
        if direction == "bearish":
            target_price = max(1, spot - target_move)
        elif direction == "bullish":
            target_price = spot + target_move

    income_preference = any(word in text for word in ["收权利金", "卖期权", "赚时间价值", "卖方", "不跌破", "不涨破", "做空波动", "空波动率", "卖波动率"])
    advanced = any(word in lower for word in ["advanced", "ratio", "short straddle", "short strangle"]) or any(
        word in text for word in ["高级", "比例价差", "裸卖", "双卖"]
    )
    position_quantity = _position_quantity_from_text(text, asset)
    hedge_intent = _hedge_intent_from_text(text)
    if hedge_intent and direction == "unknown":
        direction = "bearish"
    return {
        "asset": asset,
        "direction": direction,
        "horizon_days": horizon_days,
        "target_move_usd": target_move,
        "target_price": target_price,
        "target_range": target_range,
        "capital_usd": _capital_from_text(text),
        "position_quantity": position_quantity,
        "position_avg_cost": _position_avg_cost_from_text(text) if position_quantity else None,
        "hedge_intent": hedge_intent,
        "risk_profile": "advanced" if advanced else "beginner",
        "income_preference": income_preference,
        "notes": text or "快捷观点",
    }


def normalize_intent(raw: dict[str, Any], fallback: dict[str, Any], spot: float, asset: str = "BTC") -> dict[str, Any]:
    direction = raw.get("direction") if raw.get("direction") in {"bullish", "bearish", "range", "volatile"} else fallback["direction"]
    horizon_days = int(raw.get("horizon_days") or fallback["horizon_days"] or 30)
    fallback_target_price = fallback.get("target_price")
    target_price = raw.get("target_price") if raw.get("target_price") is not None else fallback_target_price
    target_move = raw.get("target_move_usd") if fallback_target_price is None else fallback.get("target_move_usd")
    target_range = raw.get("target_range") or fallback.get("target_range")
    if target_price is None and target_move is not None:
        target_price = spot + float(target_move) if direction == "bullish" else spot - float(target_move)
    position_quantity = _number_or_none(raw.get("position_quantity"))
    if position_quantity is None:
        position_quantity = fallback.get("position_quantity")
    position_avg_cost = _number_or_none(raw.get("position_avg_cost"))
    if position_avg_cost is None:
        position_avg_cost = fallback.get("position_avg_cost")
    hedge_intent = bool(raw.get("hedge_intent", fallback.get("hedge_intent", False)))
    if hedge_intent and direction == "unknown":
        direction = "bearish"
    return {
        "asset": asset,
        "direction": direction,
        "horizon_days": max(1, min(horizon_days, 180)),
        "target_move_usd": float(target_move) if target_move is not None else fallback.get("target_move_usd"),
        "target_price": float(target_price) if target_price is not None else fallback.get("target_price"),
        "target_range": target_range,
        "capital_usd": _number_or_none(raw.get("capital_usd")) if raw.get("capital_usd") is not None else fallback.get("capital_usd"),
        "position_quantity": position_quantity,
        "position_avg_cost": position_avg_cost,
        "hedge_intent": hedge_intent,
        "risk_profile": raw.get("risk_profile") or fallback.get("risk_profile", "beginner"),
        "income_preference": bool(raw.get("income_preference", fallback.get("income_preference", False))),
        "notes": raw.get("notes") or fallback.get("notes", ""),
    }


def empty_fallback(text: str, quick: dict[str, Any] | None, asset: str) -> dict[str, Any]:
    return {
        "asset": asset,
        "direction": (quick or {}).get("direction") or "unknown",
        "horizon_days": int((quick or {}).get("horizon_days") or 30),
        "target_move_usd": None,
        "target_price": None,
        "target_range": None,
        "capital_usd": None,
        "position_quantity": None,
        "position_avg_cost": None,
        "hedge_intent": False,
        "risk_profile": "beginner",
        "income_preference": False,
        "notes": text,
    }


async def parse_intent(text: str, quick: dict[str, Any] | None, spot: float, settings: Settings, asset: str = "BTC", require_llm: bool = False) -> dict[str, Any]:
    if require_llm:
        prompt_text = f"Selected asset: {asset}\nUser text: {text}"
        raw = await chat_json(settings, INTENT_SYSTEM_PROMPT, prompt_text)
        if not raw:
            raise ValueError("大模型没有返回可用的 JSON 解析结果。")
        # LLM is the primary parser for complex prompts. Rule parsing only fills
        # obviously stated numbers if the model omits a structured field.
        return normalize_intent(raw, parse_intent_rules(text, quick, spot, asset), spot, asset)

    fallback = parse_intent_rules(text, quick, spot, asset)
    if not settings.llm_enabled or not text.strip():
        return fallback
    try:
        raw = await chat_json(settings, INTENT_SYSTEM_PROMPT, text)
    except Exception:
        raw = None
    if not raw:
        return fallback
    return normalize_intent(raw, fallback, spot, asset)
