from __future__ import annotations

from typing import Any


def option_rows(options: list[dict[str, Any]], expiry: str, option_type: str) -> list[dict[str, Any]]:
    return sorted(
        [row for row in options if row["expiry"] == expiry and row["option_type"] == option_type],
        key=lambda row: row["strike"],
    )


def liquidity_score(row: dict[str, Any], side: str) -> float:
    price = row.get("ask") if side == "buy" else row.get("bid")
    spread = 0.0
    bid = float(row.get("bid") or 0)
    ask = float(row.get("ask") or 0)
    if bid > 0 and ask > 0:
        mid = (bid + ask) / 2
        spread = (ask - bid) / mid if mid else 9
    penalty = spread * 100
    tradable = 25 if price and price > 0 else 0
    return float(row.get("open_interest") or 0) * 0.02 + float(row.get("volume") or 0) + tradable - penalty


def pick_by_strike(rows: list[dict[str, Any]], target: float, side: str, minimum: float | None = None, maximum: float | None = None) -> dict[str, Any]:
    candidates = rows
    if minimum is not None:
        candidates = [row for row in candidates if row["strike"] >= minimum]
    if maximum is not None:
        candidates = [row for row in candidates if row["strike"] <= maximum]
    if not candidates:
        raise RuntimeError("No matching Deribit contract found for the requested strike.")
    return min(candidates, key=lambda row: (abs(row["strike"] - target), -liquidity_score(row, side)))


def pick_by_delta(rows: list[dict[str, Any]], target_delta: float, side: str) -> dict[str, Any]:
    if not rows:
        raise RuntimeError("No matching Deribit contract found for the requested delta.")
    return min(rows, key=lambda row: (abs(row["delta"] - target_delta), -liquidity_score(row, side)))


def leg(row: dict[str, Any], side: str, quantity: float = 1) -> dict[str, Any]:
    preferred = row.get("ask") if side == "buy" else row.get("bid")
    price_source = "ask" if side == "buy" else "bid"
    if not preferred or preferred <= 0:
        preferred = row.get("mark") or 0
        price_source = "mark"
    return {
        "side": side,
        "quantity": quantity,
        "instrument_name": row["instrument_name"],
        "currency": row.get("currency") or str(row["instrument_name"]).split("-", 1)[0],
        "option_type": row["option_type"],
        "strike": row["strike"],
        "expiry": row["expiry"],
        "expiry_label": row["expiry_label"],
        "price_coin": preferred,
        "price_btc": preferred,
        "price_source": price_source,
        "bid": row.get("bid"),
        "ask": row.get("ask"),
        "mark": row.get("mark"),
        "iv": row.get("iv"),
        "delta": row.get("delta"),
        "open_interest": row.get("open_interest"),
        "volume": row.get("volume"),
    }
