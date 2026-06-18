"""Macro panel loader for the cleaned Bloomberg panel (``data/macro/``).

The raw workbook is parsed by ``data/clean_macro_panel.py`` into:
  * ``data/macro/macro_panel_raw.csv`` -- wide daily-union panel of raw levels,
  * ``data/macro/manifest.csv``        -- per-series group / freq / transform / flags.

This module turns that into a *stationary* panel aligned to a target date index
(the factor as-of dates) for the E1/E2 mapping experiments.

Transform conventions (set per series in the manifest):
  * ``level``      -- spreads, vol, breakevens, diffusion indices, YoY/MoM rates
                      that are already stationary.
  * ``diff``       -- first difference (interest-rate yields, inventory levels).
  * ``log_change`` -- log first difference (FX, price indices, freight, IP).

Each transform is applied at the series' *native* frequency, then the result is
reindexed onto the (daily) target index with forward-fill, so a monthly reading
enters as the most-recent-known value on each trading day. Set
``frequency="M"`` for the slow-macro robustness pass.

Defaults drop series flagged ``circular`` (the energy spot prices WTI/Brent/
NatGas, which are themselves in the modelled commodity panel) and series flagged
``include=False`` (Global PMI / Global Manufacturing PMI, which lack 2013 data).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MACRO_DIR = PROJECT_ROOT / "data" / "macro"
RAW_PANEL = MACRO_DIR / "macro_panel_raw.csv"
MANIFEST = MACRO_DIR / "manifest.csv"


@dataclass
class MacroPanel:
    raw: pd.DataFrame          # untransformed levels, date-indexed (native obs)
    stationary: pd.DataFrame   # transformed + aligned to target index
    manifest: pd.DataFrame     # metadata for the included series


def _apply_transform(s: pd.Series, transform: str) -> pd.Series:
    s = s.dropna()
    if transform == "level":
        return s
    if transform == "diff":
        return s.diff()
    if transform == "log_change":
        if (s <= 0).any():
            # Shift to positive domain is unsafe; fall back to simple pct change.
            return s.pct_change()
        return np.log(s).diff()
    raise ValueError(f"unknown transform {transform!r}")


def load_manifest() -> pd.DataFrame:
    if not MANIFEST.exists():
        raise FileNotFoundError(
            f"{MANIFEST} not found. Run `python data/clean_macro_panel.py` first."
        )
    return pd.read_csv(MANIFEST)


def load_macro_raw() -> pd.DataFrame:
    if not RAW_PANEL.exists():
        raise FileNotFoundError(
            f"{RAW_PANEL} not found. Run `python data/clean_macro_panel.py` first."
        )
    return pd.read_csv(RAW_PANEL, parse_dates=["date"]).set_index("date").sort_index()


def build_macro_panel(
    frequency: str = "D",
    target_index: pd.DatetimeIndex | None = None,
    drop_circular: bool = True,
    include_groups: list[str] | None = None,
    exclude_series: list[str] | None = None,
) -> MacroPanel:
    """Assemble the stationary macro panel.

    Parameters
    ----------
    frequency : {"D", "M"}
        "D" keeps daily series daily and forward-fills slower series; "M"
        aggregates everything to month-end before transforming.
    target_index : DatetimeIndex, optional
        If given (daily mode), the panel is reindexed onto it (forward-filled)
        so it aligns 1:1 with the aligned factor panel.
    drop_circular : bool
        Drop series flagged circular (energy spot prices). Default True.
    include_groups : list[str], optional
        Restrict to these manifest groups (e.g. ["FX", "Rates", "Risk"]).
    exclude_series : list[str], optional
        Additional series names to drop.
    """
    manifest = load_manifest()
    raw = load_macro_raw()

    sel = manifest[manifest["include"]].copy()
    if drop_circular:
        sel = sel[~sel["circular"]]
    if include_groups is not None:
        sel = sel[sel["group"].isin(include_groups)]
    if exclude_series:
        sel = sel[~sel["name"].isin(exclude_series)]
    sel = sel[sel["name"].isin(raw.columns)]

    cols: dict[str, pd.Series] = {}
    for _, row in sel.iterrows():
        s = raw[row["name"]].dropna()
        if frequency == "M":
            s = s.resample("ME").last()
        s = _apply_transform(s, row["transform"])
        cols[row["name"]] = s

    stationary = pd.DataFrame(cols).sort_index()
    if frequency == "M":
        stationary = stationary.resample("ME").last()
    else:
        # Daily mode: forward-fill every (transformed) series onto a daily grid so
        # monthly/weekly readings enter as the most-recent-known value each day.
        if target_index is not None:
            grid = pd.DatetimeIndex(target_index)
        else:
            grid = pd.bdate_range(stationary.index.min(), stationary.index.max())
        full = stationary.index.union(grid)
        stationary = stationary.reindex(full).ffill().reindex(grid)

    stationary = stationary.dropna(how="any")
    # Drop degenerate (zero-variance) columns that would break standardization.
    nunique = stationary.nunique()
    degenerate = nunique[nunique <= 1].index.tolist()
    if degenerate:
        stationary = stationary.drop(columns=degenerate)
        sel = sel[~sel["name"].isin(degenerate)]
    return MacroPanel(raw=raw[sel["name"]], stationary=stationary, manifest=sel.reset_index(drop=True))
