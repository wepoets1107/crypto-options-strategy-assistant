# 加密期权策略宝 / Crypto Options Strategy Assistant

一个本地优先的 BTC 期权策略助手。用户可以用快捷按钮或自然语言表达观点，系统会结合 Deribit 实时现货、期权链、IV、Skew、Gamma 和大额成交数据，生成一个具体的 Deribit 期权策略，并配套 payoff 图。

A local-first BTC options strategy assistant. Users can express a view through quick buttons or natural language. The app combines real-time Deribit spot and options data, IV, skew, gamma, and large trade flow to generate one concrete Deribit options strategy with a payoff chart.

> 本项目用于研究和教育，不构成投资建议。不接交易 API，不自动下单。
>
> This project is for research and education only. It is not financial advice. It does not connect to trading APIs or place orders.

## 功能 / Features

- BTC-only MVP
- 快捷输入：看涨、看跌、看横盘
- 时间范围：未来一周、未来一个月、未来三个月
- 复杂输入框：支持用户输入更细的观点和目标价
- 手动生成策略
- 可选 5 分钟自动更新
- 用户自带 OpenAI-compatible LLM
- 无 LLM 时自动使用规则解析
- Deribit 真实期权合约选择
- 唯一策略推荐，避免新手选择困难
- Payoff 图展示收益和风险
- 页面底部打赏支持模块

English:

- BTC-only MVP
- Quick input: bullish, bearish, range-bound
- Horizon: one week, one month, three months
- Free-form input for complex views and target prices
- Manual strategy generation
- Optional 5-minute auto refresh
- User-provided OpenAI-compatible LLM
- Rule-based fallback when no LLM is configured
- Concrete Deribit contract selection
- One recommended strategy to avoid beginner choice overload
- Payoff chart
- Community support footer

## 策略池 / Strategy Pool

当前策略引擎支持：

Currently supported:

- Long Call
- Long Put
- Bull Call Spread
- Bull Put Spread
- Bear Call Spread
- Bear Put Spread
- Long Straddle
- Long Strangle
- Short Strangle
- Iron Butterfly
- Iron Condor
- Call Ratio Spread
- Put Ratio Spread

高级卖方或比例策略会附加强风险提示。

Advanced short-volatility or ratio strategies include stronger risk warnings.

## 技术栈 / Tech Stack

- Python 3.11+
- FastAPI
- Uvicorn
- httpx
- Static HTML / CSS / Vanilla JavaScript
- SVG payoff chart

## 安装 / Installation

```powershell
git clone https://github.com/wepoets1107/crypto-options-strategy-assistant.git
cd crypto-options-strategy-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 阻止激活脚本，可以用：

If PowerShell blocks the activation script, use:

```powershell
.\.venv\Scripts\activate.bat
```

## LLM 配置 / LLM Configuration

复制 `.env.example` 为 `.env`：

Copy `.env.example` to `.env`:

```powershell
copy .env.example .env
```

填写：

Fill in:

```text
LLM_BASE_URL=https://api.example.com/v1
LLM_API_KEY=your_api_key_here
LLM_MODEL=your_model_name
```

支持 OpenAI-compatible API。没有配置时，系统会使用规则解析和模板解释。

Any OpenAI-compatible API can be used. Without LLM configuration, the app falls back to rule-based parsing and template explanations.

## 启动 / Run

Windows 前台启动：

Windows foreground:

```powershell
.\start.bat
```

Windows 后台启动：

Windows background:

```powershell
.\start-background.bat
```

停止服务：

Stop:

```powershell
.\stop.bat
```

浏览器打开：

Open:

```text
http://127.0.0.1:8010/
```

通用启动命令：

Generic command:

```powershell
python run_server.py
```

## 运行逻辑 / How It Works

```text
用户观点
  ↓
LLM或规则解析成结构化意图
  ↓
抓取 Deribit BTC 现货和期权链
  ↓
Market Judgement Engine 综合研判
  ↓
Strategy Selector 只选择一个策略
  ↓
Contract Picker 选择真实 Deribit 合约
  ↓
Payoff Engine 生成收益图数据
  ↓
前端展示策略、合约、风险和 payoff 图
```

English:

```text
User view
  ↓
LLM or rule-based intent parsing
  ↓
Fetch Deribit BTC spot and options chain
  ↓
Market Judgement Engine
  ↓
Strategy Selector chooses one strategy
  ↓
Contract Picker picks real Deribit contracts
  ↓
Payoff Engine generates payoff data
  ↓
Frontend displays strategy, contracts, risks, and payoff chart
```

## 安全边界 / Safety Boundary

- 不接交易 API
- 不自动下单
- 不保存交易所账户权限
- LLM Key 只放在本地 `.env`
- `.env` 被 `.gitignore` 排除
- 默认只监听 `127.0.0.1:8010`

English:

- No trading API
- No automatic order placement
- No exchange account permissions
- LLM key stays in local `.env`
- `.env` is ignored by git
- Listens on `127.0.0.1:8010` by default

## License

MIT License. See [LICENSE](LICENSE).
