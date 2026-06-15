from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import STATIC_DIR, get_settings
from app.llm.client import chat_text
from app.llm.prompts import EXPLANATION_SYSTEM_PROMPT
from app.market_data.deribit import fetch_btc_market
from app.strategy.intent import parse_intent
from app.strategy.market_view import build_market_view
from app.strategy.selector import select_strategy


app = FastAPI(title="Crypto Options Strategy Assistant")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class GenerateRequest(BaseModel):
    text: str = ""
    quick: dict[str, Any] | None = None


def fallback_explanation(intent: dict[str, Any], market_view: dict[str, Any], strategy: dict[str, Any]) -> str:
    def usd(value: Any) -> str:
        if value is None:
            return "--"
        return f"${float(value):,.0f}"

    name = strategy["strategy_name"]
    alignment = {
        "supports": "当前数据比较支持你的想法",
        "partially_supports": "当前数据只部分支持你的想法",
        "does_not_support": "当前数据并不太支持你的想法",
    }.get(market_view["alignment"], "当前市场信号比较均衡")
    reasons = [str(item).rstrip("。.!！；; ") for item in market_view.get("reasons", []) if item]
    reason = "；".join(reasons) or "市场信号比较均衡，还没有出现特别强的一边倒证据"
    premium = strategy.get("premium", {})
    payoff = strategy.get("payoff", {})
    net_type = "收取权利金" if premium.get("net_premium_type") == "credit" else "支付权利金"
    max_loss = payoff.get("estimated_min_pnl_usd")
    max_profit = payoff.get("estimated_max_pnl_usd")
    target_pnl = payoff.get("target_pnl_usd")
    be = payoff.get("markers", {}).get("breakevens", [])
    be_text = "、".join(f"${price:,.0f}" for price in be) if be else "暂无明确盈亏平衡点"
    target_text = f"如果到期价格接近你的目标价，估算盈亏约为 ${target_pnl:,.0f}。" if target_pnl is not None else "你没有给出明确目标价，所以这里主要看区间和盈亏平衡点。"
    sizing = strategy.get("position_sizing") or {}
    sizing_text = sizing.get("message", "")

    paragraphs = [
        f"简单说：{alignment}，所以我没有给你一个特别激进的方案，而是选择了 {name}。\n\n"
        f"为什么这么选：{reason}。对新手来说，先把“最多可能亏多少、价格走到哪里开始赚钱”看清楚，比单纯猜方向更重要。",
    ]
    if sizing_text:
        paragraphs.append(f"仓位上：{sizing_text}")
    paragraphs.extend(
        [
        f"这组策略现在大致是{net_type}。按当前 Deribit bid/ask/mark 估算，图上的区间里最大亏损约为 {usd(abs(max_loss) if max_loss is not None else None)}，最大收益约为 {usd(max_profit)}，盈亏平衡点大约在 {be_text}。{target_text}\n\n"
        "需要注意：这只是基于当前公开行情的教育型估算，不是投资建议；策略本身仍然可能亏钱。"
        ]
    )
    return "\n\n".join(paragraphs)


async def explain(settings, intent: dict[str, Any], market_view: dict[str, Any], strategy: dict[str, Any]) -> str:
    payload = {"intent": intent, "market_view": market_view, "strategy": strategy}
    try:
        text = await chat_text(settings, EXPLANATION_SYSTEM_PROMPT, str(payload))
    except Exception:
        text = None
    return text or fallback_explanation(intent, market_view, strategy)


@app.middleware("http")
async def no_store_assets(request, call_next):
    response = await call_next(request)
    if request.url.path == "/" or request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.get("/")
async def index_page() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health() -> JSONResponse:
    return JSONResponse({"ok": True, "service": "Crypto Options Strategy Assistant"})


@app.post("/api/generate")
async def generate_strategy(request: GenerateRequest) -> JSONResponse:
    settings = get_settings()
    market = await fetch_btc_market()
    intent = await parse_intent(request.text, request.quick, float(market["spot"]), settings)
    market_view = build_market_view(market, intent)
    strategy = select_strategy(market, intent, market_view)
    explanation = await explain(settings, intent, market_view, strategy)
    return JSONResponse(
        {
            "intent": intent,
            "market_view": market_view,
            "strategy": strategy,
            "explanation": explanation,
            "market_meta": {
                "currency": "BTC",
                "spot": market["spot"],
                "option_count": len(market["options"]),
                "updated_at": market["updated_at"],
                "llm_enabled": settings.llm_enabled,
            },
        }
    )
