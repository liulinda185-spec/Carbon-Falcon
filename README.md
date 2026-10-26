# UCST-CCIF

**Conservation-Constrained Carbon Flux Integrated Framework** — auditable, cross-scale carbon accounting from enterprise Scope 1 to coastal blue carbon.

## What it does

- **Continuum model** (`ucst_ccif.compartments`): 12-pool daily land–river–coastal carbon model with Q10 temperature response, moisture constraints, and a mass-balance residual ε_C that flags bookkeeping gaps.
- **Leakage audit** (`ucst_ccif.leakage`): three-step detector that flags predictors algebraically derived from NEE (GPP, ER, cumulative balance) before they fake model performance.
- **Nested M0–M3 comparison** (`ucst_ccif.models`): scipy-optimized models where each added layer must justify itself out-of-sample.
- **Monte Carlo uncertainty** (`ucst_ccif.uncertainty`): parameter ensemble with 90% confidence intervals.
- **MVP integration kernels (v0.2.0)**:
  - `rothc_lite` — RothC 4-pool soil-C kernel (monthly, date-stamped inputs)
  - `bluecarbon_lookups` — InVEST-style mangrove/saltmarsh/seagrass stocks, burial, CH4
  - `dndc_lite` — rice CH4 Tier-1 (IPCC scaling factors, water-regime management table)
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

Features: enterprise CSV → Scope 1 estimate, GBA wetland biogenic demo, leakage audit, NGFS V5 scenario lookup, ISO 14064-3 PDF export.

## Tests

```bash
pytest tests/ -v
```


## Citation

Liu, Y. & Cui, W. (2026). *Integrating Ecological Carbon Fluxes Across Scales: A Conservation-Constrained, Falsification-Based Modelling Framework based on Unified Complex System Theory (UCST)*. Ecological Modelling.

## License

Apache License 2.0 — see [LICENSE](LICENSE). Part of the UCST-CCIF Open Carbon Platform (OCIP) project, GBA-first.
