# OCIP — Open Carbon Platform (Carbon Falcon)

[![Version](https://img.shields.io/badge/version-v0.3.0-blue)]()
[![Tests](https://img.shields.io/badge/tests-75%2F75-green)]()
[![License](https://img.shields.io/badge/license-Apache--2.0-gold)]()

**OCIP (Open Carbon Platform)** is the independent carbon-verification layer for
GBA enterprises, auditors and research teams, built on the **UCST-CCIF**
(Conservation-Constrained Carbon Flux Integrated Framework) engine.

> The audit is the product — not the number.

## What's new in v0.3.0

- **Four-ledger upload wizard (tab 0)**: upload the Activity, Flux, Stock and
  Intervention ledgers as CSVs — column validation + downloadable templates.
- **7-step audit pipeline (tab 10)**: `audit_pipeline.run_audit` runs S1
  (boundary) → S2 (factors) → S3 (conservation, Eq.1) → S4 (scale, Eq.4-5) →
  S5 (additionality, Eq.2-3) → S6 (leakage, Eq.7 + refit) → S7 (uncertainty),
  and returns the **8 audit artifacts** plus an audit certificate.
- **Attribution layer**: `conservation_reconcile` (Eq.1 residual), `attribution_split`
  (Eq.2 agent test), `additionality_counterfactual` (Eq.3 active/passive).
- **Leakage step 3**: `refit_without_leakage` — drop leaky predictors, refit,
  quantify the *apparent* improvement (Sapelo honest baseline: 36.1%).
- **M2a / M3 models**: `M2aAgent` (M1 + exogenous agent state) and
  `m3_counterfactual` (military / restoration / DAC scenario parameters from
  Sapelo Table 10).
- **75/75 pytest suite** (previous: 43) covering attribution, audit pipeline,
  leakage-free refit and M2a/M3.

## The problem it solves

A company says it emitted 500 t and removed 420 t by investing in a wetland,
solar panels and a lawn. Who verifies that?

OCIP answers with **conservation bookkeeping**:

- **S1 boundary** — which emissions are in scope;
- **S2 factors** — activity × emission factor library;
- **S3 conservation (Eq.1)** — claimed removals vs independently observed
  removals. The residual ε_C = observed − claimed. Negative ⇒ over-claiming.
- **S4 scale (Eq.4-5)** — daily flux integral vs stock-ledger removals;
- **S5 additionality (Eq.2-3)** — active trigger vs passive response;
- **S6 leakage (Eq.7)** — 3-step screen: classify → correlate → no-leak refit;
- **S7 uncertainty** — u95 budget for emissions and removals.

Eight artifacts: verified emission interval, verified removal interval,
conservation residual ε_C, scale residual, leakage RYG, attribution
breakdown, uncertainty budget, and an **audit certificate** (PASS / REVIEW /
FAIL / INCOMPLETE). Missing data is reported as a **data gap** — never
silently estimated.

## Quick start

```bash
pip install -e .[dev,app]
streamlit run app/streamlit_app.py
```

Eleven tabs: **0. Upload 4 Ledgers**, 1. Scope 1, 2. Scope 2, 3. Scope 3,
4. Biogenic flux, 5. Leakage audit, 6. NGFS scenarios, 7. Export PDF,
8. Anthropogenic vs nature, 9. Data guide, **10. Audit Report**.

## Library API

```python
from ucst_ccif import run_audit, conservation_reconcile, refit_without_leakage

report = run_audit(
    activity_df=...,        # columns: scope, category, activity_key, quantity
    flux_df=...,            # columns: date, NEE_daily_total, ...
    stock_df=...,           # columns: area_ha, removal_tco2e
    intervention_df=...,    # columns: scenario, baseline_removal_tco2e, intervention_removal_tco2e
    area_ha=100.0,
    claimed_removals_tco2e=420.0,
)
print(report.certificate_status)      # e.g. "PASS — ledger consistent within tolerance"
print(report.artifacts())             # the 8 audit artifacts
```

## Manuscript

Methodology: **Liu, Y., & Cui, S. — Conservation-Constrained Integrated
Framework (UCST-CCIF)** preprint, `ssrn-7417192` (30 pp).

The framework links ecosystem flux observations (L1) to policy-scale carbon
bookkeeping (L5) with one rule: **mass is conserved; every claim leaves a
residual; every model is audited for leakage before its numbers are trusted.**

## Roadmap

- [x] v0.3.0 — four-ledger upload, 7-step audit pipeline, leakage-free refit, M2a/M3
- [ ] v0.4.0 — OCIP open network: shared factor library + community audits
- [ ] v0.5.0 — API + third-party auditor onboarding

## Citation / DOI

Zenodo DOI will be minted on the **v0.3.0** GitHub release. Steps:

1. Create the tag and release on GitHub (`v0.3.0`);
2. In [zenodo.org](https://zenodo.org), authorise the
   `liulinda185-spec/Carbon-Falcon` repository (once);
3. Re-publish or refresh the release so Zenodo creates the DOI;
4. Copy the DOI back here (`10.5281/zenodo.XXXXXXX`) and into the app's
   `DOI_URL` (tab 10 / footer).

Apache-2.0 · Built by Liu Yingge (Linda) for the OCIP project.
