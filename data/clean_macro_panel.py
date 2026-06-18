#!/usr/bin/env python3
"""Clean ``data/macro_panel_data_raw.xlsx`` into tidy CSVs for the experiments.

The workbook stores many Bloomberg series across 7 category sheets. Within each
sheet, series are laid out in repeating 3-column blocks::

    col c       col c+1      col c+2
    -------     ---------    -------
    <name>      (blank)      (blank)    row 2  - human name
    "Ticker"    <ticker>     (blank)    row 3
    "Field"     "PX_LAST"    (blank)    row 4
    "Date"      "Value"      (blank)    row 5  - column labels
    <serial>    <value>                 row 6+ - data (Excel date serials)

This script parses every block by its Bloomberg ticker (robust to column order),
maps it to a clean snake_case name with a stationary-transform and frequency tag,
converts Excel serial dates, and writes:

    data/macro/series/<name>.csv     one tidy (date,value) file per series
    data/macro/macro_panel_raw.csv   wide daily-union panel of raw levels
    data/macro/manifest.csv          name, ticker, group, freq, transform, flags
    data/macro/CLEANING_LOG.md       provenance + decisions

Excluded by request: Global PMI and Global Manufacturing PMI (no data from 2013).
The energy spot prices (WTI/Brent/NatGas) are flagged ``circular`` because those
commodities are in the modelled panel; the macro loader drops them from the
regressor set by default (see src/macro_data.py).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = PROJECT_ROOT / "data" / "macro_panel_data_raw.xlsx"
OUT_DIR = PROJECT_ROOT / "data" / "macro"
SERIES_DIR = OUT_DIR / "series"


@dataclass(frozen=True)
class SeriesMeta:
    name: str          # clean snake_case key
    group: str         # FX / Rates / Risk / Energy / Inflation / Growth / Supply
    transform: str     # level / diff / log_change
    include: bool = True
    circular: bool = False
    note: str = ""


# Keyed by the Bloomberg ticker exactly as it appears in the sheet (row "Ticker").
TICKER_META: dict[str, SeriesMeta] = {
    # FX / Dollar (daily levels -> log-changes)
    "DXY Curncy": SeriesMeta("usd_dxy", "FX", "log_change"),
    "USDCNY Curncy": SeriesMeta("usd_cny", "FX", "log_change"),
    "USDBRL Curncy": SeriesMeta("usd_brl", "FX", "log_change"),
    "USDAUD Curncy": SeriesMeta("usd_aud", "FX", "log_change"),
    "USTWBGD Index": SeriesMeta("usd_twi", "FX", "log_change", note="Broad trade-weighted USD."),
    # Rates & monetary policy
    "FDTR Index": SeriesMeta("fed_funds", "Rates", "diff", note="Policy target rate; use change."),
    "USGG2YR Index": SeriesMeta("ust_2y", "Rates", "diff"),
    "USGG10YR Index": SeriesMeta("ust_10y", "Rates", "diff"),
    "GTII10 Govt": SeriesMeta("tips_10y", "Rates", "diff", note="10y real rate; level is an alternative."),
    "USYC2Y10 Index": SeriesMeta("curve_2s10s", "Rates", "level", note="Already a spread."),
    # Risk sentiment & credit (stationary in levels)
    "VIX Index": SeriesMeta("vix", "Risk", "level"),
    "MOVE Index": SeriesMeta("move", "Risk", "level", note="Rates vol."),
    "LUACOAS Index": SeriesMeta("credit_ig_oas", "Risk", "level", note="IG OAS."),
    "LF98OAS Index": SeriesMeta("credit_hy_oas", "Risk", "level", note="HY OAS."),
    # Energy cost (commodity spot prices -> CIRCULAR with the modelled panel)
    "CL1 Comdty": SeriesMeta("wti", "Energy", "log_change", circular=True, note="WTI is in the panel."),
    "CO1 Comdty": SeriesMeta("brent", "Energy", "log_change", circular=True, note="Brent is in the panel."),
    "NG1 Comdty": SeriesMeta("natgas", "Energy", "log_change", circular=True, note="NatGas is in the panel."),
    # Inflation
    "CPI YOY Index": SeriesMeta("cpi_yoy", "Inflation", "level", note="Already a YoY rate."),
    "PPI YOY Index": SeriesMeta("ppi_yoy", "Inflation", "level", note="Already a YoY rate."),
    "CPSFHOME Index": SeriesMeta("food_cpi", "Inflation", "log_change", note="Food CPI index (monthly)."),
    "CPUPENER Index": SeriesMeta("energy_cpi", "Inflation", "log_change", note="Energy CPI index (monthly)."),
    "USGGBE10 Index": SeriesMeta("breakeven_10y", "Inflation", "level"),
    # Growth & demand
    "MPMIGLCA Index": SeriesMeta("global_pmi", "Growth", "level", include=False,
                                 note="Excluded: data starts ~2023, not 2013."),
    "CPMINDX Index": SeriesMeta("china_pmi", "Growth", "level", note="Diffusion index."),
    "CHVAIOY Index": SeriesMeta("china_ip_yoy", "Growth", "level", note="Already YoY %."),
    "IP Index": SeriesMeta("us_ip", "Growth", "log_change", note="US industrial production index (monthly)."),
    "RSTAMOM Index": SeriesMeta("retail_sales_mom", "Growth", "level", note="Already MoM %."),
    "NHSPSTOT Index": SeriesMeta("housing_starts", "Growth", "log_change", note="Monthly count."),
    "MPMIGLMA Index": SeriesMeta("global_mfg_pmi", "Growth", "level", include=False,
                                 note="Excluded: data starts ~2023, not 2013."),
    "BDIY Index": SeriesMeta("baltic_dry", "Growth", "log_change", note="Daily freight proxy."),
    # Supply shocks (weekly/monthly fundamentals; exogenous to the price panel)
    "DOEASCRD Index": SeriesMeta("eia_crude_inv", "Supply", "diff", note="Crude inventories (weekly)."),
    "DOENUSCH Index": SeriesMeta("natgas_storage", "Supply", "diff", note="NatGas storage (weekly)."),
    "BAKEOIL Index": SeriesMeta("rig_count", "Supply", "log_change", note="US oil rig count (weekly)."),
}


def _excel_serial_to_date(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s.astype(float), unit="D", origin="1899-12-30")


def _infer_freq(idx: pd.DatetimeIndex) -> str:
    if len(idx) < 3:
        return "unknown"
    med = np.median(np.diff(idx.values).astype("timedelta64[D]").astype(int))
    if med <= 4:
        return "D"
    if med <= 10:
        return "W"
    if med <= 45:
        return "M"
    return "Q"


def parse_sheet(raw: pd.DataFrame) -> list[tuple[SeriesMeta, str, pd.Series]]:
    """Return [(meta, ticker, value_series indexed by date), ...] for one sheet."""
    # Locate the "Date"/"Value" label row (first row whose first cell == "Date").
    label_row = None
    for r in range(min(12, len(raw))):
        rowvals = [str(x).strip() for x in raw.iloc[r].tolist()]
        if "Date" in rowvals:
            label_row = r
            break
    if label_row is None:
        return []
    name_row = label_row - 3
    ticker_row = label_row - 2

    out = []
    ncols = raw.shape[1]
    for c in range(ncols):
        if str(raw.iloc[label_row, c]).strip() != "Date":
            continue
        ticker = str(raw.iloc[ticker_row, c + 1]).strip()
        meta = TICKER_META.get(ticker)
        if meta is None:
            # Unknown ticker; skip but keep a placeholder name from the sheet.
            continue
        dates = _excel_serial_to_date(raw.iloc[label_row + 1:, c])
        values = pd.to_numeric(raw.iloc[label_row + 1:, c + 1], errors="coerce")
        s = pd.Series(values.values, index=dates, name=meta.name)
        s = s[~s.index.isna()].dropna().sort_index()
        s = s[~s.index.duplicated(keep="last")]
        out.append((meta, ticker, s))
    return out


def main() -> None:
    SERIES_DIR.mkdir(parents=True, exist_ok=True)
    xls = pd.ExcelFile(RAW_XLSX)

    manifest_rows = []
    series_map: dict[str, pd.Series] = {}
    log_lines = ["# Macro panel cleaning log\n",
                 f"Source: `{RAW_XLSX.name}`  |  Sheets: {', '.join(xls.sheet_names)}\n",
                 "Each series parsed from its 3-column block, Excel serials converted "
                 "to dates, numeric coercion + dedupe + sort.\n",
                 "| name | ticker | group | freq | transform | span | n | include | note |",
                 "|---|---|---|---|---|---|---|---|---|"]

    for sheet in xls.sheet_names:
        raw = pd.read_excel(xls, sheet_name=sheet, header=None)
        for meta, ticker, s in parse_sheet(raw):
            freq = _infer_freq(s.index)
            s.to_frame("value").rename_axis("date").to_csv(SERIES_DIR / f"{meta.name}.csv")
            series_map[meta.name] = s
            span = f"{s.index.min().date()}..{s.index.max().date()}" if len(s) else "EMPTY"
            manifest_rows.append({
                "name": meta.name, "ticker": ticker, "group": meta.group,
                "freq": freq, "transform": meta.transform,
                "include": meta.include, "circular": meta.circular,
                "start": s.index.min().date() if len(s) else None,
                "end": s.index.max().date() if len(s) else None,
                "n_obs": int(len(s)), "note": meta.note,
            })
            log_lines.append(
                f"| {meta.name} | {ticker} | {meta.group} | {freq} | {meta.transform} | "
                f"{span} | {len(s)} | {meta.include} | {meta.note} |"
            )

    manifest = pd.DataFrame(manifest_rows).sort_values(["group", "name"]).reset_index(drop=True)
    manifest.to_csv(OUT_DIR / "manifest.csv", index=False)

    # Wide daily-union panel of RAW levels (transforms are applied by the loader).
    wide = pd.DataFrame(series_map).sort_index()
    wide.index.name = "date"
    wide.to_csv(OUT_DIR / "macro_panel_raw.csv")

    log_lines += [
        "",
        f"\n**Parsed {len(manifest)} series** "
        f"({int(manifest['include'].sum())} included, "
        f"{int((~manifest['include']).sum())} excluded).",
        f"Excluded: {', '.join(manifest.loc[~manifest['include'], 'name'])}.",
        f"Flagged circular (dropped from regressors by default): "
        f"{', '.join(manifest.loc[manifest['circular'], 'name'])}.",
        f"Wide raw panel: {wide.shape[0]} dates "
        f"({wide.index.min().date()} -> {wide.index.max().date()}), {wide.shape[1]} series.",
    ]
    (OUT_DIR / "CLEANING_LOG.md").write_text("\n".join(log_lines), encoding="utf-8")

    print(f"Wrote {len(manifest)} series to {SERIES_DIR}")
    print(f"Wrote manifest -> {OUT_DIR / 'manifest.csv'}")
    print(f"Wrote wide raw panel -> {OUT_DIR / 'macro_panel_raw.csv'} {wide.shape}")
    print(manifest[["name", "group", "freq", "transform", "start", "end", "n_obs", "include"]].to_string(index=False))


if __name__ == "__main__":
    main()
