"""
UCST-CCIF Streamlit MVP — v0.3.0 (reorganized UI: 3 workspaces)

Workspaces:
  1. Upload & Dictionary — four ledgers (activity / flux / stock / intervention),
     every CSV template carries a "#" comment line with full names + units, and
     each ledger has a column dictionary. Missing ledgers are reported as data
     gaps — never silently estimated.
  2. Audit Report — the S1→S7 pipeline (boundary → factors → conservation →
     scale → additionality → leakage → uncertainty) producing the 8 artifacts
     plus a certificate, an embedded leakage verdict and a PDF evidence pack.
  3. Benchmarks — official reference data (CEADs Guangdong / Global Carbon
     Budget / HK EPD / CH4 kernels / CCER mangrove lookup) + NGFS stress lens.

Why the old tabs disappeared: uploading the four ledgers already covers
Scope 1-3 (activity ledger, stage S1), biogenic flux (flux ledger, stage S2),
leakage (stage S6) and PDF export (post-audit). Manual input tabs were
duplicate entry points, so they were removed.
"""

from __future__ import annotations
import io
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
    st.caption("**How to use** — ① upload your four ledgers, ② run the audit, "
               "③ compare against official benchmarks. Every number is traceable "
               "to a source or a formula in this app.")
    st.caption(f"[GitHub]({GITHUB_URL}) · [Zenodo DOI]({DOI_URL}) · v{APP_VERSION.lstrip('v')}")

tab_upload, tab_report, tab_bench = st.tabs([
    "📥 1. Upload & Dictionary",
    "🧾 2. Audit Report",
    "📊 3. Benchmarks",
])

# ==================================================================
# 1. UPLOAD & DICTIONARY
# ==================================================================
with tab_upload:
    st.header("Upload the four ledgers")
    st.caption("Every file is **optional** — missing ones become reported data gaps, "
               "never silent estimates. Each CSV template carries a **`#` comment line** "
               "with full names and units; download one and open it in Excel to see it.")

    # ---- CSV templates (with # comment lines: full name + unit + example) ----
    tmpl = {
        "activity": (
            "# Activity ledger 活动账 — 全称与单位\n"
            "# scope: 核算范围 1=自烧燃料(Scope1) 2=外购电力(Scope2) 3=供应链(Scope3) | "
            "category: 类别 electricity/fuel/purchased_goods | "
            "activity_key: 具体活动键 如 guangdong/diesel_L/manufactured_goods | "
            "quantity: 数量(单位随类别: electricity→kWh, fuel→L或m3, purchased_goods→CNY)\n"
            "scope,category,activity_key,quantity\n"
            "2,electricity,guangdong,1135589.4\n"
            "1,fuel,diesel_L,20000\n"
            "2,purchased_goods,manufactured_goods,2000000\n"),
        "flux": (
            "# Flux ledger 通量账 — 全称与单位\n"
            "# date: 日期(YYYY-MM-DD) | "
            "NEE_daily_total: 净生态系统碳交换 Net Ecosystem Exchange, g C m-2 day-1, 负=吸收 | "
            "GPP_daily_total: 总初级生产力 Gross Primary Production, g C m-2 day-1 | "
            "ER_daily_total: 生态系统呼吸 Ecosystem Respiration, g C m-2 day-1\n"
            "date,NEE_daily_total,GPP_daily_total,ER_daily_total,wind_speed_mean,temperature_2m_mean\n"
            "2023-01-01,3.92,2.27,1.29,14.7,14.0\n"
            "2023-01-02,4.47,1.90,1.14,20.2,15.3\n"),
        "stock": (
            "# Stock ledger 碳库账 — 全称与单位\n"
            "# area_ha: 项目面积 hectare 公顷 | "
            "removal_tco2e: 独立观测移除量 tonnes CO2 equivalent 吨二氧化碳当量\n"
            "area_ha,removal_tco2e\n"
            "100.0,420.0\n"),
        "intervention": (
            "# Intervention ledger 干预账 — 全称与单位\n"
            "# scenario: 情景名 如 wetland_restoration | "
            "baseline_removal_tco2e: 基线移除量 tCO2e(什么都不做的对照) | "
            "intervention_removal_tco2e: 干预后移除量 tCO2e | "
            "active_fraction: 主动管理干预占比 0-1 无量纲\n"
            "scenario,baseline_removal_tco2e,intervention_removal_tco2e,active_fraction\n"
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

    # ---- upload + validation (skip # comment lines) ----
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
    c_a, c_f, c_s, c_i = st.columns(4)
    for col, (key, (skey, label)) in zip((c_a, c_f, c_s, c_i), ledgers.items()):
        with col:
            st.markdown(f"**{label}**")
            up = st.file_uploader(f"Upload {key}", type=["csv"], key=f"up_{key}")
            if up:
                try:
                    df = pd.read_csv(up, comment="#")
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

    # ---- per-ledger column dictionary ----
    st.divider()
    st.markdown('<span class="ocip-section">Column dictionary — 每列全称 / 单位 / 角色</span>',
                unsafe_allow_html=True)
    dict_rows = [
        ("activity",
         [("scope", "核算范围 GHG scope", "1 / 2 / 3", "1=自烧燃料 2=外购电 3=供应链（S1 自动分类核算）"),
          ("category", "类别 category", "electricity / fuel / purchased_goods", "决定用哪张因子表"),
          ("activity_key", "活动键 activity key", "如 guangdong / diesel_L", "映射到因子库的具体条目"),
          ("quantity", "数量 quantity", "kWh · L · m³ · CNY（随类别）", "× 排放因子 → 排放量（S1）")]),
        ("flux",
         [("date", "日期 date", "YYYY-MM-DD", "时间步（可选，自动忽略）"),
          ("NEE_daily_total", "净生态系统碳交换 NEE", "g C m⁻² day⁻¹", "审计目标：站点净碳通量（S2）"),
          ("GPP_daily_total", "总初级生产力 GPP", "g C m⁻² day⁻¹", "⚠️ NEE 代数派生，作预测变量即泄漏（S6）"),
          ("ER_daily_total", "生态系统呼吸 ER", "g C m⁻² day⁻¹", "⚠️ 同上，NEE = ER − GPP（S6）")]),
        ("stock",
         [("area_ha", "项目面积 area", "公顷 ha", "把 gC/m² 换算成 tCO₂e 的尺度（S2/S4）"),
          ("removal_tco2e", "独立观测移除量 removal", "吨 CO₂ 当量 tCO₂e", "与声称值对账的独立依据（S3）")]),
        ("intervention",
         [("scenario", "情景 scenario", "文本", "如 wetland_restoration"),
          ("baseline_removal_tco2e", "基线移除量 baseline", "tCO₂e", "什么都不做的对照（S5，式3 F_p）"),
          ("intervention_removal_tco2e", "干预后移除量 intervention", "tCO₂e", "做了之后的移除（S5，式3）"),
          ("active_fraction", "主动干预占比 active", "0–1 无量纲", "主动管理份额（可选）")]),
    ]
    for key, label, rows in (
            ("activity", "活动账", dict_rows[0][1]),
            ("flux", "通量账", dict_rows[1][1]),
            ("stock", "碳库账", dict_rows[2][1]),
            ("intervention", "干预账", dict_rows[3][1])):
        with st.expander(f"📖 {label} 列说明", expanded=False):
            st.table(pd.DataFrame(rows, columns=["列名", "全称", "单位", "在审计中的角色"]))

    st.divider()
    area_ha = st.number_input(
        "Project area (ha) — 把每日 NEE（gC/m²/d）换算成 tCO₂e",
        0.0, 1e9, 100.0, step=1.0, key="ocip_area_input")
    st.session_state["ocip_area"] = area_ha

    st.info("**Scope 1/2/3 不用手动算了** —— 活动账里填 `category` + `quantity`，"
            "审计流水线 S1 自动完成三类核算：Scope 1=自烧燃料，Scope 2=外购电力，"
            "Scope 3=供应链（差旅/通勤/采购）。上传完去 **Tab 2 Audit Report** 点 Run the audit。")

# ==================================================================
# 2. AUDIT REPORT
# ==================================================================
with tab_report:
    st.header("Audit report — 7-step pipeline, 8 artifacts")
    st.caption("Runs S1 (boundary) → S2 (factors) → S3 (conservation, Eq.1) → "
               "S4 (scale) → S5 (additionality, Eq.3) → S6 (leakage, Eq.7) → "
               "S7 (uncertainty) on the four ledgers uploaded in tab 1.")

    st.markdown("""
    <div style="display:flex;flex-wrap:wrap;gap:10px;align-items:stretch;font-size:0.85rem;margin:6px 0 10px;">
      <div style="flex:2 1 380px;background:#fff;border:1px solid #d8dee4;border-radius:10px;padding:10px;">
        <b>⚙️ 7 步流水线 run_audit()</b>
        <div style="margin-top:6px;display:flex;flex-wrap:wrap;gap:4px;align-items:center;">
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S1 边界</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S2 因子</div><span style="color:#5c6b7a;">→</span>
          <div style="border:2px solid #B23A3A;border-radius:6px;padding:4px 6px;background:#FDF3F1;">S3 守恒</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S4 尺度</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S5 额外性</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S6 泄漏</div><span style="color:#5c6b7a;">→</span>
          <div style="border:1px solid #5c6b7a;border-radius:6px;padding:4px 6px;background:#f7f9fb;">S7 不确定</div>
        </div>
        <div style="margin-top:6px;color:#5c6b7a;font-size:0.75rem;">S3: ε_C = 独立观测 − 企业声称（负=过度声称）· S5: 主动触发 F_a vs 被动响应 F_p · S6: 泄漏三步</div>
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
                                help="企业声称的移除量 —— S3 拿它和独立观测对账")
    with a2:
        agent_col = st.text_input("Agent-state column (Eq.2, optional)",
                                  placeholder="e.g. water_level / mangrove_age",
                                  help="通量账里承载管理信号的列；留空则跳过归因分解")
    with a3:
        area = st.session_state.get("ocip_area", 100.0)
        st.metric("Area used for gC → tCO₂e", f"{area:,.1f} ha",
                  help="在 Tab 1 设置")

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

        # --- leakage verdict (formerly its own tab) ---
        with st.expander("🛡️ Leakage verdict (S6)", expanded=True):
            if rep.leakage is not None and rep.leakage.leaky_predictors:
                st.markdown("**Flagged LEAKY predictors (NEE-derived, circular):** "
                            + ", ".join(f"`{p}`" for p in rep.leakage.leaky_predictors))
                st.markdown("These columns are algebraically derived from NEE "
                            "(GPP/ER balance) — any model using them inflates R² "
                            "circularly. Drop them before quoting performance.")
            if rep.leak_free_gain_pct is not None:
                st.info(f"Leakage-free refit (step 3): apparent gain from leaky "
                        f"predictors = **{rep.leak_free_gain_pct:+.1f}%** "
                        f"(Sapelo honest baseline: 36.1%).")
            else:
                st.caption("No flux ledger uploaded — leakage stage reported as a "
                           "data gap, not estimated.")

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

        # --- PDF evidence pack (formerly its own tab) ---
        st.divider()
        if st.button("📤 Download ISO 14064-3 evidence pack (PDF)"):
            from reportlab.lib.pagesizes import A4
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import getSampleStyleSheet
            buf = io.BytesIO()
            doc = SimpleDocTemplate(buf, pagesize=A4)
            styles = getSampleStyleSheet()
            story = [
                Paragraph("OCIP — Carbon Audit Evidence Pack", styles["Title"]),
                Paragraph(f"Generated: {datetime.now().isoformat(timespec='seconds')}", styles["Normal"]),
                Paragraph(f"Platform: OCIP {APP_VERSION} (UCST-CCIF engine) · {GITHUB_URL}", styles["Normal"]),
                Paragraph(f"Certificate: {rep.certificate_status}", styles["Heading2"]),
                Spacer(1, 6),
                Paragraph(f"Verified emissions: "
                          f"{rep.emissions_tco2e:.1f} ± {rep.emissions_u95_tco2e:.1f} tCO2e"
                          if rep.emissions_tco2e is not None else
                          "Verified emissions: not run", styles["Normal"]),
                Paragraph(f"Verified removals: "
                          f"{rep.removals_tco2e:.1f} ± {rep.removals_u95_tco2e:.1f} tCO2e"
                          if rep.removals_tco2e is not None else
                          "Verified removals: not run", styles["Normal"]),
                Paragraph(f"Conservation residual ε_C: {rep.residual_eC_tco2e:+.1f} tCO2e "
                          "(negative = over-claim)" if rep.residual_eC_tco2e is not None
                          else "ε_C: not run", styles["Normal"]),
                Paragraph(f"Leakage RYG: {rep.leakage_ryg}", styles["Normal"]),
                Spacer(1, 6),
                Paragraph("Stage log:", styles["Heading3"]),
            ]
            for s in rep.stages:
                story.append(Paragraph(
                    f"[{s.status}] S{s.stage} {s.name} — {s.detail}", styles["Normal"]))
            if rep.data_gaps:
                story.append(Spacer(1, 6))
                story.append(Paragraph("Data gaps (do not fill with estimates):",
                                       styles["Heading3"]))
                for g in rep.data_gaps:
                    story.append(Paragraph(f"- {g}", styles["Normal"]))
            story.append(Spacer(1, 12))
            story.append(Paragraph(
                "Verification: third-party ISO 14064-3 assurance required before "
                "disclosure.", styles["Normal"]))
            doc.build(story)
            st.download_button("Download PDF", buf.getvalue(),
                               file_name="ocip_audit_evidence_pack.pdf",
                               mime="application/pdf")
    else:
        st.info("Upload at least the activity ledger + one removal observation "
                "in tab 1, then press **Run the audit**.")

# ==================================================================
# 3. BENCHMARKS (official reference data + stress lens)
# ==================================================================
with tab_bench:
    st.header("Benchmarks — official reference data")
    st.caption("These numbers are **external standards**, not your data: they give "
               "your audit a frame of reference. Sources: CEADs 2022 (Guangdong) · "
               "Global Carbon Budget 2025 · HK EPD GHG inventory 2023 · IPCC/CCER.")

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
    st.bar_chart(pd.DataFrame({"Sector": list(gd_sectors),
                               "MtCO2": list(gd_sectors.values())}).set_index("Sector"),
                 height=240)
    g1, g2 = st.columns(2)
    g1.metric("Guangdong total (2022)", "613.9 Mt CO₂",
              help="CEADs Shan et al. provincial sectoral inventory, IPCC Sectoral Approach")
    g2.metric("Power & heat share", "61.8%",
              help="Electric power dominates — the CBAM/ETS hotspot for GBA exporters")

    # --- B. Global (GCB2025, 2024) ---
    st.markdown('<span class="ocip-section">B. Global human emissions — fossil + land-use (GCB2025, 2024)</span>',
                unsafe_allow_html=True)
    fossil = {"Coal": 4.31, "Oil": 3.40, "Gas": 2.19, "Cement": 0.40, "Other": 0.42}
    st.bar_chart(pd.DataFrame({"Fuel": list(fossil),
                               "GtC per yr": list(fossil.values())}).set_index("Fuel"),
                 height=200)
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

    # --- D. HK sectors (EPD 2023) ---
    st.markdown('<span class="ocip-section">D. Hong Kong sectors — GHG inventory 2023 (EPD, kt CO₂e)</span>',
                unsafe_allow_html=True)
    hk_sectors = {
        "Electricity & energy ind.": 21200, "Transport": 6330,
        "Industrial processes & other": 2920, "Waste": 2410,
        "Other combustion": 1660, "Agriculture": 28,
    }
    st.bar_chart(pd.DataFrame({"Sector": list(hk_sectors),
                               "ktCO2e": list(hk_sectors.values())}).set_index("Sector"),
                 height=200)
    h1, h2, h3 = st.columns(3)
    h1.metric("HK total (2023)", "34.5 Mt CO₂e",
              help="≈ −25% vs 2014 peak; EPD GHG inventory, revised methodology")
    h2.metric("Electricity share", "61.3%",
              help="Power is HK's dominant source — same story as Guangdong, same CBAM lens")
    h3.metric("Per-capita", "4.6 t CO₂e",
              help="Record low since 1990s (7.5M population)")

    # --- E. CH4 kernels (rice + landfill) ---
    st.markdown('<span class="ocip-section">E. CH₄ — rice paddies & landfills (GBA, IPCC/DNDC kernels)</span>',
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
            from ucst_ccif.landfill import landfill_ch4_tier1
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
    st.caption("CH₄ has ~28× GWP of CO₂: the GBA CH₄ wedge is rice + landfills "
               "+ tidal wetlands — OCIP audits all three on one CH₄ ledger.")

    # --- F. CCER mangrove lookup (screening tool) ---
    st.markdown('<span class="ocip-section">F. CCER mangrove restoration — project screening lookup</span>',
                unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("Methodology: **CCER—14—002—V02 红树林营造** (2026 revision, "
                    "age-based lookup; baseline = unvegetated tidal flat / retired shrimp pond). "
                    "This is a **pre-screening estimate**, not a credit claim — official "
                    "crediting requires CCER field measurement per the methodology age-based "
                    "tables (App. A, Guangdong region).")
        f1, f2, f3 = st.columns(3)
        f1.metric("Default crediting period", "20–40 yr", help="CCER methodology 计入期")
        f2.metric("GD mangrove C stock", "3.22 Mt C",
                  help="Guangdong province (Kandelia obovata dominant)")
        f3.metric("GD sink potential", "6.6–18.2 tCO₂e/ha/yr",
                  help="55 km² target → 36,171–99,891 tCO₂e/yr")
        proj_area = st.number_input("Your project area (ha)", 0.0, 100000.0,
                                    100.0, key="ccer_area")
        proj_age = st.slider("Mean stand age (yr)", 1, 50, 10, key="ccer_age")
        agb_accum = 0.35 * proj_age + 1.2          # Mg C/ha (above+below, saturating proxy)
        soil_acc = 0.35                             # Mg C/ha/yr burial
        tot_acc = agb_accum + soil_acc * proj_age   # Mg C/ha cumulative
        co2_per_ha = tot_acc * 44.0 / 12.0
        st.metric("Estimated cumulative carbon", f"{co2_per_ha * proj_area:,.0f} tCO₂e",
                  f"{co2_per_ha:.1f} tCO₂e/ha over {proj_age} yr (order-of-magnitude)")

    # --- G. NGFS stress lens (based on your audit) ---
    st.markdown('<span class="ocip-section">G. NGFS Phase V — stress lens on your inventory</span>',
                unsafe_allow_html=True)
    st.caption("Carbon-price & physical-risk lens. Uses your audited emissions when "
               "available, otherwise the demo activity in the activity template.")
    rep_now = st.session_state.get("ocip_report")
    stress_base = (rep_now.emissions_tco2e if rep_now is not None
                   and rep_now.emissions_tco2e is not None else None)
    if stress_base is None:
        # fall back to demo activity ledger (template example), same as S1 would
        demo_act = pd.DataFrame([
            {"scope": "2", "category": "electricity",
             "activity_key": "guangdong", "quantity": 1135589.4},
            {"scope": "1", "category": "fuel",
             "activity_key": "diesel_L", "quantity": 20000},
        ])
        from ucst_ccif.audit_pipeline import _validate_activity
        try:
            stress_base = _validate_activity(demo_act)["tco2e"].sum()
        except Exception:  # noqa: BLE001
            stress_base = None
    if stress_base is not None:
        ngfs = {
            "Orderly": {"carbon_price_2030": 150, "physical_risk": "low"},
            "Disorderly": {"carbon_price_2030": 350, "physical_risk": "medium"},
            "Hot House": {"carbon_price_2030": 15, "physical_risk": "high"},
        }
        sc = st.selectbox("Scenario", list(ngfs.keys()))
        c1, c2 = st.columns(2)
        c1.metric("Carbon price 2030 (US$/tCO2)", ngfs[sc]["carbon_price_2030"])
        c2.metric("Physical risk", ngfs[sc]["physical_risk"])
        st.caption(f"Under {sc.lower()}, a {ngfs[sc]['carbon_price_2030']} $/t price on "
                   f"your {stress_base:.1f} tCO₂e → "
                   f"**US${ngfs[sc]['carbon_price_2030'] * stress_base:,.0f} exposure.**")
    else:
        st.info("Run the audit first (tab 2) to stress-test your verified emissions.")

    # --- H. How to use / data sources ---
    st.markdown('<span class="ocip-section">H. How to use & where the data comes from</span>',
                unsafe_allow_html=True)
    st.markdown(
        "**The audit is the product, not the number.** Three rules:\n\n"
        "1. **Upload** — your four ledgers are the only thing the audit consumes. "
        "Missing files are reported as data gaps, never silently estimated.\n"
        "2. **Run** — the 7-step pipeline verifies your numbers against independent "
        "observation and official benchmarks; the certificate is the verdict.\n"
        "3. **Benchmark** — CEADs / GCB / HK EPD / IPCC / CCER are external standards "
        "for comparison, not substitutes for your data.\n\n"
        "Free data sources: FLUXNET (fluxnet.org, CC-BY-4.0) · JapanFlux2024 · "
        "ChinaFLUX/NESDC (Jinfo 2020–2022) · CEADs provincial · HK EPD · ERA5/Open-Meteo · "
        "TROPOMI CH₄ · Sentinel-2/GEDI biomass. Full column-by-column sourcing lives in "
        "the old Data Guide tab — ask to restore it if you need it."
    )

# ------------------------------------------------------------------
st.markdown(f"""
<div class="ocip-footer">
  OCIP {APP_VERSION} · UCST-CCIF engine · {GITHUB_URL} · DOI {DOI_URL}<br/>
  The audit is the product — not the number.
</div>
""", unsafe_allow_html=True)
