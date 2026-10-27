"""
Nested M0-M3 carbon-flux model comparison (UCST-CCIF).

Ported from LiuYG_03_leakage_free_model_comparison.py.

M0: baseline (Fourier seasonal + exogenous meteorology + disturbance kernel)
M1: M0 + conservation-state term
M2: M1 + state-dependent agent feedback
M3: counterfactual human-agency scenario engine (post-calibration)

Each model must justify itself out-of-sample. Calibration fit alone is
NOT evidence for retaining added complexity.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.signal import detrend


def fourier_seasonal(doy: np.ndarray, params: np.ndarray) -> np.ndarray:
    """3rd-order Fourier seasonal term. params = [a0,a1,b1,a2,b2,a3,b3]."""
    a0, a1, b1, a2, b2, a3, b3 = params[:7]
    t = 2 * np.pi * doy / 365.25
    return (a0 + a1*np.sin(t) + b1*np.cos(t)
            + a2*np.sin(2*t) + b2*np.cos(2*t)
            + a3*np.sin(3*t) + b3*np.cos(3*t))


@dataclass
class ModelResult:
    name: str
    params: np.ndarray
    calib_rmse: float
    valid_rmse: float
    valid_r2: float
    valid_mae: float
    n_params: int
    valid_predictions: np.ndarray = None


class M0Baseline:
    """
    M0: compartmentalized baseline.
    Fourier seasonal + exogenous predictors + disturbance kernel.
    No conservation state, no agent feedback.
    """
    name = "M0"

    def __init__(self, exo_cols: list[str], disturbance_col: str = "disturbance"):
        self.exo_cols = exo_cols
        self.disturbance_col = disturbance_col
        self.n_exo = len(exo_cols)
        self.n_params = 7 + self.n_exo + 1  # Fourier + exo + disturbance

    def predict(self, params: np.ndarray, df: pd.DataFrame) -> np.ndarray:
        seasonal = fourier_seasonal(df["doy"].values, params)
        exo_sum = np.zeros(len(df))
        for i, col in enumerate(self.exo_cols):
            exo_sum += params[7 + i] * df[col].values
        c_dist = params[7 + self.n_exo]
        return seasonal + exo_sum + c_dist * df[self.disturbance_col].values

    def residuals(self, params: np.ndarray, df: pd.DataFrame, target: str) -> np.ndarray:
        return self.predict(params, df) - df[target].values


class M1Conservation(M0Baseline):
    """
    M1: M0 + conservation-state term (cumulative exogenous anomaly, detrended).
    Uses leakage-free exogenous conservation state only.
    """
    name = "M1"

    def __init__(self, exo_cols: list[str], disturbance_col: str = "disturbance"):
        super().__init__(exo_cols, disturbance_col)
        self.n_params = 7 + self.n_exo + 1 + 2  # + C_state, dC_state

    def predict(self, params: np.ndarray, df: pd.DataFrame) -> np.ndarray:
        base = super().predict(params[: 7 + self.n_exo + 1], df)
        c_C = params[7 + self.n_exo + 1]
        c_dC = params[7 + self.n_exo + 2]
        return base + c_C * df["C_state"].values + c_dC * df["dC_state"].values


def compute_conservation_state(df: pd.DataFrame, exo_cols: list[str]) -> pd.DataFrame:
    """
    Compute leakage-free conservation state from exogenous anomalies.
    This is the M1_exo construction: z-scored anomalies, cumulative, detrended.
    """
    df = df.copy()
    z_cols = []
    for col in exo_cols:
        seasonal = df.groupby("month")[col].transform("mean")
        anom = df[col] - seasonal
        std = anom.std()
        df[f"_{col}_z"] = anom / std if std > 0 else 0.0
        z_cols.append(f"_{col}_z")
    df["_env_anomaly"] = df[z_cols].mean(axis=1)
    cum = np.cumsum(df["_env_anomaly"].values)
    df["C_state"] = detrend(cum)
    df["dC_state"] = np.diff(df["C_state"], prepend=df["C_state"].iloc[0])
    return df


def fit_model(model, calib: pd.DataFrame, valid: pd.DataFrame,
              target: str, init: np.ndarray,
              bounds: tuple[np.ndarray, np.ndarray]) -> ModelResult:
    """Fit a model with scipy least_squares and report out-of-sample metrics."""
    fit = least_squares(model.residuals, init, args=(calib, target),
                        bounds=bounds, max_nfev=10000)
    params = fit.x
    calib_rmse = float(np.sqrt(np.mean(model.residuals(params, calib, target) ** 2)))

    v_pred = model.predict(params, valid)
    v_obs = valid[target].values
    valid_rmse = float(np.sqrt(np.mean((v_pred - v_obs) ** 2)))
    valid_mae = float(np.mean(np.abs(v_pred - v_obs)))
    ss_res = float(np.sum((v_obs - v_pred) ** 2))
    ss_tot = float(np.sum((v_obs - np.mean(v_obs)) ** 2))
    valid_r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0

    return ModelResult(
        name=model.name, params=params,
        calib_rmse=calib_rmse, valid_rmse=valid_rmse,
        valid_r2=valid_r2, valid_mae=valid_mae,
        n_params=len(init), valid_predictions=v_pred,
    )


def compare_m0_m1(df: pd.DataFrame, target: str,
                  exo_cols: list[str],
                  calib_end_year: int = 2020,
                  disturbance_col: str = "disturbance") -> dict[str, ModelResult]:
    """
    Run the full M0 vs M1_exo comparison.

    df must have columns: date, doy, month, year, target, exo_cols, disturbance_col.
    """
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df["doy"] = df["date"].dt.dayofyear
    df["month"] = df["date"].dt.month
    df["year"] = df["date"].dt.year
    needed = [target] + list(exo_cols) + [disturbance_col]
    df = df.dropna(subset=needed)
    df = compute_conservation_state(df, exo_cols)

    calib = df[df["year"] <= calib_end_year].copy()
    valid = df[df["year"] > calib_end_year].copy()

    # M0 init/bounds
    n_exo = len(exo_cols)
    m0_init = [0, -0.8, -0.3, 0.2, 0.1, 0.05, 0.0]
    m0_init += [0.01] * n_exo + [0.1]
    m0_lo = [-3, -3, -3, -2, -2, -1, -1] + [-5]*n_exo + [-3]
    m0_hi = [3, 3, 3, 2, 2, 1, 1] + [5]*n_exo + [3]

    m0 = M0Baseline(exo_cols, disturbance_col)
    r0 = fit_model(m0, calib, valid, target,
                   np.array(m0_init), (np.array(m0_lo), np.array(m0_hi)))

    # M1 init/bounds (M0 params + 2 conservation terms)
    m1_init = list(r0.params) + [0.001, 0.1]
    m1_lo = list(m0_lo) + [-0.01, -5]
    m1_hi = list(m0_hi) + [0.01, 5]
    m1 = M1Conservation(exo_cols, disturbance_col)
    r1 = fit_model(m1, calib, valid, target,
                   np.array(m1_init), (np.array(m1_lo), np.array(m1_hi)))

    return {"M0": r0, "M1": r1}
