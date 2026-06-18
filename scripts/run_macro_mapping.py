#!/usr/bin/env python3
"""E1/E2: map aligned AE factors to the observable macro panel.

Requires the macro panel (see src/macro_data.py for the expected files). Runs:
  E1  - HAC-OLS spanning regression + Bai-Ng spanning diagnostic
  E1.4 - incremental-content test (f vs macro-spanned f_hat vs residual u)
  E2  - nonlinear (GBT) mapping + SHAP + nonlinearity premium

Writes per-experiment CSVs / markdown into results/.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd

from src.data import load_return_panel
from src.factor_alignment import align_by_correlation, aligned_factor_panel
from src.factor_extraction import FactorBundle


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--bundle", type=Path, default=PROJECT_ROOT / "results" / "factor_bundle.npz")
    p.add_argument("--reference", type=int, default=0)
    p.add_argument("--frequency", choices=["D", "M"], default="D")
    p.add_argument("--skip-incremental", action="store_true",
                   help="Skip the (slower) incremental-content re-forecast.")
    p.add_argument("--output-dir", type=Path, default=PROJECT_ROOT / "results")
    return p.parse_args()


def main() -> None:
    args = parse_args()
    from src.macro_data import build_macro_panel
    from src.macro_mapping import (
        bai_ng_spanning_summary,
        incremental_content,
        nonlinear_macro_mapping,
        spanning_regression,
    )

    bundle = FactorBundle.load(args.bundle)
    panel = load_return_panel()
    alignment = align_by_correlation(bundle, reference=args.reference)
    factors = aligned_factor_panel(bundle, alignment)

    try:
        macro = build_macro_panel(frequency=args.frequency, target_index=factors.index).stationary
    except FileNotFoundError as exc:
        print("Macro panel not available yet:\n", exc)
        print("\nDrop the FRED/external CSVs into data/macro/ and re-run.")
        return

    factors = factors.reindex(macro.index).dropna()
    macro = macro.loc[factors.index]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    print(f"E1/E2 on {len(factors)} dates, {factors.shape[1]} factors, {macro.shape[1]} macro series")

    # E1 spanning regression
    reg = spanning_regression(factors, macro)
    rows = []
    for f, r in reg.items():
        rows.append({"factor": f, "r2": r.r2, "dominant": ", ".join(r.dominant[:3]),
                     "hac_lags": r.hac_lags, "n_obs": r.n_obs})
    pd.DataFrame(rows).to_csv(args.output_dir / "e1_spanning_summary.csv", index=False)
    coef = pd.DataFrame({f: r.coefficients for f, r in reg.items()})
    coef.to_csv(args.output_dir / "e1_spanning_coefficients.csv")

    # E1 Bai-Ng spanning diagnostic
    bn = bai_ng_spanning_summary(factors, macro)
    pd.Series(bn).to_json(args.output_dir / "e1_bai_ng_spanning.json")
    print(f"  Bai-Ng canonical correlations: "
          f"{[round(c, 3) for c in bn['canonical_correlations']]}")

    # E1.4 incremental content
    if not args.skip_incremental:
        inc = incremental_content(bundle, alignment, factors, macro, panel=panel)
        inc.rmse.to_csv(args.output_dir / "e1_incremental_rmse.csv")
        inc.shapley.to_csv(args.output_dir / "e1_incremental_shapley.csv")
        print(f"  Incremental: macro-spanned part retains "
              f"{inc.spanned_share_of_value:.1%} of original forecast value")

    # E2 nonlinear mapping
    nl = nonlinear_macro_mapping(factors, macro)
    nl_rows = []
    for f, r in nl.items():
        nl_rows.append({"factor": f, "r2_nonlinear": r.r2_nonlinear,
                        "r2_linear": r.r2_linear, "nonlinearity_premium": r.nonlinearity_premium,
                        "top_macro": ", ".join(r.shap_importance.head(3).index)})
    pd.DataFrame(nl_rows).to_csv(args.output_dir / "e2_nonlinear_summary.csv", index=False)
    print(f"\nWrote E1/E2 outputs to {args.output_dir}")


if __name__ == "__main__":
    main()
