# UCST-CCIF

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.XXXXXXX.svg)](https://doi.org/10.5281/zenodo.XXXXXXX) <!-- Replace XXXX with your minted DOI after publishing the release (Zenodo auto-mints it) -->

**Conservation-Constrained Carbon Flux Integrated Framework** — auditable, cross-scale carbon accounting from enterprise Scope 1 to coastal blue carbon.

## What it does

- **Continuum model** (`ucst_ccif.compartments`): 12-pool daily land–river–coastal carbon model with Q10 temperature response, moisture constraints, and a mass-balance residual ε_C that flags bookkeeping gaps.
- **Leakage audit** (`ucst_ccif.leakage`): three-step detector that flags predictors algebraically derived from NEE (GPP, ER, cumulative balance) before they fake model performance.
- **Nested M0–M3 comparison** (`ucst_ccif.models`): scipy-optimized models where each added layer must justify itself out-of-sample.
- **Monte Carlo uncertainty** (`ucst_ccif.uncertainty`): parameter ensemble with 90% confidence intervals.
- **MVP integration kernels (v0.2.1)**:
  - `rothc_lite` — RothC 4-pool soil-C kernel (monthly, date-stamped inputs)
  - `bluecarbon_lookups` — InVEST-style mangrove/saltmarsh/seagrass stocks, burial, CH4
  - `dndc_lite` — rice CH4 Tier-1 (IPCC scaling factors, water-regime management table)
  - `landfill` — landfill CH4 Tier-1 kernel (IPCC 2006/2019: MSW × DOC × DOC_F × F × (1−OX) × MCF; 5 landfill management types; AR5/AR6 GWP display)
  - `threepg_lookups` — GBA subtropical species parameters + light NPP scoping
  - `raymond_evasion` — inland-water CO2 evasion (gas-transfer, Raymond-2013)
  - `netcdf_priors` — read-only prior registry/client for CAMS, FLUXCOM, SoilGrids, NASA CMS mangrove, SOCAT, CEADs
- **CLI**: `ucst-ccif run | audit | compare | rothc | blue | rice | evasion | priors | version`.

## Install

```bash
pip install -e ".[dev]"      # for development
pip install -e ".[app]"       # for the Streamlit MVP
pip install -e ".[data]"      # for NetCDF prior pulls (xarray + netCDF4)
```

## Quick start

```python
from ucst_ccif import CarbonContinuumModel, ParameterSet, MonteCarloEnsemble
import numpy as np

T = 365
gpp = np.clip(3.5 + 2.5*np.sin(2*np.pi*np.arange(T)/365), 0.2, 7.0)
T_air = np.full(T, 20.0)
swc = np.full(T, 0.55)
rain = np.zeros(T)

model = CarbonContinuumModel(ParameterSet())
state = model.run(gpp, T_air, swc, rain)
print(f"Annual NEE: {state.nee.mean()*365:.1f} gC m-2 yr-1")
```

## Streamlit MVP

```bash
streamlit run app/streamlit_app.py
```

Nine tabs: **Scope 1/2/3** enterprise inventory (MEE factors, Guangdong grid), **Biogenic** GBA wetland flux demo, **Leakage** audit, **NGFS V5** scenarios, **ISO 14064-3 PDF** export, **Anthropogenic ledger** (HK EPD 2023 sectors, Guangdong CEADs 2022, Global Carbon Budget 2025, CH4 by sector — rice + landfill, CCER mangrove restoration lookup, anthropogenic-vs-nature balance sheet), and a **Data guide** (free data-source map, CSV upload setup, LEAKY pattern guide, unit conversions, end-to-end worked example).

## Tests

```bash
pytest tests/ -v
```

## Roadmap — ML/AI as the next step

The current release is a **process-based + statistical** toolkit (no ML training): the continuum model, scipy-optimised M0–M3 comparison, Monte Carlo sampling and the correlation-based leakage audit are all white-box by design. The next development phase adds machine learning in **thin, auditable layers only** — ML never replaces the core ledger, the leakage audit, or the conservation residual ε_C:

| Priority | Capability | What it adds | Why it fits OCIP |
|---|---|---|---|
| **P1** | ML emulator priors (LPJ-GUESS RF/NN emulator, GMD 2025) | Cheap, reproducible GPP/NEE baseline grids as M0 priors | Replaces costly full-DGVM runs while keeping the prior pipeline read-only and testable |
| **P2** | Conformal prediction (e.g. MAPIE) | Honest prediction intervals around all M0–M3 outputs | Strengthens the falsification narrative and makes MRV uncertainty claims defensible |
| **P3** | Double ML / causal forests | M3 counterfactual attribution and CCER/CRCF additionality | Directly matches Article 6.4 baseline-and-additionality requirements |
| **P4** | Geospatial foundation models (e.g. Prithvi-EO-2.0, fine-tuned on FLUXNET) + deep ensembles | Up-scaled GPP priors and covariate-drift detection | Provides operational GPP priors for GBA; drift alarms flag model degradation before it misleads clients |

**Implementation contract for the ML phase:**
- Ship as an optional `ucst_ccif.ml` module with its own test suite; keep core dependencies lean (e.g. scikit-learn + MAPIE as extras).
- Every ML feature must pass the leakage audit before acceptance — a predictor that is algebraically derived from the target is rejected by construction.
- Validate site-to-site at GBA before any client-facing use; never adopt a foundation-model output without a local benchmark.

## Zenodo DOI

This repository is linked to Zenodo. To mint a DOI:
1. Publish a GitHub release from a tag (e.g. `v0.2.1`) — Zenodo archives it automatically.
2. Zenodo creates a record and mints a DOI (`10.5281/zenodo.XXXXXXXX`).
3. Paste the DOI into the badge at the top of this README and into the Citation section below.
4. Add the DOI to `pyproject.toml` (in `[project.urls]`) if desired.

## Citation

Liu, Y. & Cui, W. (2026). *Integrating Ecological Carbon Fluxes Across Scales: A Conservation-Constrained, Falsification-Based Modelling Framework based on Unified Complex System Theory (UCST)*. Ecological Modelling. DOI: `10.5281/zenodo.XXXXXXX` *(minted via Zenodo GitHub integration; update after first release)*.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Part of the UCST-CCIF Open Carbon Platform (OCIP) project, GBA-first.
