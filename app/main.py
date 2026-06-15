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
    name = strategy["strategy_name"]
    alignment = {
        "supports": "当前市场数据较支持你的观点",
        "partially_supports": "当前市场数据只部分支持你的观点",
        "does_not_support": "当前市场数据并不强烈支持你的观点",
    }.get(market_view["alignment"], "当前市场信号较均衡")
    reason = "；".join(market_view["reasons"])
    return (
        f"{alignment}。系统选择 {name}，因为它能把风险收益结构固定下来，适合先看清最大亏损再做判断。"
        f"市场依据：{reason}。请注意，这只是基于 Deribit 当前公开行情的教育型估算，不构成投资建议。"
    )


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
