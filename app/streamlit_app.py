"""
UCST-CCIF Streamlit MVP — v0.2

Tabs:
  1. Scope 1 stationary combustion (MEE factors)
  2. Scope 2 purchased electricity (MEE Guangdong grid factor)
  3. Scope 3 (T&D losses, business travel, commuting, purchased goods)
  4. Wetland biogenic flux
  5. Leakage audit
  6. NGFS scenarios
  7. Export audit PDF
"""

from __future__ import annotations
import os, io
from datetime import datetime
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(page_title="UCST-CCIF Carbon Calculator", layout="wide",
                   initial_sidebar_state="expanded")

from ucst_ccif.emission_factors import (
    FUELS, GRID_FACTORS_MEE_2022, GRID_SOURCE,
    TD_LOSS_RATE, TRAVEL_FACTORS, COMMUTE_FACTORS, SPEND_FACTORS,
)

# ------------------------------------------------------------------
st.sidebar.title("UCST-CCIF")
st.sidebar.caption("Conservation-constrained carbon accounting")
region = st.sidebar.selectbox("Grid region",
    ["guangdong", "south_region", "national_avg"], index=0)
grid_factor = GRID_FACTORS_MEE_2022[region]
st.sidebar.info(f"Grid EF: {grid_factor:.4f} kgCO2/kWh\n({GRID_SOURCE})")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
    "1. Scope 1", "2. Scope 2", "3. Scope 3",
    "4. Biogenic", "5. Leakage", "6. NGFS", "7. Export PDF"
])

# ========== SCOPE 1 ==========
with tab1:
    st.header("Scope 1 — stationary combustion")
    st.write("Enter fuel use. Factors from MEE power-generation guideline App.A.")
    rows = [
        {"fuel": "natural_gas_m3", "quantity": 5000, "unit": "m3"},
        {"fuel": "diesel_L", "quantity": 200, "unit": "L"},
    ]
    fuel_table = st.data_editor(pd.DataFrame(rows), num_rows="dynamic")
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
    st.dataframe(s1, use_container_width=True)
    s1_total = s1["tCO2e"].sum() if len(s1) else 0
    st.metric("Scope 1 total", f"{s1_total:.3f} tCO2e")

# ========== SCOPE 2 ==========
with tab2:
    st.header("Scope 2 — purchased electricity")
    kwh = st.number_input("Annual electricity consumption (kWh)", value=500000, step=10000)
    s2 = kwh * grid_factor / 1000.0  # tCO2e
    st.metric("Scope 2 (location-based)", f"{s2:.2f} tCO2e",
              help=f"{kwh:,} kWh x {grid_factor} kgCO2/kWh")
    st.caption(f"Factor source: {GRID_SOURCE}")

# ========== SCOPE 3 ==========
with tab3:
    st.header("Scope 3 — selected categories")
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
st.subheader("Total GHG inventory")
total = s1_total + s2 + s3_total
st.metric("Total (Scope 1+2+3 selected)", f"{total:.2f} tCO2e")

# ========== BIOGENIC ==========
with tab4:
    st.header("Biogenic flux — GBA coastal wetland")
    from ucst_ccif import CarbonContinuumModel, ParameterSet
    T = 365
    doy = np.arange(T)
    gpp = np.clip(4.0 + 3.0*np.sin(2*np.pi*(doy-120)/365.25), 0.5, 8.0)
    T_air = 22.0 + 8.0*np.sin(2*np.pi*(doy-200)/365.25)
    swc = np.full(T, 0.6)
    rain = np.zeros(T)
    m = CarbonContinuumModel(ParameterSet())
    s = m.run(gpp, T_air, swc, rain)
    c1, c2, c3 = st.columns(3)
    c1.metric("Annual NEE", f"{s.nee.mean()*365:+.1f} gC m-2 yr-1")
    c2.metric("Blue carbon burial", f"{s.coastal_burial_cum:.1f} gC m-2 yr-1")
    c3.metric("|eps_C|", f"{np.mean(np.abs(s.eps_C)):.4f}")
    st.line_chart(pd.DataFrame({"day": doy, "NEE": s.nee}).set_index("day"))

# ========== LEAKAGE ==========
with tab5:
    st.header("Leakage audit")
    from ucst_ccif import audit_leakage
    uploaded = st.file_uploader("Upload CSV with target + predictors", type=["csv"])
    if uploaded:
        df = pd.read_csv(uploaded)
        tgt = st.selectbox("Target column", df.columns)
        preds = [c for c in df.columns if c != tgt]
        rep = audit_leakage(df, tgt, preds)
        st.text(rep.summary())
    else:
        st.info("Upload a CSV to run the 3-step leakage audit.")

# ========== NGFS ==========
with tab6:
    st.header("NGFS Phase V scenarios")
    ngfs = {
        "Orderly": {"carbon_price_2030": 150, "physical_risk": "low"},
        "Disorderly": {"carbon_price_2030": 350, "physical_risk": "medium"},
        "Hot House": {"carbon_price_2030": 15, "physical_risk": "high"},
    }
    sc = st.selectbox("Scenario", list(ngfs.keys()))
    st.json(ngfs[sc])

# ========== PDF ==========
with tab7:
    st.header("Export ISO 14064-3 audit trail")
    if st.button("Generate PDF"):
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph
        from reportlab.lib.styles import getSampleStyleSheet
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4)
        styles = getSampleStyleSheet()
        story = [
            Paragraph("UCST-CCIF Carbon Audit Report", styles["Title"]),
            Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["Normal"]),
            Paragraph(f"Boundary: corporate operations, {region} grid", styles["Normal"]),
            Paragraph(f"Scope 1: {s1_total:.3f} tCO2e", styles["Normal"]),
            Paragraph(f"Scope 2: {s2:.2f} tCO2e (factor {grid_factor} kg/kWh, MEE 2022)", styles["Normal"]),
            Paragraph(f"Scope 3 (selected): {s3_total:.2f} tCO2e", styles["Normal"]),
            Paragraph(f"Total: {total:.2f} tCO2e", styles["Heading2"]),
            Paragraph("Factors: MEE Announcement 2024 No.33; MEE power guideline App.A.", styles["Normal"]),
            Paragraph("Verification: third-party ISO 14064-3 assurance required before disclosure.", styles["Normal"]),
        ]
        doc.build(story)
        st.download_button("Download", buf.getvalue(),
                           file_name="ucst_ccif_audit.pdf", mime="application/pdf")
