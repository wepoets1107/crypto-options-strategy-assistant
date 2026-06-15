const $ = (id) => document.getElementById(id);

let currentDirection = "bullish";
let currentDays = 30;
let lastPayload = null;

function fmt(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  return Number(value).toLocaleString("en-US", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

function money(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "--";
  const sign = Number(value) > 0 ? "+" : Number(value) < 0 ? "-" : "";
  return `${sign}$${fmt(Math.abs(Number(value)), 0)}`;
}

function setLog(message) {
  $("log").textContent = message;
}

function activeButton(group, attr) {
  return [...group.querySelectorAll("button")].find((button) => button.classList.contains("active"))?.dataset[attr];
}

function setupSegments() {
  $("directionGroup").addEventListener("click", (event) => {
    if (!(event.target instanceof HTMLButtonElement)) return;
    $("directionGroup").querySelectorAll("button").forEach((button) => button.classList.toggle("active", button === event.target));
    currentDirection = event.target.dataset.direction;
  });
  $("horizonGroup").addEventListener("click", (event) => {
    if (!(event.target instanceof HTMLButtonElement)) return;
    $("horizonGroup").querySelectorAll("button").forEach((button) => button.classList.toggle("active", button === event.target));
    currentDays = Number(event.target.dataset.days || 30);
  });
}

function quickText() {
  const directionMap = { bullish: "看涨", bearish: "看跌", range: "看横盘" };
  const horizonMap = { 7: "未来一周", 30: "未来一个月", 90: "未来三个月" };
  return `我${directionMap[currentDirection]}比特币，时间范围是${horizonMap[currentDays] || "未来一个月"}。`;
}

async function generate(useQuick = false, silent = false) {
  const text = useQuick ? quickText() : $("promptInput").value.trim();
  const payload = {
    text,
    quick: useQuick ? { direction: currentDirection, horizon_days: currentDays } : null,
  };
  lastPayload = payload;
  if (!silent) setLog("正在连接 Deribit 并生成策略...");
  $("generateBtn").disabled = true;
  $("quickBtn").disabled = true;
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    render(data);
    setLog(`${silent ? "默认策略已生成" : "策略已生成"}：${data.strategy.strategy_name}`);
  } catch (error) {
    setLog(`生成失败：${error.message}`);
  } finally {
    $("generateBtn").disabled = false;
    $("quickBtn").disabled = false;
  }
}

async function rerunLast() {
  if (!lastPayload) {
    await generate(true, true);
    return;
  }
  $("generateBtn").disabled = true;
  $("quickBtn").disabled = true;
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(lastPayload),
    });
    if (!response.ok) throw new Error(await response.text());
    render(await response.json());
    setLog("5分钟自动更新完成。");
  } catch (error) {
    setLog(`自动更新失败：${error.message}`);
  } finally {
    $("generateBtn").disabled = false;
    $("quickBtn").disabled = false;
  }
}

async function refreshSpot() {
  try {
    const response = await fetch("/api/spot");
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    $("spot").textContent = `BTC $${fmt(data.spot, 0)}`;
    if (!$("updatedAt").textContent || $("updatedAt").textContent === "尚未生成") {
      $("updatedAt").textContent = new Date(data.updated_at).toLocaleString();
    }
  } catch (error) {
    $("spot").textContent = "BTC --";
  }
}

function render(data) {
  $("spot").textContent = `BTC $${fmt(data.market_meta.spot, 0)}`;
  $("updatedAt").textContent = new Date(data.market_meta.updated_at).toLocaleString();
  $("llmBadge").textContent = data.market_meta.llm_enabled ? "LLM解析" : "规则解析";
  renderIntent(data.intent);
  renderMarket(data.market_view);
  renderStrategy(data.strategy);
  $("explanation").textContent = data.explanation;
  $("riskList").innerHTML = data.strategy.risk_notes.map((note) => `<li>${note}</li>`).join("");
}

function renderIntent(intent) {
  const labels = {
    bullish: "看涨",
    bearish: "看跌",
    range: "横盘/区间",
    volatile: "大波动",
    unknown: "未识别",
  };
  const riskLabels = { beginner: "新手", advanced: "高级" };
  const rangeText = intent.target_range?.lower && intent.target_range?.upper
    ? `$${fmt(intent.target_range.lower, 0)} - $${fmt(intent.target_range.upper, 0)}`
    : "--";
  $("intentBox").innerHTML = [
    ["标的", intent.asset],
    ["方向", labels[intent.direction] || intent.direction],
    ["时间范围", `${intent.horizon_days} 天`],
    ["目标价", intent.target_price ? `$${fmt(intent.target_price, 0)}` : "--"],
    ["目标区间", rangeText],
    ["目标涨跌", intent.target_move_usd ? `$${fmt(intent.target_move_usd, 0)}` : "--"],
    ["资金规模", intent.capital_usd ? `$${fmt(intent.capital_usd, 0)}` : "--"],
    ["风险偏好", riskLabels[intent.risk_profile] || intent.risk_profile],
  ]
    .map(([key, value]) => `<div><span>${key}</span><strong>${value}</strong></div>`)
    .join("");
}

function renderMarket(view) {
  $("confidence").textContent = `支持度 ${Math.round(view.direction_confidence * 100)}%`;
  const features = view.features;
  const rows = [
    `选择到期：${features.selected_expiry_label}，约 ${fmt(features.selected_expiry_days, 1)} 天`,
    `ATM IV：${features.atm_iv ? fmt(features.atm_iv, 1) + "%" : "--"}；25D Skew：${features.skew_25d ? fmt(features.skew_25d, 2) : "--"}`,
    `波动率判断：${view.volatility_view}；大额成交：${view.trade_flow_view}`,
    `<span class="brief-title">判断依据</span>`,
    ...(view.diagnostics || view.reasons || []),
  ];
  $("marketBox").innerHTML = rows.map((row) => `<div>${row}</div>`).join("");
}

function renderStrategy(strategy) {
  $("strategyName").textContent = `策略建议：${strategy.strategy_name}`;
  $("strategyMeta").textContent = `${strategy.asset} · ${strategy.expiry_label}`;
  $("legsTable").innerHTML = [
    `<div class="leg-row header"><span>方向</span><span>合约</span><span>数量</span><span>行权价</span><span>价格</span><span>IV</span><span>Delta</span></div>`,
    ...strategy.legs.map((leg) => {
      const badge = leg.side === "buy" ? "badge-buy" : "badge-sell";
      return `<div class="leg-row">
        <span class="${badge}">${leg.side.toUpperCase()}</span>
        <strong>${leg.instrument_name}</strong>
        <span>${leg.quantity}</span>
        <span>$${fmt(leg.strike, 0)}</span>
        <span>${fmt(leg.price_btc, 4)} BTC · ${leg.price_source}</span>
        <span>${fmt(leg.iv, 1)}%</span>
        <span>${fmt(leg.delta, 2)}</span>
      </div>`;
    }),
  ].join("");
  const payoff = strategy.payoff;
  $("metrics").innerHTML = [
    ["净权利金", `${money(strategy.premium.net_premium_usd)} · ${strategy.premium.net_premium_type}`],
    ["估算最大亏损", money(payoff.estimated_min_pnl_usd)],
    ["估算最大收益", money(payoff.estimated_max_pnl_usd)],
    ["目标价收益", payoff.target_pnl_usd === null ? "--" : money(payoff.target_pnl_usd)],
    ["资金判断", strategy.position_sizing?.message || "--"],
  ]
    .map(([key, value]) => `<article><span>${key}</span><strong>${value}</strong></article>`)
    .join("");
  renderPayoff(payoff);
}

function renderPayoff(payoff) {
  const points = payoff.points || [];
  if (!points.length) {
    $("payoffChart").innerHTML = "";
    return;
  }
  const width = 760;
  const height = 330;
  const pad = { left: 68, right: 24, top: 22, bottom: 58 };
  const minX = Math.min(...points.map((p) => p.price));
  const maxX = Math.max(...points.map((p) => p.price));
  const minY = Math.min(...points.map((p) => p.pnl), 0);
  const maxY = Math.max(...points.map((p) => p.pnl), 0);
  const x = (value) => pad.left + ((value - minX) / (maxX - minX || 1)) * (width - pad.left - pad.right);
  const y = (value) => height - pad.bottom - ((value - minY) / (maxY - minY || 1)) * (height - pad.top - pad.bottom);
  const path = points.map((p, i) => `${i ? "L" : "M"} ${x(p.price).toFixed(1)} ${y(p.pnl).toFixed(1)}`).join(" ");
  const zeroY = y(0);
  const spotX = x(payoff.markers.spot);
  const targetX = payoff.markers.target ? x(payoff.markers.target) : null;
  const bePrices = payoff.markers.breakevens || [];
  const breakevens = bePrices
    .map((price, index) => {
      const labelY = height - (index % 2 === 0 ? 28 : 12);
      return `<line class="marker-breakeven" x1="${x(price)}" y1="${pad.top}" x2="${x(price)}" y2="${height - pad.bottom}" />
        <circle cx="${x(price)}" cy="${zeroY}" r="4" fill="#17202a"><title>Breakeven ${fmt(price, 0)}</title></circle>
        <text class="chart-text strong" x="${x(price) + 5}" y="${labelY}">BE $${fmt(price, 0)}</text>`;
    })
    .join("");
  $("payoffChart").innerHTML = `<svg class="payoff-svg" viewBox="0 0 ${width} ${height}" role="img" aria-label="Payoff chart">
    <line class="grid-line" x1="${pad.left}" y1="${pad.top}" x2="${pad.left}" y2="${height - pad.bottom}" />
    <line class="grid-line" x1="${pad.left}" y1="${height - pad.bottom}" x2="${width - pad.right}" y2="${height - pad.bottom}" />
    <line class="zero-line" x1="${pad.left}" y1="${zeroY}" x2="${width - pad.right}" y2="${zeroY}" />
    <path class="payoff-line" d="${path}" />
    <line class="marker-spot" x1="${spotX}" y1="${pad.top}" x2="${spotX}" y2="${height - pad.bottom}" />
    ${targetX ? `<line class="marker-target" x1="${targetX}" y1="${pad.top}" x2="${targetX}" y2="${height - pad.bottom}" />` : ""}
    ${breakevens}
    <text class="chart-text" x="${pad.left}" y="${height - 12}">$${fmt(minX, 0)}</text>
    <text class="chart-text" x="${width - pad.right - 68}" y="${height - 12}">$${fmt(maxX, 0)}</text>
    <text class="chart-text strong" x="${spotX + 4}" y="30">Spot $${fmt(payoff.markers.spot, 0)}</text>
    <text class="chart-text strong" x="${spotX + 4}" y="${height - 42}">Spot</text>
    ${targetX ? `<text class="chart-text strong" x="${targetX + 4}" y="48">Target $${fmt(payoff.markers.target, 0)}</text>
    <text class="chart-text strong" x="${targetX + 4}" y="${height - 42}">Target</text>` : ""}
    <text class="chart-text" x="8" y="${y(maxY) + 4}">${money(maxY)}</text>
    <text class="chart-text strong" x="8" y="${zeroY - 6}">$0</text>
    <text class="chart-text" x="8" y="${y(minY) + 4}">${money(minY)}</text>
  </svg>`;
}

setupSegments();
$("quickBtn").addEventListener("click", () => generate(true));
$("generateBtn").addEventListener("click", () => generate(false));

refreshSpot();
generate(true, true);
window.setInterval(refreshSpot, 60 * 1000);
