# 冰火岛加密期权策略宝

**Crypto Options Strategy Assistant**

一个本地优先的 BTC / ETH 加密期权策略助手。用户可以用快捷按钮或自然语言表达交易观点，系统会结合 Deribit 的实时现货、期权链、IV、Skew、Gamma、大额成交等公开行情，生成一个具体的期权策略，并配套到期 Payoff 图和 AI 解读。

A local-first BTC / ETH crypto options strategy assistant. Users can express a market view through quick buttons or natural language. The app combines public Deribit market data, including spot, options chain, IV, skew, gamma, and large trade flow, then generates one concrete options strategy with an expiry payoff chart and AI explanation.

> 本项目用于研究和教育，不构成投资建议。不连接交易所交易 API，不自动下单。
>
> This project is for research and education only. It is not financial advice. It does not connect to exchange trading APIs or place orders.

## 主要功能 / Features

- BTC / ETH 标的切换
- 快捷观点：看涨、看跌、看横盘
- 时间范围：未来一周、未来一个月、未来三个月
- 复杂需求输入框：由用户自己的 OpenAI-compatible 大模型解析
- 页面底部“状态”模块可直接配置模型 Base URL、模型名称和 API Key
- 支持测试模型连接，并把配置保存到本地 `.env`
- Deribit 真实期权合约选择
- 单一策略推荐，减少新手选择困难
- 支持资金规模、持仓数量、持仓均价、保护/对冲意图识别
- Payoff 图展示现货价格、盈亏平衡点、目标价和到期盈亏
- AI 解读支持 Markdown 渲染，显示为正常排版
- 页面底部社区打赏模块

English:

- BTC / ETH asset switch
- Quick views: bullish, bearish, range-bound
- Horizons: one week, one month, three months
- Free-form prompt parsed by the user's own OpenAI-compatible LLM
- Built-in model configuration in the bottom status panel
- Test model connectivity and save config to local `.env`
- Concrete Deribit options contract selection
- One recommended strategy to avoid beginner choice overload
- Capital, holding size, average cost, and hedge intent recognition
- Payoff chart with spot, breakevens, target, and expiry PnL
- AI explanation with rendered Markdown
- Community support footer

## 策略池 / Strategy Pool

当前支持：

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
- OpenAI-compatible LLM API

## 快速开始 / Quick Start

```powershell
git clone https://github.com/wepoets1107/crypto-options-strategy-assistant.git
cd crypto-options-strategy-assistant
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

如果 PowerShell 阻止激活脚本，可以使用：

If PowerShell blocks the activation script, use:

```powershell
.\.venv\Scripts\activate.bat
```

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

然后打开：

Then open:

```text
http://127.0.0.1:8010/
```

通用启动命令：

Generic command:

```powershell
python run_server.py
```

## 模型配置 / LLM Configuration

推荐方式：打开页面后，在底部 **状态** 模块里填写：

Recommended: open the app and fill in the bottom **Status** panel:

- Base URL
- 模型名称 / Model name
- API Key

点击 **测试模型** 确认连接正常，再点击 **保存配置**。配置会写入本地 `.env`，保存后立即生效，不需要重启。

Click **Test Model** first, then **Save Config**. The config is saved to local `.env` and takes effect immediately without restarting the server.

也可以手动创建 `.env`：

You can also create `.env` manually:

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

说明：

Notes:

- 支持 OpenAI-compatible API
- 未配置模型时，快捷观点仍可使用
- 复杂需求必须配置模型，系统不会用规则硬猜
- API Key 只保存在本地 `.env`
- `.env` 已被 `.gitignore` 排除，不会进入开源仓库

English:

- Any OpenAI-compatible API can be used
- Quick views still work without an LLM
- Complex prompts require an LLM and are not guessed by rules
- API keys stay in local `.env`
- `.env` is ignored by git and should not be committed

## 工作流 / How It Works

```text
用户观点 / User view
  ↓
LLM 或快捷规则解析结构化意图 / Intent parsing
  ↓
抓取 Deribit 现货和期权链 / Fetch Deribit market data
  ↓
市场研判 / Market judgement
  ↓
策略选择器只选择一个策略 / Strategy selector chooses one strategy
  ↓
选择真实 Deribit 合约 / Pick concrete contracts
  ↓
仓位和资金判断 / Position and capital sizing
  ↓
Payoff 引擎生成收益图 / Payoff engine
  ↓
前端展示策略、合约、风险和 AI 解读 / Frontend display
```

## 项目结构 / Project Structure

```text
app/
  config.py                Local config and .env handling
  main.py                  FastAPI routes
  llm/                     OpenAI-compatible LLM client and prompts
  market_data/             Deribit market data fetchers
  strategy/                Intent, market view, contract picking, payoff, selector
  static/                  HTML, CSS, JavaScript frontend
docs/                      Design notes
examples/                  Example materials
run_server.py              Generic server launcher
start.bat                  Windows foreground launcher
start-background.bat       Windows background launcher
stop.bat                   Stop local server
```

## 安全边界 / Safety Boundary

- 不连接交易所交易 API
- 不自动下单
- 不保存交易所账户权限
- 不请求 Deribit 私有账户信息
- API Key 仅用于用户自己的大模型服务
- API Key 默认只保存在本地 `.env`
- 页面仅回显脱敏后的 key
- 默认只监听 `127.0.0.1:8010`

English:

- No exchange trading API
- No automatic order placement
- No exchange account permissions
- No Deribit private account data
- API keys are only for the user's own LLM provider
- API keys are stored locally in `.env`
- The UI only shows masked keys
- The server listens on `127.0.0.1:8010` by default

## 常见问题 / FAQ

**没有配置模型，还能用吗？**

可以。快捷观点可以直接使用；复杂需求需要先配置大模型。

**Can I use it without an LLM?**

Yes. Quick views work without an LLM. Complex prompts require an LLM.

**会自动交易吗？**

不会。它只做行情分析、策略估算和教育展示。

**Does it trade automatically?**

No. It only analyzes market data and displays educational strategy estimates.

**API Key 会上传到 GitHub 吗？**

不会。`.env` 被 `.gitignore` 排除。请不要手动提交 `.env`。

**Will my API key be uploaded to GitHub?**

No. `.env` is ignored by git. Do not manually commit it.

## License

MIT License. See [LICENSE](LICENSE).
