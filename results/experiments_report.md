# AE Factor–Macro Mapping: Experiments Report

**Generated:** 2026-06-18  
**Directive:** `AE_factor_macro_mapping_directive.md`  
**Sample:** 27 commodities, daily log-returns, 2013-10-21 → 2026-06-01 (2,870 obs)  
**Macro panel:** Bloomberg workbook `data/macro_panel_data_raw.xlsx` → cleaned to `data/macro/` (28 regressors used; see §1)

This report summarizes every experiment run so far on the merged 2013+ dataset. Experiments E4 (regime overlay) and E5 (guided AE) were **not** run.

---

## 1. Data & prerequisites

### 1.1 Commodity panel
| Item | Value |
|---|---|
| Commodities | 27 (Energy × 8, Metals × 10, Agriculture × 9) |
| Date range | 2013-10-21 → 2026-06-01 |
| Source | `data/returns.csv` (from `Raw_Data_Final_Universe.xlsx`) |

### 1.2 Macro panel (cleaned)
Script: `python data/clean_macro_panel.py`  
Output folder: `data/macro/`

| Decision | Detail |
|---|---|
| **Included** | 28 series after dropping circular energy spot prices (WTI, Brent, NatGas — they are in the commodity panel) |
| **Excluded** | Global PMI, Global Manufacturing PMI (data starts ~2023, not 2013) |
| **Groups** | FX (5), Rates (5), Risk (4), Inflation (5), Growth (6), Supply (3) |
| **Alignment** | Transforms applied at native frequency, then forward-filled to daily trading calendar |
| **Mapping sample** | 1,610 dates (aligned factor as-of dates ∩ macro panel) |

Full series list and transforms: `data/macro/manifest.csv`, `data/macro/CLEANING_LOG.md`.

### 1.3 AE factor extraction (input to all experiments)
Script: `python scripts/extract_factors.py`

| Parameter | Value |
|---|---|
| Model | Vanilla autoencoder (single-layer encoder/decoder, ReLU, K=5) |
| Rolling window M | **1,260 trading days (~5 years)** — repo default, not fixed in Cerqueti et al. (2024) |
| OOS windows | 1,610 (first forecast ~2018-10) |
| Per-window output | In-window factor series (M×K), decoder weights (N×K), live factor f_t |
| Artifact | `results/factor_bundle.npz` |

The factor-augmented forecaster uses AR(1) with p=1 and K=5 latent factors, matching the paper's BIC choice.

---

## 2. E0 — Cross-window factor alignment & stability audit

**Script:** `python scripts/run_alignment.py`  
**Purpose:** Match AE latent coordinates across rolling windows (permutation + sign ambiguity) before pooling any macro regressions.

### Method
- **Anchor 1 (output correlation):** Chained adjacent-window Hungarian matching on \|corr\|, sign fixed by matched correlation.
- **Anchor 2 (decoder geometry):** Direct match of decoder weight columns to reference by \|cosine\| similarity.
- **Reference window:** w₀ = 0 (first OOS window, forecast date 2018-10-19 area).

### Results

| Metric | Value | Gate threshold |
|---|---|---|
| Median adjacent \|corr\| (anchor 1) | **0.998** | ≥ 0.8 → stable |
| Mean / min adjacent \|corr\| | 0.995 / 0.899 | |
| Median decoder \|cosine\| (anchor 2) | 0.945 | |
| Anchor agreement rate | **1.000** | |
| Permutation-event rate | 0.000 | |
| Sign-flip rate (all factors) | 0.000 | |

### Verdict: **STABLE**

Factors have a persistent identity across windows. Cross-window pooled macro mapping (E1/E2) is methodologically valid.

**Outputs:** `results/factors_aligned.csv`, `results/alignment_stability.csv`, `results/alignment_report.md`

---

## 3. Forecast-Shapley φ_k (factor importance for OOS accuracy)

**Script:** `python scripts/run_factor_shapley.py`  
**Purpose:** Rank each aligned factor by its contribution to out-of-sample forecast MSE reduction vs. plain AR(1). This is the *forecast* Shapley layer (distinct from E2 macro-SHAP).

### Method
- Exact Shapley over all 2^K = 32 factor subsets per (window, commodity).
- Value function: v(S) = MSE(AR1) − MSE(AR1 + factors in S).
- Negative φ_k ⇒ factor k *reduces* forecast error when included.

### Pooled results (all commodities, all 1,610 windows)

| Factor | φ_k (MSE reduction) | \|share\| | Rank |
|---|---|---|---|
| f2 | −4.37×10⁻⁷ | 43.9% | 1 |
| f1 | −1.74×10⁻⁷ | 17.5% | 2 |
| f3 | −1.65×10⁻⁷ | 16.5% | 3 |
| f5 | −1.43×10⁻⁷ | 14.4% | 4 |
| f4 | +7.66×10⁻⁸ | 7.7% | 5 |

| Aggregate | Value |
|---|---|
| Pooled MSE — AR(1) | 6.002×10⁻⁴ |
| Pooled MSE — full AE model | 6.010×10⁻⁴ |
| Sum φ_k (efficiency check) | −8.43×10⁻⁷ |

### Interpretation
All φ_k magnitudes are tiny; pooled MSE is **slightly worse** with all factors than AR(1) alone. The AE factors do not improve one-step daily forecasts on this sample. f2 carries the largest (still negligible) marginal weight; f4 is the only factor with a positive φ (marginally harmful).

**Outputs:** `results/forecast_shapley.csv`, `results/forecast_shapley_ranking.csv`

---

## 4. E1 — Linear spanning regression + incremental-content test

**Script:** `python scripts/run_macro_mapping.py`  
**Sample:** 1,610 aligned factor dates × 28 macro regressors (daily, stationary)

### 4.1 Per-factor OLS spanning (HAC standard errors)

Regressions: f_k,t = α_k + θ_k' M_t + u_k,t (standardized θ, Newey-West with 7 lags).

| Factor | R² | Dominant macro drivers |
|---|---|---|
| f1 | 0.131 | credit_hy_oas, cpi_yoy, credit_ig_oas |
| f2 | 0.101 | credit_hy_oas, credit_ig_oas, cpi_yoy |
| f3 | 0.158 | credit_ig_oas, credit_hy_oas, usd_twi |
| f4 | **0.231** | ust_10y, tips_10y, usd_twi |
| f5 | **0.217** | ust_10y, tips_10y, ppi_yoy |

**Pattern:** Credit spreads and inflation explain f1–f3 (10–16% variance). Rate factors (10y yield, TIPS, TWI) dominate f4–f5 (22–23%). No factor is strongly explained by macro (all R² < 0.25).

Full coefficient matrix: `results/e1_spanning_coefficients.csv`

### 4.2 Bai–Ng (2006) spanning diagnostic (canonical correlations)

Tests whether the 5-dimensional latent factor space is linearly spanned by the 28-dimensional macro panel.

| Canonical correlation | Value |
|---|---|
| 1st | 0.581 |
| 2nd | 0.374 |
| 3rd | 0.336 |
| 4th | 0.222 |
| 5th | 0.111 |
| **Min** | **0.111** |
| Mean | 0.325 |

**Conclusion:** The factor space is **not spanned** by the macro panel. The largest canonical correlation (0.58) is well below 1; at least 4 of 5 latent directions have substantial macro-orthogonal content.

### 4.3 Incremental-content test (f vs. f̂^M vs. u)

Decompose f_k = f̂^M_k + u_k via ridge-regularized projection onto macro (standardized regressors, α=10). Re-run factor-augmented forecaster three ways:

| Variant | RMSE (AR1 baseline) | RMSE (factor-augmented) | Δ vs AR1 |
|---|---|---|---|
| **Original f** | 0.024499 | 0.024516 | +0.000017 (worse) |
| **Macro-spanned f̂^M** | 0.024499 | 0.024917 | +0.000418 (much worse) |
| **Residual u** | 0.024499 | 0.024532 | +0.000033 (worse) |

**Interpretation:**
- Original factors add no forecast value (consistent with §3).
- The macro-spanned reconstruction **hurts** forecasts — the linear macro map captures correlation structure in f but not the part useful for prediction.
- Residual (macro-orthogonal) factors behave like the original (slightly harmful).
- "Macro-spanned share of forecast value" is **undefined** because the original factors do not beat AR(1).

**Outputs:** `results/e1_spanning_summary.csv`, `results/e1_bai_ng_spanning.json`, `results/e1_incremental_rmse.csv`, `results/e1_incremental_shapley.csv`

---

## 5. E2 — Nonlinear macro mapping + macro-SHAP

**Method:** Gradient-boosted trees f_k = h_k(M_t) with purged/embargoed time-series CV (5 folds, 21-day embargo). Report out-of-fold R² and mean |SHAP| macro attribution.

| Factor | R² (nonlinear) | R² (linear) | Nonlinearity premium | Top macro (SHAP) |
|---|---|---|---|---|
| f1 | −0.053 | −0.218 | +0.165 | usd_twi, ust_10y, curve_2s10s |
| f2 | −0.181 | −0.289 | +0.108 | usd_aud, tips_10y, usd_twi |
| f3 | −0.105 | −1.557 | **+1.453** | usd_twi, usd_aud, usd_cny |
| f4 | −0.098 | −0.666 | +0.568 | usd_twi, usd_cny, usd_aud |
| f5 | −0.340 | −1.304 | +0.964 | ust_10y, tips_10y, usd_aud |

### Interpretation
- **Out-of-fold R² is negative for all factors** — nonlinear macro models do not generalize; no stable nonlinear macro identity is recoverable.
- Large nonlinearity premiums (especially f3, f5) reflect in-sample overfit of GBT on small effective samples, not genuine nonlinear structure.
- SHAP consistently highlights **USD block** (twi, aud, cny) and **rates** (ust_10y, tips_10y) — consistent with E1's dominant drivers, but without predictive power OOS.
- **E1 remains the defensible mapping layer**; E2 does not overtake it.

**Output:** `results/e2_nonlinear_summary.csv`

---

## 6. E3 — Decoder-Jacobian commodity fingerprint

**Script:** `python scripts/run_jacobian.py`  
**Method:** Mean aligned decoder weight columns J_{·k} = ∂x̂/∂f_k across 1,610 windows. Sector taxonomy splits Base vs. Precious metals.

### Sector intensity (mean |loading| per commodity in sector)

| Sector | f1 | f2 | f3 | f4 | f5 |
|---|---|---|---|---|---|
| PreciousMetals | **0.415** | **0.570** | **0.486** | 0.162 | 0.170 |
| Energy | 0.347 | 0.251 | 0.122 | 0.295 | **0.341** |
| Agriculture | 0.275 | 0.233 | 0.364 | 0.277 | 0.275 |
| BaseMetals | 0.122 | 0.102 | 0.182 | **0.319** | 0.121 |

### Per-factor identity assignment

| Factor | Dominant sector | Top commodities | Canonical macro hypothesis (directive) | E1 macro match? |
|---|---|---|---|---|
| **f1** | PreciousMetals | HRWWheat, HeatingOil, Corn, Brent, Silver | Real rates, USD, VIX | Partial — credit/inflation, not rates |
| **f2** | PreciousMetals | Silver, Gold, Soybeans, Corn, Platinum | Real rates, USD, VIX | Partial — credit spreads |
| **f3** | PreciousMetals | Soybeans, Silver, Gold, Corn, SoybeanOil | Real rates, USD, VIX | Partial — credit + TWI |
| **f4** | BaseMetals | Zinc, Copper, HRWWheat, Gasoline, Aluminium | Global IP, USD, real rates | **Yes** — ust_10y, tips_10y, usd_twi |
| **f5** | Energy | SoybeanOil, Soybeans, Diesel, LeanHogs, WTI | Kilian demand / oil shocks | Partial — rates dominate in E1, not supply |

### Interpretation
- Loadings are **diffuse** (top-2 concentration only 0.13–0.18 per factor) — factors are entangled across sectors, not clean sector factors.
- f2/f3 align with precious-metals intensity but load heavily on agriculture names too.
- f4 is the cleanest triangulation case: base-metals Jacobian ↔ rate/TWI macro in E1.
- f5 has energy intensity in Jacobian but rate macro in E1 — **E1/E3 disagree** on f5.

**Outputs:** `results/jacobian_loadings.csv`, `results/jacobian_fingerprint.md`

---

## 7. Cross-experiment synthesis (directive rubric)

Scoring each factor on the directive's four criteria:

| Factor | (1) Identity concentration | (2) E1/E2/E3 triangulation | (3) Forecast relevance | (4) Stability |
|---|---|---|---|---|
| f1 | Low (R²=0.13) | Weak — precious/agri mix, credit macro | None (φ≈0) | Stable (E0) |
| f2 | Low (R²=0.10) | Weak — precious/agri, credit macro | Largest \|φ\|, still ~0 | Stable |
| f3 | Low (R²=0.16) | Weak — precious/agri, credit+TWI | None | Stable |
| f4 | Moderate (R²=0.23) | **Best** — base metals ↔ rates/TWI | Slightly harmful (φ>0) | Stable |
| f5 | Moderate (R²=0.22) | Mixed — energy Jacobian, rates macro | None | Stable |

### Headline findings

1. **E0 passes.** AE factors are stable across rolling windows on the 2013+ sample — the coordinate system is economically persistent even if weakly macro-explainable.

2. **Macro mapping is weak.** Linear R² ≤ 0.23; canonical correlations far from 1; nonlinear models fail OOS. The AE captures structure **beyond** what this 28-series macro panel spans.

3. **No forecast value.** Factors do not improve one-step daily return forecasts vs. AR(1). The macro-spanned part of f is especially harmful for prediction.

4. **Best partial identity: f4.** Base-metals Jacobian fingerprint aligns with rate/TWI macro regressors — the only factor with coherent E1 + E3 triangulation.

5. **E2 adds no publishable mapping.** Negative OOS R²; stick with E1 linear results.

6. **E4/E5 not run.** Regime overlays (NBER, GFC, COVID, etc.) and guided AE retraining remain as optional next steps if a stronger mapping is needed.

---

## 8. Reproduction commands

```bash
# Data prep
python data/clean_macro_panel.py

# Factor pipeline (prerequisite for all experiments)
python scripts/extract_factors.py
python scripts/run_alignment.py
python scripts/run_factor_shapley.py
python scripts/run_jacobian.py

# Macro mapping (E1 + E2)
python scripts/run_macro_mapping.py
```

---

## 9. Output file index

| File | Experiment |
|---|---|
| `data/macro/macro_panel_raw.csv` | Macro cleaning |
| `data/macro/manifest.csv` | Macro cleaning |
| `results/factor_bundle.npz` | Factor extraction |
| `results/factors_aligned.csv` | E0 |
| `results/alignment_report.md` | E0 |
| `results/forecast_shapley_ranking.csv` | Forecast-Shapley |
| `results/e1_spanning_summary.csv` | E1 spanning |
| `results/e1_bai_ng_spanning.json` | E1 Bai–Ng |
| `results/e1_incremental_rmse.csv` | E1 incremental |
| `results/e2_nonlinear_summary.csv` | E2 |
| `results/jacobian_fingerprint.md` | E3 |
