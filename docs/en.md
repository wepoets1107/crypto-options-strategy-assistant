# English Notes

Crypto Options Strategy Assistant is a local BTC options strategy assistant. It reads Deribit public data, combines the user's view with current market structure, recommends one concrete strategy, and displays real contracts plus a payoff chart.

## Example

Input:

```text
I think BTC may rise by $10,000 in the next month.
```

Possible output:

```text
Recommended strategy: Bull Call Spread
Buy 1 BTC-xx-xxxxx-C
Sell 1 BTC-xx-xxxxx-C
```

Actual contracts are selected from live Deribit data.
