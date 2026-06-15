# 中文说明

加密期权策略宝是本地运行的 BTC 期权策略助手。它读取 Deribit 公共数据，结合用户观点和市场状态，只输出一个具体策略，并展示真实合约与 payoff 图。

## 示例

用户输入：

```text
我认为接下来一个月，比特币可能上涨1万美元
```

系统可能输出：

```text
推荐策略：Bull Call Spread
Buy 1 BTC-xx-xxxxx-C
Sell 1 BTC-xx-xxxxx-C
```

具体合约以实时 Deribit 数据为准。
