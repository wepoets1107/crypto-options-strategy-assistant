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
        r"(\d+(?:\.\d+)?)\s*万美元",
        r"(\d+(?:\.\d+)?)\s*美元",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if not match:
            continue
        number = float(match.groups()[-1])
        return number * 10000 if "万" in match.group(0) else number
    return None


def _capital_from_text(text: str) -> float | None:
    text = text.replace(",", "")
    patterns = [
        r"(?:我有|本金|资金|预算|仓位|账户)\s*(\d+(?:\.\d+)?)\s*(?:u|U|USDT|usdt|美元|美金|刀)",
        r"(\d+(?:\.\d+)?)\s*(?:u|U|USDT|usdt)\b",
        r"(\d+(?:\.\d+)?)\s*(?:美元|美金|刀)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return float(match.group(1))
    return None


def parse_intent_rules(text: str, quick: dict[str, Any] | None, spot: float) -> dict[str, Any]:
    lower = text.lower()
    direction = (quick or {}).get("direction") or "unknown"
    if direction == "unknown":
        if any(word in text for word in ["看涨", "上涨", "涨", "暴涨", "突破", "牛市"]):
            direction = "bullish"
        elif any(word in text for word in ["看跌", "下跌", "跌", "回落", "熊市"]):
            direction = "bearish"
        elif any(word in text for word in ["横盘", "震荡", "区间", "不涨不跌"]):
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

    target_move = _target_move_from_text(text)
    target_price = None
    if target_move:
        if direction == "bearish":
            target_price = max(1, spot - target_move)
        elif direction == "bullish":
            target_price = spot + target_move

    income_preference = any(word in text for word in ["收权利金", "卖期权", "赚时间价值", "卖方", "不跌破", "不涨破"])
    advanced = any(word in lower for word in ["advanced", "ratio", "short straddle", "short strangle"]) or any(
        word in text for word in ["高级", "比例价差", "裸卖", "双卖"]
    )
    return {
        "asset": "BTC",
        "direction": direction,
        "horizon_days": horizon_days,
        "target_move_usd": target_move,
        "target_price": target_price,
        "capital_usd": _capital_from_text(text),
        "risk_profile": "advanced" if advanced else "beginner",
        "income_preference": income_preference,
        "notes": text or "快捷观点",
    }


def normalize_intent(raw: dict[str, Any], fallback: dict[str, Any], spot: float) -> dict[str, Any]:
    direction = raw.get("direction") if raw.get("direction") in {"bullish", "bearish", "range", "volatile"} else fallback["direction"]
    horizon_days = int(raw.get("horizon_days") or fallback["horizon_days"] or 30)
    target_move = raw.get("target_move_usd")
    target_price = raw.get("target_price")
    if target_price is None and target_move is not None:
        target_price = spot + float(target_move) if direction == "bullish" else spot - float(target_move)
    return {
        "asset": "BTC",
        "direction": direction,
        "horizon_days": max(1, min(horizon_days, 180)),
        "target_move_usd": float(target_move) if target_move is not None else fallback.get("target_move_usd"),
        "target_price": float(target_price) if target_price is not None else fallback.get("target_price"),
        "capital_usd": float(raw.get("capital_usd")) if raw.get("capital_usd") is not None else fallback.get("capital_usd"),
        "risk_profile": raw.get("risk_profile") or fallback.get("risk_profile", "beginner"),
        "income_preference": bool(raw.get("income_preference", fallback.get("income_preference", False))),
        "notes": raw.get("notes") or fallback.get("notes", ""),
    }


async def parse_intent(text: str, quick: dict[str, Any] | None, spot: float, settings: Settings) -> dict[str, Any]:
    fallback = parse_intent_rules(text, quick, spot)
    if not settings.llm_enabled or not text.strip():
        return fallback
    try:
        raw = await chat_json(settings, INTENT_SYSTEM_PROMPT, text)
    except Exception:
        raw = None
    if not raw:
        return fallback
    return normalize_intent(raw, fallback, spot)
