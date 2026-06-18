# Rolling Forecast Report

**Generated:** 2026-06-18  
**Reference:** Cerqueti et al. (2024) — vanilla autoencoder factor-augmented AR(1)  
**Script:** `python scripts/run_forecasts.py`

---

## Setup

| Item | Value |
|---|---|
| **Commodities** | 27 (merged 2013+ universe) |
| **Sample** | 2013-10-21 → 2026-06-01 (2,870 trading days) |
| **Estimation window M** | 1,260 days (~5 years) |
| **OOS forecasts** | 1,610 windows (first forecast ~2018-10) |
| **Models compared** | AR(1) baseline vs. vanilla AE factor-augmented AR(1) |
| **Latent factors K** | 5 |
| **Forecast lag p** | 1 |

### Per-window procedure
1. Take returns in window [d−M, …, d−1]; z-score inside the window (no look-ahead).
2. Train vanilla autoencoder; extract latent factors f_t.
3. Fit AR(1) and factor-augmented AR(1) per commodity on the window.
4. One-step-ahead forecast for date d; roll forward.

---

## Overall results

| Model | Pooled MSE | Pooled MAE | RMSE |
|---|---|---|---|
| **AR(1)** | **6.002×10⁻⁴** | 0.01491 | 0.02450 |
| Vanilla AE + AR(1) | 6.010×10⁻⁴ | 0.01498 | 0.02452 |
| **Δ (AE − AR1)** | +0.14% worse | +0.48% worse | +0.08% worse |

The AE-augmented model **does not beat** the AR(1) baseline on pooled one-step daily forecast accuracy.

| Stat | Value |
|---|---|
| Commodities where AE wins (lower MSE) | **7 / 27** (26%) |
| Mean per-commodity MSE change | −0.08% (AE slightly worse on average) |
| Total forecast observations | 43,470 (1,610 × 27) |

---

## Best & worst commodities (AE vs AR1)

**Largest AE improvement (MSE):**

| Commodity | MSE AR(1) | MSE AE | Improvement |
|---|---|---|---|
| Methanol | 3.54×10⁻⁴ | 3.41×10⁻⁴ | +3.8% |
| Diesel | 9.42×10⁻⁴ | 9.16×10⁻⁴ | +2.7% |
| SGXIronOre | 6.70×10⁻⁴ | 6.64×10⁻⁴ | +0.8% |

**Largest AE deterioration:**

| Commodity | MSE AR(1) | MSE AE | Change |
|---|---|---|---|
| LiveCattle | 1.41×10⁻⁴ | 1.43×10⁻⁴ | −1.5% |
| WTI | 1.20×10⁻³ | 1.21×10⁻³ | −0.9% |
| HeatingOil | 8.31×10⁻⁴ | 8.37×10⁻⁴ | −0.7% |

**Near-ties (|Δ| < 0.1%):** Soybeans, Copper, Zinc, Lithium, Corn, Gold, Nickel, Platinum, and most agriculture names.

**Highest volatility (both models):** NaturalGas (MSE ~2.6×10⁻³), WTI, Gasoline, Diesel, Brent.

**Lowest volatility:** Lithium, Gold, LiveCattle (MSE ~1.2–1.4×10⁻⁴).

---

## Interpretation

1. **Marginal overall.** Pooled MSE worsens by ~0.14% with AE factors — economically negligible but directionally unfavorable.

2. **Heterogeneous by commodity.** AE helps a minority (7/27), mainly Methanol, Diesel, and SGXIronOre. Energy and livestock show the largest AE losses.

3. **Consistent with experiment results.** Forecast-Shapley φ_k ≈ 0 (see `results/experiments_report.md`) confirms factors add no meaningful OOS forecast value on this sample.

4. **Window choice.** M = 1,260 is a repo default (~5 years), not specified in the paper. With only ~12.7 years of data, the first ~5 years are estimation-only; OOS evaluation runs ~2018–2026.

---

## Outputs

| File | Contents |
|---|---|
| `results/forecasts.csv` | Date × commodity actuals and forecasts |
| `results/errors.csv` | Forecast errors (AR1, vanilla AE) |
| `results/summary.csv` | Per-commodity MSE/MAE summary |
| `results/summary.md` | Auto-generated table summary |

Full per-commodity table: `results/summary.csv` (27 rows + ALL aggregate).
