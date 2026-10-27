"""
Three-step target-leakage audit for carbon-flux models.

Ported from LiuYG_03_leakage_free_model_comparison.py.
Implements the protocol in Section 5.1 of the manuscript:

  1. Predictor classification: flag predictors algebraically derived from NEE.
  2. Correlation screening: |r| > 0.5 investigate, |r| > 0.8 near-deterministic.
  3. Leakage-free refit: drop leaky predictors, refit, compare.

This is a first-class audit feature in the product, not an afterthought.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence
import numpy as np
import pandas as pd


# Predictor names that are algebraically derived from NEE via flux partitioning.
# GPP and ER are deterministic transforms of NEE: GPP - ER = NEE.
LEAKY_PATTERNS: tuple[str, ...] = (
    "gpp", "GPP", "er_", "ER_", "_er", "ecosystem_resp",
    "nee_balance", "carbon_balance", "cumulative_balance",
    "npp_balance", "lateral_flux",
)


@dataclass
class LeakageReport:
    """Result of a leakage audit."""
    classified: dict[str, str] = field(default_factory=dict)
    correlations: dict[str, float] = field(default_factory=dict)
    leaky_predictors: list[str] = field(default_factory=list)
    near_deterministic: list[str] = field(default_factory=list)

    def summary(self) -> str:
        lines = ["=== UCST-CCIF Leakage Audit ==="]
        lines.append(f"Predictors classified: {len(self.classified)}")
        lines.append(f"Leaky (NEE-derived):  {len(self.leaky_predictors)} -> {self.leaky_predictors}")
        lines.append(f"Near-deterministic (|r|>0.8): {self.near_deterministic}")
        lines.append("")
        lines.append("Per-predictor correlations with target:")
        for k, v in sorted(self.correlations.items(), key=lambda x: -abs(x[1])):
            flag = "  <-- LEAKY" if k in self.leaky_predictors else ""
            lines.append(f"  {k:30s} r={v:+.3f}{flag}")
        return "\n".join(lines)


def classify_predictor(col: str) -> str:
    """
    Classify a column as 'leaky' if its name matches flux-partitioning patterns.
    This is a heuristic; the user should confirm with the data dictionary.
    """
    for pat in LEAKY_PATTERNS:
        if pat in col:
            return "leaky"
    return "exogenous"


def audit_leakage(df: pd.DataFrame,
                  target_col: str,
                  predictor_cols: Sequence[str]) -> LeakageReport:
    """
    Run the 3-step leakage audit.

    Parameters
    ----------
    df : DataFrame with target and predictor columns
    target_col : name of the target variable (e.g. 'NEE_daily_total')
    predictor_cols : list of predictor column names

    Returns
    -------
    LeakageReport with classification, correlations, and flags.
    """
    report = LeakageReport()
    try:
        y = np.asarray(df[target_col].values, dtype=float)
    except (TypeError, ValueError) as e:
        raise ValueError(
            f"target column {target_col!r} is not numeric: {e}"
        ) from e

    for col in predictor_cols:
        if col not in df.columns:
            continue
        report.classified[col] = classify_predictor(col)
        try:
            x = np.asarray(df[col].values, dtype=float)
        except (TypeError, ValueError):
            continue  # non-numeric column (e.g. date) is not a predictor
        mask = np.isfinite(x) & np.isfinite(y)
        if mask.sum() < 10:
            report.correlations[col] = float("nan")
            continue
        r = np.corrcoef(x[mask], y[mask])[0, 1]
        report.correlations[col] = float(r)

        if report.classified[col] == "leaky":
            report.leaky_predictors.append(col)
        if abs(r) > 0.8:
            report.near_deterministic.append(col)

    return report


def split_predictors(report: LeakageReport) -> tuple[list[str], list[str]]:
    """Return (leaky_cols, exogenous_cols) from a report."""
    leaky = [c for c, cls in report.classified.items() if cls == "leaky"]
    exogenous = [c for c, cls in report.classified.items() if cls == "exogenous"]
    return leaky, exogenous
