# Optional validation data

The live scanner score must remain non-price/public-source only.

For later research validation, place a separate CSV here named:

```text
forward_returns.csv
```

Required columns:

```text
date,symbol,score,forward_1d,forward_5d,forward_20d
```

This lets Edgefield test whether raw non-price pressure buckets have forward information value without feeding price data back into the live score.
