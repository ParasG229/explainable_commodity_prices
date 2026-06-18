"""Macro panel M_t loader, manifest, and stationarity transforms (Data Appendix).

The mapping experiments (E1/E2) regress the aligned latent factors on an
observable macro panel. This module defines the *candidate* panel from the
directive's Data Appendix, the stationary transform each series enters with, and
a loader that assembles a date-aligned, stationary DataFrame.

The actual data is supplied by the user (FRED + a couple of external series).
Drop either:
  * one CSV per series in ``data/macro/<FRED_CODE>.csv`` with columns
    ``date,<value>`` (the standard FRED export), or
  * a single combined ``data/macro/macro_panel.csv`` with a ``date`` column and
    one column per series (named by FRED code or the ``name`` below).

Circularity caution (directive): do NOT add a broad commodity index (e.g. GSCI).
Regressors must be FX, rates, vol, credit, and real-activity series exogenous to
the commodity panel.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MACRO_DIR = PROJECT_ROOT / "data" / "macro"

# Transform codes:
#   "level"      -> use as-is (spreads, vol, breakevens are typically stationary)
#   "diff"       -> first difference
#   "log_change" -> log(x).diff()  (for positive trending levels: DXY, IP)
Transform = str


@dataclass(frozen=True)
class MacroSeries:
    name: str          # canonical short name used in regressions
    fred_code: str     # FRED series id (or "EXTERNAL" if not on FRED)
    transform: Transform
    freq: str          # "D" daily or "M" monthly
    group: str         # FX / vol / term / credit / funding / real_rate / infl / activity / uncertainty
    note: str = ""


# Candidate macro panel from the Data Appendix.
MACRO_MANIFEST: list[MacroSeries] = [
    MacroSeries("usd_broad", "DTWEXBGS", "log_change", "D", "FX",
                "Broad trade-weighted USD index (DXY is an alternative)."),
    MacroSeries("vix", "VIXCLS", "level", "D", "vol", "Equity-vol / risk."),
    MacroSeries("term_10y2y", "T10Y2Y", "level", "D", "term",
                "10y-2y term spread (T10Y3M is an alternative)."),
    MacroSeries("credit_hy_oas", "BAMLH0A0HYM2", "level", "D", "credit",
                "HY OAS (BAA-AAA spread is an alternative)."),
    MacroSeries("funding_ted", "TEDRATE", "level", "D", "funding",
                "Funding stress; SOFR-OIS preferred post-2018 if available."),
    MacroSeries("real_rate_10y", "DFII10", "level", "D", "real_rate", "10y TIPS yield."),
    MacroSeries("breakeven_10y", "T10YIE", "level", "D", "infl", "10y inflation breakeven."),
    MacroSeries("indpro", "INDPRO", "log_change", "M", "activity",
                "Industrial production (monthly robustness pass)."),
    MacroSeries("kilian_rea", "EXTERNAL", "level", "M", "activity",
                "Kilian global real activity index (download from author site)."),
    MacroSeries("baltic_dry", "EXTERNAL", "log_change", "D", "activity",
                "Baltic Dry Index, higher-frequency real-activity proxy."),
    MacroSeries("epu", "USEPUINDXD", "level", "D", "uncertainty",
                "Economic Policy Uncertainty index (daily)."),
]

MANIFEST_BY_NAME = {s.name: s for s in MACRO_MANIFEST}
MANIFEST_BY_CODE = {s.fred_code: s for s in MACRO_MANIFEST if s.fred_code != "EXTERNAL"}


@dataclass
class MacroPanel:
    raw: pd.DataFrame          # untransformed levels, date-indexed
    stationary: pd.DataFrame   # after per-series transforms
    series: list[MacroSeries] = field(default_factory=list)


def _apply_transform(s: pd.Series, transform: Transform) -> pd.Series:
    if transform == "level":
        return s
    if transform == "diff":
        return s.diff()
    if transform == "log_change":
        if (s <= 0).any():
            raise ValueError(f"log_change requires positive values for {s.name}")
        return np.log(s).diff()
    raise ValueError(f"unknown transform {transform!r}")


def _read_single_series(code: str, macro_dir: Path) -> pd.Series | None:
    path = macro_dir / f"{code}.csv"
    if not path.exists():
        return None
    df = pd.read_csv(path)
    date_col = next((c for c in df.columns if c.lower() in {"date", "observation_date", "datetime"}), df.columns[0])
    val_col = next((c for c in df.columns if c != date_col), None)
    s = pd.Series(
        pd.to_numeric(df[val_col], errors="coerce").values,
        index=pd.to_datetime(df[date_col]),
        name=code,
    )
    return s.sort_index()


def load_macro_raw(macro_dir: Path | None = None) -> pd.DataFrame:
    """Assemble raw (untransformed) macro levels from disk.

    Prefers a combined ``macro_panel.csv``; otherwise reads per-code CSVs.
    Raises a clear error listing what is missing if nothing is found.
    """
    macro_dir = macro_dir or MACRO_DIR
    combined = macro_dir / "macro_panel.csv"
    if combined.exists():
        df = pd.read_csv(combined, parse_dates=["date"]).set_index("date").sort_index()
        # Map FRED codes to canonical names where applicable.
        rename = {c: MANIFEST_BY_CODE[c].name for c in df.columns if c in MANIFEST_BY_CODE}
        return df.rename(columns=rename)

    series: dict[str, pd.Series] = {}
    for spec in MACRO_MANIFEST:
        if spec.fred_code == "EXTERNAL":
            s = _read_single_series(spec.name, macro_dir)
        else:
            s = _read_single_series(spec.fred_code, macro_dir)
            if s is None:
                s = _read_single_series(spec.name, macro_dir)
        if s is not None:
            series[spec.name] = s

    if not series:
        raise FileNotFoundError(
            f"No macro data found in {macro_dir}. Provide either "
            f"'{macro_dir / 'macro_panel.csv'}' (date + columns) or per-series CSVs "
            f"named by FRED code, e.g. {macro_dir / 'DTWEXBGS.csv'}. "
            f"Expected series: {', '.join(s.name + '(' + s.fred_code + ')' for s in MACRO_MANIFEST)}."
        )
    return pd.DataFrame(series).sort_index()


def build_macro_panel(
    macro_dir: Path | None = None,
    frequency: str = "D",
    target_index: pd.DatetimeIndex | None = None,
    include_monthly_in_daily: bool = True,
) -> MacroPanel:
    """Build a stationary macro panel.

    Parameters
    ----------
    frequency : {"D", "M"}
        "D" keeps daily series at daily frequency; monthly series (INDPRO,
        Kilian) are forward-filled if ``include_monthly_in_daily`` (use the
        monthly robustness pass for clean slow-macro inference). "M" aggregates
        everything to month-end.
    target_index : DatetimeIndex, optional
        If given (e.g. the factor as-of dates), the stationary panel is reindexed
        onto it (daily) so it aligns 1:1 with the aligned factor panel.
    """
    raw = load_macro_raw(macro_dir)
    present = [s for s in MACRO_MANIFEST if s.name in raw.columns]

    cols: dict[str, pd.Series] = {}
    for spec in present:
        if frequency == "M":
            s = raw[spec.name].resample("ME").last()
        else:
            s = raw[spec.name]
            if spec.freq == "M" and include_monthly_in_daily:
                s = s.reindex(raw.index).ffill()
            elif spec.freq == "M" and not include_monthly_in_daily:
                continue
        cols[spec.name] = _apply_transform(s, spec.transform)

    stationary = pd.DataFrame(cols).dropna(how="all")
    if frequency == "D" and target_index is not None:
        stationary = stationary.reindex(target_index).ffill()
    stationary = stationary.dropna(how="any")
    return MacroPanel(raw=raw, stationary=stationary, series=present)
