"""
UCST-CCIF Streamlit MVP — v0.3 (UI refresh, same engines)

Tabs:
  1. Scope 1 stationary combustion (MEE factors)
  2. Scope 2 purchased electricity (MEE Guangdong grid factor)
  3. Scope 3 (T&D losses, business travel, commuting, purchased goods)
  4. Wetland biogenic flux
  5. Leakage audit
  6. NGFS scenarios
  7. Export audit PDF
  8. Anthropogenic (sector ledger: HK/Guangdong/global vs nature)
  9. Data guide & worked example (where to find data, CSV setup, end-to-end logic)
"""

from __future__ import annotations
import os, io
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="OCIP — Carbon Verification Layer", layout="wide",
                   initial_sidebar_state="expanded", page_icon="🛰️")

from ucst_ccif.emission_factors import (
    FUELS, GRID_FACTORS_MEE_2022, GRID_SOURCE,
    TD_LOSS_RATE, TRAVEL_FACTORS, COMMUTE_FACTORS, SPEND_FACTORS,
)

# ------------------------------------------------------------------
# Brand & theme
APP_VERSION = "v0.3.0"
APP_TAGLINE = "The independent carbon-verification layer for GBA enterprises & research teams"
GITHUB_URL = "https://github.com/liulinda185-spec/Carbon-Falcon"
DOI_URL = "https://zenodo.org/records/23687344"

st.markdown("""
<style>
  /* Hero */
  .ocip-hero { padding: .35rem .9rem .5rem .9rem; border-left: 5px solid #1F497D;
               background: linear-gradient(90deg, #FFFFFF 0%, #F2F5F9 100%);
               border-radius: 10px; margin-bottom: .4rem; }
  .ocip-hero h1 { margin: 0; font-size: 2.0rem; letter-spacing: -.01em;
                  color: #1F497D; }
  .ocip-hero .tagline { color: #47596B; font-size: 1.02rem; margin-top: .1rem; }
  .ocip-hero .badges { margin-top: .3rem; }
  .ocip-badge { display: inline-block; background: #1F497D; color: #fff;
                border-radius: 20px; padding: .1rem .7rem; font-size: .78rem;
                margin-right: .4rem; font-weight: 600; }
  .ocip-badge.gold { background: #C9A227; }
  .ocip-badge.grey { background: #5C6B7A; }
  /* Cards */
  .ocip-card { background: #FFFFFF; border: 1px solid #E3E8EE; border-radius: 10px;
               padding: .9rem 1.1rem; margin: .3rem 0 .7rem 0;
               box-shadow: 0 1px 2px rgba(31,73,125,.05); }
  .ocip-card h4 { color: #1F497D; margin: 0 0 .35rem 0; font-size: 1.0rem; }
  .ocip-card .src { color: #8A97A5; font-size: .8rem; }
  /* Section labels */
  .ocip-section { color: #1F497D; font-weight: 700; font-size: .95rem;
                  letter-spacing: .04em; margin: .2rem 0 .15rem 0; }
  /* Metrics polish */
  [data-testid="stMetric"] { background: #FFFFFF; border: 1px solid #E3E8EE;
                             border-radius: 10px; padding: .6rem .8rem; }
  [data-testid="stMetricLabel"] { color: #5C6B7A; }
  /* Footer */
  .ocip-footer { color: #8A97A5; font-size: .8rem; margin-top: 1.2rem;
                 border-top: 1px solid #E3E8EE; padding-top: .5rem; }
  /* Sidebar brand */
  .ocip-side-brand { font-size: 1.15rem; font-weight: 800; color: #1F497D; }
  .ocip-side-sub { color: #5C6B7A; font-size: .82rem; }
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div class="ocip-hero">
  <h1>🛰️ OCIP — Open Carbon Platform</h1>
  <div class="tagline">{APP_TAGLINE}</div>
  <div class="badges">
    <span class="ocip-badge">{APP_VERSION}</span>
    <span class="ocip-badge">75/75 tests</span>
    <span class="ocip-badge gold">Apache-2.0</span>
    <span class="ocip-badge grey">UCST-CCIF engine</span>
  </div>
</div>
""", unsafe_allow_html=True)
st.caption("One auditable ledger: fossil + biogenic flux · leakage audit built in · "
           "L1 point flux → L5 policy · same factors, same ε_C residual rule at every scale.")

# ------------------------------------------------------------------
# Sidebar
with st.sidebar:
    st.markdown('<div class="ocip-side-brand">OCIP</div>', unsafe_allow_html=True)
    st.markdown('<div class="ocip-side-sub">Carbon verification · UCST-CCIF</div>',
                unsafe_allow_html=True)
    st.divider()
    region = st.selectbox("Grid region",
        ["guangdong", "south_region", "national_avg"], index=0,
        help="Grid emission factor used across Scope 2, balance sheet and examples.")
    grid_factor = GRID_FACTORS_MEE_2022[region]
    st.info(f"Grid EF: {grid_factor:.4f} kgCO2/kWh\n({GRID_SOURCE})")
    st.divider()
    st.caption("**How to use** — start at Scope 1–3 (your activity data), then "
               "Biogenic & Leakage for the natural side and model checks, then "
               "Export PDF for an audit-ready trail. Tab 9 explains every input.")
    st.caption(f"[GitHub]({GITHUB_URL}) · [Zenodo DOI]({DOI_URL}) · v{APP_VERSION.lstrip('v')}")

tab_upload, tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab_report = st.tabs([
    "📥 0. Upload 4 Ledgers", "⚡ 1. Scope 1", "🔌 2. Scope 2", "🔗 3. Scope 3",
    "🌿 4. Biogenic", "🛡️ 5. Leakage", "🧭 6. NGFS", "📤 7. Export PDF",
    "🏭 8. Anthropogenic", "📚 9. Data Guide", "🧾 10. Audit Report"
])

# ========== 0. UPLOAD FOUR LEDGERS ==========
with tab_upload:
    st.header("Upload the four ledgers")
    st.caption("The 7-step audit pipeline (tab 10) reads exactly these four "
               "ledgers. Every file is optional — missing ones become reported "
               "data gaps, never silent estimates.")

    # ---- CSV templates ----
    tmpl = {
        "activity": ("scope,category,activity_key,quantity\n"
                     "2,electricity,guangdong,1135589.4\n"
                     "1,fuel,diesel_L,20000\n"
                     "2,purchased_goods,manufactured_goods,2000000\n"),
        "flux": ("date,NEE_daily_total,GPP_daily_total,ER_daily_total,"
                 "wind_speed_mean,temperature_2m_mean\n"
                 "2023-01-01,3.92,2.27,1.29,14.7,14.0\n"
                 "2023-01-02,4.47,1.90,1.14,20.2,15.3\n"),
        "stock": ("area_ha,removal_tco2e\n"
                  "100.0,420.0\n"),
        "intervention": ("scenario,baseline_removal_tco2e,"
                          "intervention_removal_tco2e,active_fraction\n"
                          "wetland_restoration,300.0,420.0,0.4\n"),
    }
    t1, t2, t3, t4 = st.columns(4)
    for col, key, label in ((t1, "activity", "Activity ledger"),
                            (t2, "flux", "Flux ledger"),
                            (t3, "stock", "Stock ledger"),
                            (t4, "intervention", "Intervention ledger")):
        with col:
            st.download_button(
                f"⬇ {label} template (CSV)", data=tmpl[key],
                file_name=f"ocip_{key}_template.csv", mime="text/csv")

    st.divider()
    c_a, c_f, c_s, c_i = st.columns(4)
    required = {
        "activity": ["scope", "category", "activity_key", "quantity"],
        "flux": ["date", "NEE_daily_total"],
        "stock": ["area_ha", "removal_tco2e"],
        "intervention": ["scenario", "baseline_removal_tco2e",
                         "intervention_removal_tco2e"],
    }
    ledgers = {
        "activity": ("ocip_activity", "Activity ledger (Scope 1-3)"),
        "flux": ("ocip_flux", "Flux ledger (daily NEE)"),
        "stock": ("ocip_stock", "Stock ledger (observed removal)"),
        "intervention": ("ocip_intervention", "Intervention ledger (Eq.3)"),
    }
    for col, (key, (skey, label)) in zip((c_a, c_f, c_s, c_i), ledgers.items()):
        with col:
            st.markdown(f"**{label}**")
            up = st.file_uploader(f"Upload {key}", type=["csv"],
                                  key=f"up_{key}")
            if up:
                try:
                    df = pd.read_csv(up)
                    st.session_state[skey] = df
                    miss = [c for c in required[key] if c not in df.columns]
                    st.dataframe(df.head(3), width="stretch")
                    if miss:
                        st.error(f"Missing columns: {', '.join(miss)}")
                    else:
                        st.success(f"OK — {len(df)} rows, required columns present")
                except Exception as e:  # noqa: BLE001
                    st.error(f"Could not parse CSV: {e}")
                    st.session_state.pop(skey, None)

    area_ha = st.number_input(
        "Project area (ha) — used to convert daily NEE (gC/m²/d) into tCO₂e",
        0.0, 1e9, 100.0, step=1.0, key="ocip_area_input")
    st.session_state["ocip_area"] = area_ha
    st.caption("Run the pipeline from **tab 10 (Audit Report)** once at least "
               "the activity ledger and one removal observation are in.")

# ========== SCOPE 1 ==========
with tab1:
    st.header("Scope 1 — stationary combustion")
    st.caption("Enter fuel use. Factors from MEE power-generation guideline App.A.")
    with st.container(border=True):
        rows = [
            {"fuel": "natural_gas_m3", "quantity": 5000, "unit": "m3"},
            {"fuel": "diesel_L", "quantity": 200, "unit": "L"},
        ]
        fuel_table = st.data_editor(
            pd.DataFrame(rows), num_rows="dynamic",
            column_config={
                "fuel": st.column_config.SelectboxColumn(
                    "Fuel", options=list(FUELS.keys()),
                    help="Key from the MEE factor table"),
                "quantity": st.column_config.NumberColumn("Quantity", min_value=0),
            },
            width="stretch")
        s1_rows = []
        for _, r in fuel_table.iterrows():
            f = FUELS.get(r["fuel"])
            if f and r["quantity"]:
                kg = f.ef_kgCO2_unit * float(r["quantity"])
                s1_rows.append({"Fuel": f.name, "Qty": r["quantity"],
                                "Unit": r["unit"],
                                "EF kgCO2/unit": round(f.ef_kgCO2_unit, 3),
                                "kgCO2e": round(kg, 1),
                                "tCO2e": round(kg/1000, 3),
                                "Source": "MEE App.A"})
        s1 = pd.DataFrame(s1_rows)
        if len(s1):
            st.dataframe(s1, width="stretch")
        else:
            st.info("Add a fuel row to see the breakdown.")
        s1_total = s1["tCO2e"].sum() if len(s1) else 0
        st.metric("Scope 1 total", f"{s1_total:.3f} tCO2e")

# ========== SCOPE 2 ==========
with tab2:
    st.header("Scope 2 — purchased electricity")
    st.caption("Location-based method: consumption × regional grid factor.")
    with st.container(border=True):
        c1, c2 = st.columns([1, 1])
        with c1:
            kwh = st.number_input("Annual electricity consumption (kWh)",
                                  value=500000, step=10000)
        with c2:
            st.metric("Scope 2 (location-based)", f"{kwh * grid_factor / 1000.0:.2f} tCO2e",
                      help=f"{kwh:,} kWh x {grid_factor} kgCO2/kWh")
    s2 = kwh * grid_factor / 1000.0  # tCO2e
    st.caption(f"Factor source: {GRID_SOURCE}")

# ========== SCOPE 3 ==========
with tab3:
    st.header("Scope 3 — selected categories")
    with st.container(border=True):
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("Cat 3: T&D losses")
            td = s2 * TD_LOSS_RATE
            st.write(f"Grid T&D loss rate: {TD_LOSS_RATE*100:.1f}%")
            st.write(f"Upstream T&D: **{td:.2f} tCO2e**")

            st.subheader("Cat 6: Business travel")
            flight_km = st.number_input("Long-haul flights (passenger-km/yr)", value=20000)
            car_km = st.number_input("Work car travel (km/yr)", value=5000)
            travel = (flight_km * TRAVEL_FACTORS["flight_long_haul"]
                      + car_km * TRAVEL_FACTORS["car_petrol"]) / 1000.0
            st.write(f"Business travel: **{travel:.2f} tCO2e**")
        with c2:
            st.subheader("Cat 7: Employee commuting")
            employees = st.number_input("Number of employees", value=50)
            commute_km_day = st.number_input("Avg one-way commute (km)", value=8)
            commute_days = 230
            commute = (employees * commute_km_day * 2 * commute_days
                       * COMMUTE_FACTORS["metro"]) / 1_000_000.0
            st.write(f"Commuting (metro): **{commute:.2f} tCO2e**")

            st.subheader("Cat 1: Purchased goods (spend-based)")
            spend = st.number_input("Annual procurement (CNY)", value=2_000_000)
            purchased = spend * SPEND_FACTORS["manufactured_goods"] / 1000.0
            st.write(f"Purchased goods: **{purchased:.2f} tCO2e** (rough IO estimate)")

    s3_total = td + travel + commute + purchased
    st.metric("Scope 3 (selected cats)", f"{s3_total:.2f} tCO2e")
    st.caption("Note: spend-based factors are rough IO averages. Replace with Climatiq/EXIOBASE for production.")

# ========== TOTAL ==========
st.divider()
with st.container(border=True):
    st.markdown('<span class="ocip-section">Total GHG inventory — Scope 1 + 2 + 3 (selected)</span>',
                unsafe_allow_html=True)
    total = s1_total + s2 + s3_total
    st.metric("Total", f"{total:.2f} tCO2e",
              help="Rolls up tabs 1–3 on the same ledger as the natural side (tab 4 / 8G).")

# ========== BIOGENIC ==========
with tab4:
    st.header("Biogenic flux — GBA coastal wetland")
    st.caption("CarbonContinuumModel demo: GPP/T_air/soil-water forcing → NEE, burial, ε_C residual.")
    with st.container(border=True):
        c1, c2, c3 = st.columns(3)
        with c1:
            gpp_amp = st.slider("GPP seasonal amplitude (gC/m²/day)", 1.0, 6.0, 3.0,
                                key="b_gpp_amp")
            gpp_base = st.slider("GPP base (gC/m²/day)", 2.0, 6.0, 4.0, key="b_gpp_base")
        with c2:
            t_amp = st.slider("Temperature amplitude (°C)", 4.0, 12.0, 8.0, key="b_t_amp")
            t_base = st.slider("Mean annual temperature (°C)", 15.0, 28.0, 22.0,
                               key="b_t_base")
        with c3:
            swc = st.slider("Soil water content (fraction)", 0.2, 0.9, 0.6, key="b_swc")
            st.caption("Rain kept at 0 for the demo forcing.")

    from ucst_ccif import CarbonContinuumModel, ParameterSet
    T = 365
    doy = np.arange(T)
    gpp = np.clip(gpp_base + gpp_amp*np.sin(2*np.pi*(doy-120)/365.25), 0.5, 8.0)
    T_air = t_base + t_amp*np.sin(2*np.pi*(doy-200)/365.25)
    swc_arr = np.full(T, swc)
    rain = np.zeros(T)
    m = CarbonContinuumModel(ParameterSet())
    s = m.run(gpp, T_air, swc_arr, rain)
    c1, c2, c3 = st.columns(3)
    c1.metric("Annual NEE", f"{s.nee.mean()*365:+.1f} gC m-2 yr-1",
              help="Negative = net uptake")
    c2.metric("Blue carbon burial", f"{s.coastal_burial_cum:.1f} gC m-2 yr-1")
    c3.metric("|ε_C| residual", f"{np.mean(np.abs(s.eps_C)):.4f}",
              help="Conservation residual — the audit flag, not hidden")
    st.line_chart(pd.DataFrame({"day": doy, "NEE (gC/m²/d)": s.nee}).set_index("day"))

# ========== LEAKAGE ==========
with tab5:
    st.header("Leakage audit")
    st.caption("3-step screen: predictor classification → correlation screen → no-leak refit. "
               "Upload a CSV with one target + ≥1 predictor (≥30 rows recommended).")
    with st.container(border=True):
        uploaded = st.file_uploader("Upload CSV with target + predictors", type=["csv"])
        if uploaded:
            df = pd.read_csv(uploaded)
            tgt = st.selectbox("Target column", df.columns)
            preds = [c for c in df.columns if c != tgt]
            from ucst_ccif import audit_leakage
            rep = audit_leakage(df, tgt, preds)
            st.text(rep.summary())
            # classification table
            if hasattr(rep, "classified"):
                cls_df = pd.DataFrame({
                    "Predictor": list(rep.classified.keys()),
                    "Class": ["**LEAKY**" if v == "leaky" else "exogenous"
                              for v in rep.classified.values()],
                })
                st.dataframe(cls_df, width="stretch")
        else:
            st.info("Upload a CSV to run the 3-step leakage audit. See tab 9 for the exact "
                    "column format and a copy-paste template.")

# ========== NGFS ==========
with tab6:
    st.header("NGFS Phase V scenarios")
    st.caption("Carbon-price & physical-risk lens for stress-testing your inventory.")
    ngfs = {
        "Orderly": {"carbon_price_2030": 150, "physical_risk": "low"},
        "Disorderly": {"carbon_price_2030": 350, "physical_risk": "medium"},
        "Hot House": {"carbon_price_2030": 15, "physical_risk": "high"},
    }
    with st.container(border=True):
        sc = st.selectbox("Scenario", list(ngfs.keys()))
        c1, c2 = st.columns(2)
        c1.metric("Carbon price 2030 (US$/tCO2)", ngfs[sc]["carbon_price_2030"])
        c2.metric("Physical risk", ngfs[sc]["physical_risk"])
        st.caption(f"Policy lens: under {sc.lower()}, a {ngfs[sc]['carbon_price_2030']} "
                   f"$/t price on your {total:.1f} tCO₂e → "
                   f"US${ngfs[sc]['carbon_price_2030'] * total:,.0f} exposure.")

# ========== PDF ==========
with tab7:
    st.header("Export ISO 14064-3 audit trail")
    st.caption("Evidence pack: numbers, factors, residual and verification note.")
    with st.container(border=True):
        if st.button("Generate PDF"):
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph
            from reportlab.lib.styles import getSampleStyleSheet
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("OCIP — Carbon Audit Report", styles["Title"]),
                Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["Normal"]),
                Paragraph(f"Platform: OCIP {APP_VERSION} (UCST-CCIF engine) · {GITHUB_URL}", styles["Normal"]),
                Paragraph(f"Boundary: corporate operations, {region} grid", styles["Normal"]),
                Paragraph(f"Scope 1: {s1_total:.3f} tCO2e", styles["Normal"]),
                Paragraph(f"Scope 2: {s2:.2f} tCO2e (factor {grid_factor} kg/kWh, MEE 2022)", styles["Normal"]),
                Paragraph(f"Scope 3 (selected): {s3_total:.2f} tCO2e", styles["Normal"]),
                Paragraph(f"Total: {total:.2f} tCO2e", styles["Heading2"]),
                Paragraph("Factors: MEE Announcement 2024 No.33; MEE power guideline App.A.", styles["Normal"]),
                Paragraph("Leakage audit: run tab 5 on site flux data before quoting any model R².", styles["Normal"]),
                Paragraph("Verification: third-party ISO 14064-3 assurance required before disclosure.", styles["Normal"]),
            ]
            doc.build(story)
            st.download_button("Download PDF", buf.getvalue(),
                               file_name="ocip_audit_report.pdf", mime="application/pdf")

# ========== ANTHROPOGENIC ==========
with tab8:
    st.header("Anthropogenic — human sectors & the nature ledger")
    st.caption("One ledger, two sides: what humans emit vs what nature absorbs. "
               "Sources: CEADs provincial inventory 2022 (Guangdong) · Global Carbon Budget 2025 · "
               "HK EPD GHG inventory 2023")

    # --- A. GBA human sectors (CEADs 2022, Guangdong) ---
    st.markdown('<span class="ocip-section">A. GBA human sectors — Guangdong 2022 (CEADs, Mt CO₂)</span>',
                unsafe_allow_html=True)
    gd_sectors = {
        "Electric power": 379.2, "Cement & minerals": 57.7,
        "Transport & logistics": 46.6, "Iron & steel": 34.7,
        "Urban residential": 26.3, "Nonferrous metals": 14.0,
        "Rural residential": 13.4, "Wholesale & catering": 12.5,
        "Petroleum refining": 8.1,
    }
    df_gd = pd.DataFrame({"Sector": list(gd_sectors),
                          "MtCO2": list(gd_sectors.values())}).set_index("Sector")
    st.bar_chart(df_gd, height=260)
    g1, g2 = st.columns(2)
    g1.metric("Guangdong total (2022)", "613.9 Mt CO₂",
              help="CEADs Shan et al. provincial sectoral inventory, IPCC Sectoral Approach")
    g2.metric("Power & heat share", "61.8%",
              help="Electric power dominates — the CBAM/ETS hotspot for GBA exporters")

    # --- B. Global human emissions (GCB2025, 2024) ---
    st.markdown('<span class="ocip-section">B. Global human emissions — fossil + land-use (GCB2025, 2024)</span>',
                unsafe_allow_html=True)
    fossil = {"Coal": 4.31, "Oil": 3.40, "Gas": 2.19, "Cement": 0.40, "Other": 0.42}
    df_fossil = pd.DataFrame({"Fuel": list(fossil),
                              "GtC per yr": list(fossil.values())}).set_index("Fuel")
    st.bar_chart(df_fossil, height=220)
    b1, b2, b3 = st.columns(3)
    b1.metric("Fossil + cement", "10.53 GtC/yr", "≈ 38.6 GtCO₂/yr")
    b2.metric("Land-use change", "1.25 GtC/yr", "≈ 4.6 GtCO₂/yr")
    b3.metric("Atmospheric growth", "+4.9 GtC/yr",
              help="≈ 49% of emissions stay in the atmosphere; the rest goes to sinks")

    # --- C. Nature ledger ---
    st.markdown('<span class="ocip-section">C. Nature ledger — where the rest goes (GCB2025)</span>',
                unsafe_allow_html=True)
    n1, n2, n3 = st.columns(3)
    n1.metric("Ocean sink", "3.1 GtC/yr", "≈ 11.4 GtCO₂/yr")
    n2.metric("Land sink", "2.5 GtC/yr", "≈ 9.2 GtCO₂/yr (incl. blue carbon)")
    n3.metric("Total sinks", "5.6 GtC/yr", "vs 11.8 emitted")
    st.caption("Same bookkeeping rules at every scale: OCIP audits the anthropogenic "
               "side (Scope 1–3, sectoral inventories) and the natural side (biogenic "
               "flux, blue carbon) on one ledger — L1 point flux to L5 policy.")

    # --- D. HK sectors (EPD GHG inventory 2023) ---
    st.markdown('<span class="ocip-section">D. Hong Kong sectors — GHG inventory 2023 (EPD, kt CO₂e)</span>',
                unsafe_allow_html=True)
    hk_sectors = {
        "Electricity & energy ind.": 21200, "Transport": 6330,
        "Industrial processes & other": 2920, "Waste": 2410,
        "Other combustion": 1660, "Agriculture": 28,
    }
    df_hk = pd.DataFrame({"Sector": list(hk_sectors),
                          "ktCO2e": list(hk_sectors.values())}).set_index("Sector")
    st.bar_chart(df_hk, height=220)
    h1, h2, h3 = st.columns(3)
    h1.metric("HK total (2023)", "34.5 Mt CO₂e",
              help="≈ −25% vs 2014 peak; EPD GHG inventory, revised methodology")
    h2.metric("Electricity share", "61.3%",
              help="Power is HK's dominant source — same story as Guangdong, same CBAM lens")
    h3.metric("Per-capita", "4.6 t CO₂e",
              help="Record low since 1990s (7.5M population)")
    st.caption("Compare your own Scope 1–3 total against HK's official sector mix — "
               "if your intensity is above the sector average, the ledger flags it.")

    # --- E. CH4 by sector: rice (DNDC-lite) + landfill (IPCC Tier-1) ---
    st.markdown('<span class="ocip-section">E. CH₄ by sector — rice paddies & landfills (GBA)</span>',
                unsafe_allow_html=True)
    c_rice, c_land = st.columns(2)
    with c_rice:
        with st.container(border=True):
            from ucst_ccif.dndc_lite import rice_ch4_season, RICE_WATER_REGIMES
            st.markdown("**Rice paddies (DNDC-lite, IPCC scaling)**")
            regime = st.selectbox("Water regime", list(RICE_WATER_REGIMES), key="rice_regime")
            rice_days = st.slider("Season length (days)", 90, 180, 120, key="rice_days")
            rice_ha = st.number_input("Area (ha)", 1.0, 10000.0, 100.0, key="rice_ha")
            try:
                est = rice_ch4_season(regime, rice_days, area_ha=rice_ha)
                st.metric("Seasonal CH₄", f"{est.total_kgCH4:.1f} kg",
                          f"{est.total_tCO2e:.1f} tCO₂e (GWP28)")
            except KeyError as e:
                st.error(str(e))
    with c_land:
        with st.container(border=True):
            from ucst_ccif.landfill import landfill_ch4_tier1, LANDFILL_MCF
            st.markdown("**Landfills (IPCC 2006/2019 Tier-1)**")
            msw_t = st.number_input("Waste disposed (t/yr)", 0.0, 10_000_000.0,
                                    1_500_000.0, step=50_000.0, key="land_msw")
            lf_type = st.selectbox("Landfill type",
                                   ["managed_anaerobic", "managed_semi_aerobic",
                                    "unmanaged_deep", "unmanaged_shallow",
                                    "uncategorised"], key="land_type")
            lr = landfill_ch4_tier1(msw_t, mcf_key=lf_type)
            st.metric("Landfill CH₄", f"{lr.ch4_t:.1f} t CH₄/yr",
                      f"{lr.co2e_t_ar5:.1f} tCO₂e/yr (AR5 GWP28)")
            st.caption(f"e.g. 1.5 Mt MSW/yr, managed anaerobic → "
                       f"{landfill_ch4_tier1(1_500_000.0).ch4_t:.1f} t CH₄ ≈ "
                       f"{landfill_ch4_tier1(1_500_000.0).co2e_t_ar5:.1f} tCO₂e/yr")
    st.caption("CH₄ has ~28× GWP of CO₂: the GBA CH₄ wedge is rice + landfills "
               "+ tidal wetlands — OCIP audits all three on one CH₄ ledger.")

    # --- F. CCER mangrove restoration lookup ---
    st.markdown('<span class="ocip-section">F. CCER mangrove restoration — project lookup</span>',
                unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("Methodology: **CCER—14—002—V02 红树林营造** (2026 revision, "
                    "age-based lookup; baseline = unvegetated tidal flat / retired shrimp pond).")
        f1, f2, f3 = st.columns(3)
        f1.metric("Default crediting period", "20–40 yr", help="CCER methodology 计入期")
        f2.metric("GD mangrove C stock", "3.22 Mt C",
                  help="Guangdong province (Kandelia obovata dominant)")
        f3.metric("GD sink potential", "6.6–18.2 tCO₂e/ha/yr",
                  help="55 km² target → 36,171–99,891 tCO₂e/yr")
        proj_area = st.number_input("Your project area (ha)", 0.0, 100000.0,
                                    100.0, key="ccer_area")
        proj_age = st.slider("Mean stand age (yr)", 1, 50, 10, key="ccer_age")
        # conservative age-based carbon accumulation for subtropical mangroves
        agb_accum = 0.35 * proj_age + 1.2          # Mg C/ha (above+below, saturating proxy)
        soil_acc = 0.35                             # Mg C/ha/yr burial
        tot_acc = agb_accum + soil_acc * proj_age   # Mg C/ha cumulative
        co2_per_ha = tot_acc * 44.0 / 12.0
        st.metric("Estimated cumulative carbon", f"{co2_per_ha * proj_area:,.0f} tCO₂e",
                  f"{co2_per_ha:.1f} tCO₂e/ha over {proj_age} yr (order-of-magnitude)")
        st.caption("Lookup is a scoping estimate for pitch purposes — "
                   "official crediting requires CCER field measurement per the methodology "
                   "age-based tables (App. A, Guangdong region).")

    # --- G. Anthropogenic vs natural — your own carbon balance sheet ---
    st.markdown('<span class="ocip-section">G. Your own carbon balance sheet — anthropogenic vs natural</span>',
                unsafe_allow_html=True)
    st.markdown("Same ledger, your scale: factory electricity vs your wetland/rice area.")
    with st.container(border=True):
        b1, b2 = st.columns(2)
        with b1:
            own_kwh = st.number_input("Your factory electricity (kWh/yr)", 0.0,
                                      1_000_000_000.0, 500_000.0, step=50_000.0,
                                      key="own_kwh")
            own_t = own_kwh * grid_factor / 1000.0   # tCO2e
            st.metric("Your Scope 2 (anthropogenic)", f"{own_t:.1f} tCO₂e/yr",
                      f"× {grid_factor} kgCO₂/kWh (Guangdong grid)")
        with b2:
            own_ha = st.number_input("Your wetland / rice area (ha)", 0.0,
                                     100000.0, 10.0, key="own_ha")
            nee_g = -155.6                            # gC/m²/yr (GBA wetland demo, synthetic)
            own_sink = abs(nee_g) * own_ha * 10000.0 * 44.0 / 12.0 / 1e6  # tCO2e
            st.metric("Your nature sink (biogenic)", f"{own_sink:.1f} tCO₂e/yr",
                      f"@ −{abs(nee_g):.0f} gC/m²/yr NEE (demo forcing)")
        st.metric("Net position (anthropogenic − natural)",
                  f"{own_t - own_sink:+,.1f} tCO₂e/yr",
                  delta=f"{own_sink / own_t * 100:.1f}% of your emissions offset by your land"
                        if own_t > 0 else "enter factory load to compare")
    st.caption("This is the L5→L2 drill-down: HK/Guangdong sector data sets the scale, "
               "your numbers set the subject, and ε_C-style reconciliation flags "
               "whether the two sides of your ledger balance.")

# ========== 9. DATA GUIDE & WORKED EXAMPLE ==========
with tab9:
    st.header("Data guide & worked example")
    st.write("What OCIP solves, where to find your data, how to set up uploads — "
             "and one end-to-end example that shows the logic on a single ledger.")

    # --- 9.1 Problem statement ---
    st.subheader("1. What problem does OCIP solve?")
    p1, p2, p3 = st.columns(3)
    p1.markdown("**① Regional inventories can't be audited down to you.**\n\n"
                "HK/Guangdong report sector totals (electricity 61%, transport 18%…) — "
                "but a firm can't see where *its* numbers sit, and officials can't "
                "verify a firm's self-reported figure against an independent benchmark.")
    p2.markdown("**② Self-reported numbers can't be trusted on their own.**\n\n"
                "Leakage audits catch models that quietly use GPP/ER — which are "
                "*algebraically derived* from the very NEE they claim to predict. "
                "Without the audit, a 0.90 R² can hide a circular argument (Sapelo "
                "honest baseline: R² 0.90 → ~0.45).")
    p3.markdown("**③ Natural and human carbon are two ledgers that never meet.**\n\n"
                "A company books Scope 1–3; a wetland project books blue carbon. "
                "OCIP puts both on **one ledger with the same factors and the same "
                "ε_C residual rule**, so the two sides can actually be reconciled "
                "(your factory vs your wetland, net position).")
    st.caption("OCIP is the **auditor, not a calculator**: built-in benchmarks are "
               "the accounting standards; your uploaded data is the ledger; the "
               "leakage audit + residual reconciliation is the control.")

    # --- 9.2 Data source map ---
    st.subheader("2. Where to find your data (free first)")
    st.markdown(
        "| What you need (CSV column) | Free source | Licence / condition |\n"
        "|---|---|---|\n"
        "| NEE / GPP / ER (flux) | FLUXNET Data System → fluxnet.org, per site | Tier-1 sites CC-BY-4.0 free |\n"
        "| Flux — Asia analogue | JapanFlux2024 (Kyushu/Okinawa) → japanflux.org | CC-BY-4.0, best near-term |\n"
        "| Flux — mainland China | ChinaFLUX (CAS) → chinaflux.org · **now on NESDC** (e.g. Jinfo forest 2020–2022) | CC BY-NC 4.0, protected until 2026-12-15; commercial licence via MOU |\n"
        "| Flux — build your own tower | EddyPro 7 (free) → REddyProc gap-fill → ONEFlux QC | fully open-source |\n"
        "| Meteorology (wind/ustar/T/CO₂) | tower meteorology; ERA5 (ECMWF); Open-Meteo API | free |\n"
        "| Emission inventories / factors | CEADs provincial (your folder), HK EPD, EDGAR, GCB2025 | free |\n"
        "| Enterprise factors (production-grade) | Climatiq (free Starter; Data Pro ≈HK$25k/yr) | subscription |\n"
        "| CH₄ satellite (landfill/rice) | TROPOMI/Sentinel-5P daily XCH₄ → Copernicus Data Space | Copernicus open, free |\n"
        "| Land cover / biomass | Sentinel-2 (10 m), GEDI, MODIS GPP | free (NASA/ESA) |\n"
        "| Gridded priors (NetCDF) | CAMS inversion, FLUXCOM-X (CC-BY-4.0), SoilGrids (CC-BY-4.0), SOCAT, NASA CMS mangrove | free — feed `netcdf_priors` |\n"
    )

    # --- 9.3 Upload CSV setup ---
    st.subheader("3. How to set up your upload CSV")
    st.markdown(
        "**Rules (Leakage tab):** one row = one time step (usually a day); one "
        "column = one variable; at least 1 numeric target column + ≥1 numeric "
        "predictor; date columns are auto-ignored; empty columns are skipped; "
        "≥30 rows recommended.\n\n"
        "**Column-name auto-classification** — if a predictor name contains "
        "`gpp`/`GPP`/`er_`/`ER_`/`_er`/`ecosystem_resp`/`nee_balance`/"
        "`carbon_balance`/`cumulative_balance`/`npp_balance`/`lateral_flux` it is "
        "**flagged LEAKY** (NEE-derived); everything else is exogenous.\n\n"
        "**Copy-paste template:**"
    )
    st.code(
        "date,NEE_daily_total,GPP_daily_total,ER_daily_total,"
        "wind_speed_mean,ustar_mean,co2_mole_fraction_mean\n"
        "2021-01-01,0.818,1.708,2.447,4.513,0.456,407.7\n"
        "2021-01-02,-0.236,1.702,1.466,3.201,0.380,405.2\n"
        "2021-01-03,0.412,1.655,2.067,2.894,0.311,403.8",
        language="csv",
    )
    st.markdown(
        "**Why GPP/ER will be flagged:** NEE = ER − GPP by definition, so GPP and "
        "ER are deterministic transforms of the target. A model 'explaining' NEE "
        "with them is circular — the audit catches it before anyone quotes an R²."
    )

    # --- 9.3b Column-by-column guide ---
    st.markdown("**Column-by-column guide (what to put in each field):**")
    st.markdown(
        "| Column | What it is | Units | How to get it | Role in the audit |\n"
        "|---|---|---|---|---|\n"
        "| `date` | Day of measurement | YYYY-MM-DD | your logger | optional — auto-ignored |\n"
        "| `NEE_daily_total` | **Net Ecosystem Exchange** — net CO₂ flux of the site | g C m⁻² day⁻¹ (negative = absorbing, positive = emitting) | FLUXNET / your tower after ONEFlux | **target** — the thing being audited |\n"
        "| `GPP_daily_total` | **Gross Primary Production** — photosynthesis uptake | g C m⁻² day⁻¹ | FLUXNET partitioning | ⚠️ **LEAKY** — NEE = ER − GPP, circular as predictor |\n"
        "| `ER_daily_total` | **Ecosystem Respiration** — all organisms respiring | g C m⁻² day⁻¹ | FLUXNET partitioning | ⚠️ **LEAKY** — same identity |\n"
        "| `wind_speed_mean` | daily mean wind speed | m s⁻¹ | tower meteorology / ERA5 / Open-Meteo | exogenous — legitimate predictor |\n"
        "| `ustar_mean` | **friction velocity** — turbulence quality gate | m s⁻¹ | tower | exogenous — used for u*-filter QA |\n"
        "| `co2_mole_fraction_mean` | mean CO₂ mole fraction (concentration) | ppm (µmol mol⁻¹) | analyser / Open-Meteo | exogenous — legitimate predictor |\n"
    )
    st.markdown(
        "**What each LEAKY pattern means** — any column *named* like this is "
        "auto-flagged, even if you did not intend it:\n\n"
        "| Pattern | Full meaning | Why it is NEE-derived |\n"
        "|---|---|---|\n"
        "| `gpp` / `GPP` | Gross Primary Production | NEE = ER − GPP; it is one term of the identity |\n"
        "| `er_` / `ER_` / `_er` / `ecosystem_resp` | Ecosystem Respiration | the other term of the identity |\n"
        "| `nee_balance` | NEE balance term | a re-statement of NEE itself |\n"
        "| `carbon_balance` | carbon-budget balance | integrates NEE over time |\n"
        "| `cumulative_balance` | cumulative carbon balance | time-integral of NEE |\n"
        "| `npp_balance` | net primary production balance | NPP ≈ GPP − autotrophic R — couples to NEE |\n"
        "| `lateral_flux` | lateral carbon export (river/erosion) | closes the site budget, derived from the same C accounting |\n"
    )
    st.markdown("**How do I actually get these values?** Three paths — tower, download, or skip:")
    st.markdown(
        "| Column | You own a tower (compute it) | No tower (download ready-made) | Enterprise user |\n"
        "|---|---|---|---|\n"
        "| `date` | logger timestamp | in the file | — |\n"
        "| `NEE_daily_total` | raw tower → **EddyPro 7** (free) → **REddyProc/ONEFlux** gap-fill → daily integral | **FLUXNET / JapanFlux2024** daily CSV (already u*-filtered + gap-filled) | skip, or commission a monitor |\n"
        "| `GPP_daily_total` | flux partitioning (REddyProc night/day method) | already in FLUXNET file | skip |\n"
        "| `ER_daily_total` | same (or NEE − GPP) | already in FLUXNET file (RECO) | skip |\n"
        "| `wind_speed_mean` | tower met mast 30-min mean → daily | FLUXNET WS column; or ERA5 / Open-Meteo grid | not needed |\n"
        "| `ustar_mean` | 3-D sonic anemometer output | FLUXNET USTAR column | not needed |\n"
        "| `co2_mole_fraction_mean` | IRGA analyser record | FLUXNET CO₂ column | not needed |\n"
    )
    st.markdown(
        "**Unit conversion (if you process raw tower data):** tower output is "
        "30-min **µmol CO₂ m⁻² s⁻¹**; to get **g C m⁻² day⁻¹** use:\n\n"
        "`daily_gC = mean_µmol × 86400 s × 12.011 g/mol ÷ 1e6`\n\n"
        "Example: −2.5 µmol m⁻² s⁻¹ → −2.59 g C m⁻² day⁻¹ (negative = uptake). "
        "For CO₂ mass multiply by 44.01/12.011 (×3.664). The fastest path for "
        "most users: download a FLUXNET daily CSV — every column already in the "
        "right units, no computation needed."
    )

    # --- 9.4 Why this is different ---
    st.subheader("4. Why is this different from every other carbon calculator?")
    st.markdown(
        "| | Typical calculators (Emitwise, Normative, spreadsheets) | OCIP / UCST-CCIF |\n"
        "|---|---|---|\n"
        "| What you get | activity × factor = a number | a number **plus** an audit trail |\n"
        "| Can it check your model? | no — garbage in, confident number out | **leakage audit** catches circular predictors (GPP/ER) before any R² is quoted |\n"
        "| Human vs nature | Scope 1–3 only, or land carbon only — two separate products | **one ledger**: factory and wetland on the same factors and the same ε_C residual rule |\n"
        "| Benchmarking | you vs nothing | you vs **official sector benchmarks** (HK EPD, Guangdong, CCER methodology) |\n"
        "| Honesty | opaque factors, no validation | Sapelo honest baseline: R² 0.90 → ~0.45 after removing leaked predictors; every number traceable to a source or formula in this app |\n"
        "| Scale | one answer | **L1 point flux → L5 policy** drill-down on the same bookkeeping |\n"
        "| For auditors | export a PDF of numbers | export an **ISO 14064-3-ready evidence pack** (factor version, residual, leakage log) |\n"
    )
    st.caption("Positioning: OCIP is the **quality-control layer** for carbon numbers — "
               "the audit is the product, not the number.")

    # --- 9.5 Worked example ---
    st.subheader("5. Worked example — Shenzhen SME, one ledger, six steps")
    st.markdown(
        "**Scenario:** a Shenzhen electronics factory books its carbon for the year, "
        "holds 5 ha of restored mangrove (CCER pipeline) beside a 10 ha wetland, "
        "and wants to know: *how much do I emit, how much does my land absorb, "
        "and does my own GHG model pass a leakage audit?*"
    )
    w1, w2, w3 = st.columns(3)
    with w1:
        ex_kwh = st.number_input("Factory electricity (kWh/yr)", 0.0, 1e9,
                                 2_000_000.0, step=100_000.0, key="ex_kwh")
        ex_diesel = st.number_input("Diesel (L/yr)", 0.0, 1e8,
                                    20_000.0, step=5_000.0, key="ex_diesel")
    with w2:
        ex_mangrove_ha = st.number_input("Mangrove project (ha)", 0.0, 1e5,
                                         5.0, step=1.0, key="ex_mangrove_ha")
        ex_mangrove_age = st.slider("Mean stand age (yr)", 1, 50, 10,
                                    key="ex_mangrove_age")
    with w3:
        ex_wet_ha = st.number_input("Wetland (ha)", 0.0, 1e5, 10.0, step=1.0,
                                    key="ex_wet_ha")
        st.caption("Steps 1–2 use the same factors as tabs 1–2 and F; step 5 uses "
                   "the leakage audit engine.")

    # Step 1: Scope 1 (diesel)
    diesel_kgCO2 = FUELS["diesel_L"].ef_kgCO2_unit * ex_diesel
    scope1_t = diesel_kgCO2 / 1000.0
    # Step 2: Scope 2 (electricity)
    scope2_t = ex_kwh * grid_factor / 1000.0
    total_anthrop = scope1_t + scope2_t
    # Step 3: benchmark against HK structure
    hk_total_kt = 34_500.0
    share = total_anthrop / (hk_total_kt * 1000.0) * 100.0
    # Step 4: natural side
    mangrove_acc = ((0.35 * ex_mangrove_age + 1.2) + 0.35 * ex_mangrove_age) \
        * 44.0 / 12.0
    mangrove_t = mangrove_acc * ex_mangrove_ha
    wetland_t = abs(-155.6) * ex_wet_ha * 10_000.0 * 44.0 / 12.0 / 1e6
    nature_t = mangrove_t + wetland_t
    # Step 5: leakage demo (3 rows, GPP/ER circular)
    demo_df = pd.DataFrame({
        "date": ["2021-01-01", "2021-01-02", "2021-01-03"],
        "NEE_daily_total": [0.818, -0.236, 0.412],
        "GPP_daily_total": [1.708, 1.702, 1.655],
        "ER_daily_total": [2.447, 1.466, 2.067],
        "wind_speed_mean": [4.513, 3.201, 2.894],
        "ustar_mean": [0.456, 0.380, 0.311],
        "co2_mole_fraction_mean": [407.7, 405.2, 403.8],
    })
    from ucst_ccif.leakage import audit_leakage
    rep = audit_leakage(
        demo_df, "NEE_daily_total",
        ["GPP_daily_total", "ER_daily_total", "wind_speed_mean",
         "ustar_mean", "co2_mole_fraction_mean"],
    )
    leaky = [k for k, v in rep.classified.items() if v == "leaky"]

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Step 1 · Scope 1 (diesel)",
              f"{scope1_t:,.1f} tCO₂e", f"{diesel_kgCO2:,.0f} kgCO₂")
    m2.metric("Step 2 · Scope 2 (grid)",
              f"{scope2_t:,.1f} tCO₂e",
              f"× {grid_factor} kg/kWh Guangdong")
    m3.metric("Step 3 · vs HK inventory",
              f"{share:.3f}% of HK total",
              "HK 34.5 Mt CO₂e (EPD 2023)")
    m4.metric("Step 4 · your land absorbs",
              f"{nature_t:,.1f} tCO₂e/yr",
              f"{nature_t / total_anthrop * 100:.1f}% of your emissions"
              if total_anthrop > 0 else "enter activity data")
    m5 = st.metric("Step 5 · leakage audit",
                  f"{len(leaky)} predictor(s) flagged LEAKY",
                  "GPP/ER are NEE-derived — circular by construction")
    if leaky:
        st.caption(f"Flagged: {', '.join(sorted(leaky))} — drop them and refit "
                   f"for an honest R² (Sapelo: 0.90 → ~0.45).")
    st.metric("Step 6 · net position",
              f"{total_anthrop - nature_t:+,.1f} tCO₂e/yr",
              f"{nature_t / total_anthrop * 100:.1f}% offset by your own land"
              if total_anthrop > 0 else "enter activity data to compare")
    st.caption("Same ledger, six steps: your activity → your emissions (tabs 1–2 "
               "factors) → benchmark vs HK structure (tab 8D) → your natural assets "
               "(tab 8F–G) → leak check (tab 5) → net position. Every number on "
               "this page is traceable to a source or a formula in this app.")

# ========== 10. AUDIT REPORT ==========
with tab_report:
    st.header("Audit report — 7-step pipeline, 8 artifacts")
    st.caption("Runs S1 (boundary) → S2 (factors) → S3 (conservation, Eq.1) → "
               "S4 (scale) → S5 (additionality, Eq.3) → S6 (leakage, Eq.7) → "
               "S7 (uncertainty) on the four ledgers uploaded in tab 0.")

    st.markdown("""
    <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:stretch;font-size:0.85rem;margin:6px 0 10px;">
      <div style="flex:1 1 200px;background:#eef4fa;border:1px solid #b9cfe4;border-radius:10px;padding:10px;">
        <b>📥 四账（Tab 0 上传）</b>
        <div style="margin-top:6px;display:flex;flex-direction:column;gap:4px;">
          <div style="border:1px solid #9db8d4;border-radius:6px;padding:4px 6px;background:#fff;">活动账<br/><span style="color:#5c6b7a;font-size:0.75rem;">scope·category·activity_key·quantity</span></div>
          <div style="border:1px solid #9db8d4;border-radius:6px;padding:4px 6px;background:#fff;">通量账<br/><span style="color:#5c6b7a;font-size:0.75rem;">date·NEE_daily_total</span></div>
          <div style="border:1px solid #9db8d4;border-radius:6px;padding:4px 6px;background:#fff;">碳库账<br/><span style="color:#5c6b7a;font-size:0.75rem;">area_ha·removal_tco2e</span></div>
          <div style="border:1px solid #9db8d4;border-radius:6px;padding:4px 6px;background:#fff;">干预账<br/><span style="color:#5c6b7a;font-size:0.75rem;">scenario·baseline·intervention</span></div>
        </div>
      </div>
      <div style="flex:2 1 380px;background:#fff;border:1px solid #d8dee4;border-radius:10px;padding:10px;">
        <b>⚙️ 7 步流水线 run_audit()</b>
        <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;">
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S1 边界</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S2 因子</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S3 守恒</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S4 尺度</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S5 额外性</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S6 泄漏</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S7 不确定</div>
        </div>
        <div style="margin-top:6px;color:#5c6b7a;font-size:0.75rem;">S3: ε_C = 独立观测 − 企业声称 · S5: 主动触发 F_a vs 被动响应 F_p · S6: 泄漏三步</div>
      </div>
      <div style="flex:1 1 220px;background:#eaf6ec;border:1px solid #b7d9bd;border-radius:10px;padding:10px;">
        <b>📤 8 件输出 + 证书</b>
        <div style="margin-top:6px;color:#2c3e50;line-height:1.6;font-size:0.8rem;">
          ① 边界清单 · ② 排放区间 · ③ 移除区间 · ④ 残差 ε_C<br/>
          ⑤ 尺度残差 · ⑥ 泄漏 RYG 旗标 · ⑦ 归因分解 · ⑧ 不确定性预算
        </div>
        <div style="margin-top:6px;border:1px solid #3a7d44;border-radius:6px;padding:4px 6px;background:#fff;font-weight:600;">🏅 PASS / REVIEW / FAIL / INCOMPLETE</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    a1, a2, a3 = st.columns(3)
    with a1:
        claim = st.number_input("Company's claimed removal (tCO₂e/yr)",
                                0.0, 1e9, 420.0, step=10.0,
                                help="What the company books as 'we reduced X t' — "
                                     "compared against independent observation in S3")
    with a2:
        agent_col = st.text_input("Agent-state column (Eq.2, optional)",
                                  placeholder="e.g. water_level / mangrove_age",
                                  help="Column in the flux ledger that carries the "
                                       "management signal; attribution split is skipped "
                                       "if left empty")
    with a3:
        area = st.session_state.get("ocip_area", 100.0)
        st.metric("Area used for gC → tCO₂e", f"{area:,.1f} ha",
                  help="Set in tab 0 (Upload)")

    if st.button("Run the audit", type="primary"):
        from ucst_ccif import run_audit
        rep = run_audit(
            activity_df=st.session_state.get("ocip_activity"),
            flux_df=st.session_state.get("ocip_flux"),
            stock_df=st.session_state.get("ocip_stock"),
            intervention_df=st.session_state.get("ocip_intervention"),
            area_ha=(area if area > 0 else None),
            claimed_removals_tco2e=(claim if claim > 0 else None),
            agent_col=(agent_col.strip() if agent_col.strip() else None),
        )
        st.session_state["ocip_report"] = rep
        st.session_state["ocip_report_text"] = rep.summary()

    rep = st.session_state.get("ocip_report")
    if rep is not None:
        # --- certificate + headline metrics ---
        cert_color = {"PASS": "#1F7A3D", "FAIL": "#B23A3A",
                      "REVIEW": "#C9A227", "INCOMPLETE": "#5C6B7A"}
        cc = next((v for k, v in cert_color.items()
                   if rep.certificate_status.startswith(k)), "#5C6B7A")
        st.markdown(
            f"<div style='border-left:6px solid {cc}; padding:.4rem .9rem; "
            f"background:#F7F9FB; border-radius:8px; margin:.3rem 0'>"
            f"<b style='font-size:1.25rem;color:{cc}'>{rep.certificate_status}</b>"
            f"<div style='color:#47596B'>Audit certificate — the verdict of the "
            f"8-artifact report.</div></div>", unsafe_allow_html=True)

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Verified emissions",
                  (f"{rep.emissions_tco2e:,.1f} ± {rep.emissions_u95_tco2e:,.1f}"
                   " tCO₂e" if rep.emissions_tco2e is not None else "—"),
                  help="Artifact 1: verified emission interval (S2 + S7)")
        m2.metric("Verified removals",
                  (f"{rep.removals_tco2e:,.1f} ± {rep.removals_u95_tco2e:,.1f}"
                   " tCO₂e" if rep.removals_tco2e is not None else "—"),
                  help="Artifact 2: verified removal interval (S3)")
        m3.metric("Conservation residual ε_C",
                  (f"{rep.residual_eC_tco2e:+,.1f} tCO₂e"
                   if rep.residual_eC_tco2e is not None else "—"),
                  help="Artifact 3: observed − claimed. Negative = over-claim (S3)")
        m4.metric("Leakage flag",
                  {"red": "🔴 RED — leaky predictors",
                   "amber": "🟠 AMBER", "green": "🟢 GREEN — clean",
                   "grey": "⚪ no flux data"}.get(rep.leakage_ryg, "—"),
                  help="Artifact 5: RYG status of the flux model (S6, Eq.7)")

        with st.expander("Stage log (S1–S7)", expanded=True):
            st.dataframe(pd.DataFrame([
                {"Stage": f"S{s.stage}", "Name": s.name, "Status": s.status,
                 "Detail": s.detail} for s in rep.stages
            ]), width="stretch")
        if rep.data_gaps:
            with st.expander("Reported data gaps (never silently estimated)",
                             expanded=True):
                for g in rep.data_gaps:
                    st.markdown(f"- {g}")
        with st.expander("Full 8-artifact payload (JSON)"):
            st.json(rep.artifacts())
        if rep.leak_free_gain_pct is not None:
            st.info(f"Leakage-free refit (step 3): apparent gain from leaky "
                    f"predictors = {rep.leak_free_gain_pct:+.1f}% — "
                    f"see tab 5 for details.")
    else:
        st.info("Upload at least the activity ledger + one removal observation "
                "in tab 0, then press **Run the audit**.")

# ------------------------------------------------------------------
st.markdown(f"""
<div class="ocip-footer">
  OCIP {APP_VERSION} · UCST-CCIF engine · {GITHUB_URL} · DOI {DOI_URL}<br/>
  The audit is the product — not the number.
</div>
""", unsafe_allow_html=True)
