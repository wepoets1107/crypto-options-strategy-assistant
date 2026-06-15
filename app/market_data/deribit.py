from __future__ import annotations

import asyncio
import math
import time
from collections import defaultdict
from datetime import UTC, datetime
from typing import Any

import httpx


DERIBIT_API = "https://www.deribit.com/api/v2"
SUPPORTED_CURRENCIES = {"BTC": "btc_usd"}


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        output = float(value)
        if math.isnan(output) or math.isinf(output):
            return default
        return output
    except (TypeError, ValueError):
        return default


def normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def bs_delta(spot: float, strike: float, years: float, vol: float, option_type: str) -> float:
    if spot <= 0 or strike <= 0 or years <= 0 or vol <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + 0.5 * vol * vol * years) / (vol * math.sqrt(years))
    if option_type == "call":
        return normal_cdf(d1)
    return normal_cdf(d1) - 1.0


def bs_gamma(spot: float, strike: float, years: float, vol: float) -> float:
    if spot <= 0 or strike <= 0 or years <= 0 or vol <= 0:
        return 0.0
    d1 = (math.log(spot / strike) + 0.5 * vol * vol * years) / (vol * math.sqrt(years))
    pdf = math.exp(-0.5 * d1 * d1) / math.sqrt(2 * math.pi)
    return pdf / (spot * vol * math.sqrt(years))


async def deribit_public(client: httpx.AsyncClient, method: str, params: dict[str, Any] | None = None) -> Any:
    response = await client.get(f"{DERIBIT_API}/public/{method}", params=params or {})
    response.raise_for_status()
    payload = response.json()
    if "error" in payload:
        raise RuntimeError(payload["error"])
    return payload.get("result")


def expiry_label(expiry_iso: str) -> str:
    expiry = datetime.fromisoformat(expiry_iso)
    return expiry.strftime("%d%b%y").upper()


def instrument_meta(instruments: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    meta = {}
    for item in instruments:
        name = item.get("instrument_name")
        if not name:
            continue
        expiry_ts = safe_float(item.get("expiration_timestamp")) / 1000
        expiry = datetime.fromtimestamp(expiry_ts, UTC) if expiry_ts else None
        meta[name] = {
            "instrument_name": name,
            "strike": safe_float(item.get("strike")),
            "option_type": "call" if item.get("option_type") == "call" else "put",
            "expiry": expiry,
        }
    return meta


def enrich_options(summaries: list[dict[str, Any]], meta: dict[str, dict[str, Any]], spot: float) -> list[dict[str, Any]]:
    now = datetime.now(UTC)
    rows = []
    for item in summaries:
        name = item.get("instrument_name")
        info = meta.get(name or "")
        expiry = info.get("expiry") if info else None
        if not info or not expiry:
            continue
        days = (expiry - now).total_seconds() / 86400
        if days <= 0:
            continue
        strike = safe_float(info["strike"])
        option_type = info["option_type"]
        iv = safe_float(item.get("mark_iv")) / 100
        years = max(days / 365.0, 1 / 365 / 24)
        delta = bs_delta(spot, strike, years, iv, option_type)
        gamma = bs_gamma(spot, strike, years, iv)
        bid = safe_float(item.get("bid_price"))
        ask = safe_float(item.get("ask_price"))
        mark = safe_float(item.get("mark_price"))
        rows.append(
            {
                "instrument_name": name,
                "strike": strike,
                "expiry": expiry.isoformat(timespec="seconds"),
                "expiry_label": expiry.strftime("%d%b%y").upper(),
                "days": days,
                "option_type": option_type,
                "bid": bid,
                "ask": ask,
                "mark": mark,
                "iv": iv * 100,
                "delta": delta,
                "gamma": gamma,
                "open_interest": safe_float(item.get("open_interest")),
                "volume": safe_float(item.get("volume")),
            }
        )
    return rows


def by_expiry(options: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in options:
        grouped[row["expiry"]].append(row)
    return dict(grouped)


def closest_expiry(options: list[dict[str, Any]], horizon_days: int) -> str:
    grouped = by_expiry(options)
    if not grouped:
        raise RuntimeError("No live BTC options were returned by Deribit.")
    candidates = []
    for expiry, rows in grouped.items():
        days = min(row["days"] for row in rows)
        oi = sum(row["open_interest"] for row in rows)
        candidates.append((abs(days - horizon_days), -oi, expiry))
    candidates.sort()
    return candidates[0][2]


def atm_iv(options: list[dict[str, Any]], spot: float, expiry: str) -> float | None:
    rows = [row for row in options if row["expiry"] == expiry and row["iv"] > 0]
    if not rows:
        return None
    picked = min(rows, key=lambda row: abs(row["strike"] - spot))
    return picked["iv"]


def closest_delta_iv(rows: list[dict[str, Any]], option_type: str, target_delta: float) -> float | None:
    side_rows = [row for row in rows if row["option_type"] == option_type and row["iv"] > 0]
    if not side_rows:
        return None
    picked = min(side_rows, key=lambda row: abs(row["delta"] - target_delta))
    return picked["iv"]


def market_features(options: list[dict[str, Any]], spot: float, horizon_days: int) -> dict[str, Any]:
    expiry = closest_expiry(options, horizon_days)
    expiry_rows = [row for row in options if row["expiry"] == expiry]
    atm = atm_iv(options, spot, expiry)
    call25 = closest_delta_iv(expiry_rows, "call", 0.25)
    put25 = closest_delta_iv(expiry_rows, "put", -0.25)
    skew25 = call25 - put25 if call25 is not None and put25 is not None else None
    call_oi = sum(row["open_interest"] for row in options if row["option_type"] == "call")
    put_oi = sum(row["open_interest"] for row in options if row["option_type"] == "put")
    gamma_buckets: dict[float, float] = defaultdict(float)
    for row in options:
        if row["days"] > 30:
            continue
        gross = row["gamma"] * row["open_interest"] * spot * spot / 100
        gamma_buckets[row["strike"]] += gross if row["option_type"] == "call" else -gross
    max_gamma = None
    if gamma_buckets:
        strike, value = max(gamma_buckets.items(), key=lambda item: abs(item[1]))
        max_gamma = {"strike": strike, "value": value}
    return {
        "selected_expiry": expiry,
        "selected_expiry_label": expiry_label(expiry),
        "selected_expiry_days": min(row["days"] for row in expiry_rows),
        "atm_iv": atm,
        "skew_25d": skew25,
        "put_call_oi": put_oi / call_oi if call_oi else None,
        "max_gamma": max_gamma,
    }


async def fetch_recent_trades(client: httpx.AsyncClient, currency: str = "BTC") -> dict[str, Any]:
    end_timestamp = int(time.time() * 1000)
    start_timestamp = end_timestamp - 24 * 60 * 60 * 1000
    return await deribit_public(
        client,
        "get_last_trades_by_currency_and_time",
        {
            "currency": currency,
            "kind": "option",
            "start_timestamp": start_timestamp,
            "end_timestamp": end_timestamp,
            "count": "1000",
        },
    )


def trade_bias(trades: list[dict[str, Any]]) -> dict[str, Any]:
    calls = 0.0
    puts = 0.0
    large = []
    for trade in trades:
        name = str(trade.get("instrument_name") or "")
        amount = safe_float(trade.get("amount"))
        if amount < 100:
            continue
        if name.endswith("-C"):
            calls += amount
        elif name.endswith("-P"):
            puts += amount
        large.append(
            {
                "instrument_name": name,
                "direction": trade.get("direction", "unknown"),
                "amount": amount,
                "price": safe_float(trade.get("price")),
            }
        )
    bias = "balanced"
    if calls > puts * 1.3:
        bias = "call_heavy"
    elif puts > calls * 1.3:
        bias = "put_heavy"
    return {"bias": bias, "large_call_amount": calls, "large_put_amount": puts, "large_trades": large[:12]}


async def fetch_btc_market() -> dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        index_task = deribit_public(client, "get_index_price", {"index_name": SUPPORTED_CURRENCIES["BTC"]})
        instruments_task = deribit_public(client, "get_instruments", {"currency": "BTC", "kind": "option", "expired": "false"})
        summaries_task = deribit_public(client, "get_book_summary_by_currency", {"currency": "BTC", "kind": "option"})
        trades_task = fetch_recent_trades(client, "BTC")
        index, instruments, summaries, trades = await asyncio.gather(
            index_task,
            instruments_task,
            summaries_task,
            trades_task,
        )
    spot = safe_float(index.get("index_price"))
    options = enrich_options(summaries, instrument_meta(instruments), spot)
    return {
        "currency": "BTC",
        "spot": spot,
        "options": options,
        "trade_bias": trade_bias(trades.get("trades", []) if isinstance(trades, dict) else []),
        "updated_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
