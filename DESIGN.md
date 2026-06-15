# 设计说明 / Design Notes

## 定位 / Positioning

加密期权策略宝不是一个模板化“看涨就买 Call”的工具，而是一个市场校验器和策略翻译器。

Crypto Options Strategy Assistant is not a template tool that simply maps bullish views to calls. It is a market validator and strategy translator.

## 核心原则 / Core Principles

- 面向新手，只输出一个推荐策略
- 具体到 Deribit 真实合约
- 每个策略必须有 payoff 图
- AI 不创造合约名
- AI 负责理解和解释，策略选择必须基于行情数据和规则
- 不接交易 API，不自动下单

English:

- Beginner-oriented: recommend one strategy only
- Use concrete Deribit contracts
- Every strategy must include a payoff chart
- AI must not invent contract names
- AI handles understanding and explanation; market data and rules drive selection
- No trading API and no order placement

## 模块 / Modules

```text
app/main.py                 FastAPI entrypoint
app/config.py               Local config and .env loading
app/market_data/deribit.py  Deribit public data fetching and option enrichment
app/llm/client.py           OpenAI-compatible LLM client
app/strategy/intent.py      User view parsing
app/strategy/market_view.py Market Judgement Engine
app/strategy/selector.py    Strategy selection and orchestration
app/strategy/contracts.py   Real contract picking
app/strategy/payoff.py      Payoff points and metrics
app/static/                 Browser UI
```

## 输入模式 / Input Modes

1. 快捷输入：
   - 看涨
   - 看跌
   - 看横盘
   - 未来一周 / 一个月 / 三个月

2. 复杂输入：
   - 用户可以输入自然语言，例如“我认为接下来一个月，比特币可能上涨1万美元”

English:

1. Quick input:
   - Bullish
   - Bearish
   - Range-bound
   - One week / one month / three months

2. Free-form input:
   - Natural language views such as “I think BTC may rise by $10,000 in the next month”

## Market Judgement Engine

市场研判会综合：

- BTC spot
- selected expiry
- ATM IV
- 25D skew
- Put/Call OI
- 30D gamma concentration
- 24h large option trades
- user target vs implied move

It combines:

- BTC spot
- selected expiry
- ATM IV
- 25D skew
- Put/Call OI
- 30D gamma concentration
- 24h large option trades
- user target vs implied move

## 策略选择 / Strategy Selection

示例规则：

Example rules:

- Bullish + target + expensive/normal IV -> Bull Call Spread
- Bullish + income preference -> Bull Put Spread
- Bearish + target + expensive/normal IV -> Bear Put Spread
- Bearish + income preference -> Bear Call Spread
- Range-bound + expensive IV -> Iron Condor
- Volatile + cheap IV -> Long Straddle
- Volatile + normal/expensive IV -> Long Strangle

## 合约选择 / Contract Picking

- 到期日优先选择不早于用户时间范围的最近 expiry，确保策略覆盖用户观点周期
- ATM 腿选择接近 spot 的真实合约
- 目标腿选择接近 target price 的真实合约
- Delta 腿选择接近目标 delta 的真实合约
- 买入腿优先使用 ask
- 卖出腿优先使用 bid
- bid/ask 缺失时使用 mark 并标记为估算

English:

- Prefer the nearest live expiry that is not earlier than the user's horizon, so the strategy covers the user's view window
- ATM legs use real contracts closest to spot
- Target legs use real contracts closest to target price
- Delta legs use real contracts closest to target delta
- Buy legs prefer ask
- Sell legs prefer bid
- Fall back to mark when bid/ask is missing

## Payoff

Payoff 使用到期盈亏估算，单位 USD。Deribit BTC 期权价格以 BTC 计价，前端展示时用当前 spot 转换为 USD 估算。

Payoff is estimated at expiry in USD. Deribit BTC option prices are BTC-denominated; the UI converts premiums to USD using current spot for readability.
