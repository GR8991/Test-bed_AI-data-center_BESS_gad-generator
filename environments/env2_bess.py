import streamlit as st
from models.bess_model import run_bess
from utils.plots import plot_bess_overview, plot_soc
from utils.constants import MP2XL, NVIDIA_REQ

def render(state):
    st.header("🔋 ENV 2 — Tesla Megapack 2 XL BESS")
    st.caption(
        "Simulates the Megapack 2 XL absorbing AI load ramps, managing SOC over 24h, "
        "and responding to Demand Response dispatch. "
        "**Requires ENV 1 to be run first.**"
    )

    if state.p_it_mw is None:
        st.warning("⚠️ Run ENV 1 (AI Data Centre Load) first to generate the load profile.")
        return state

    # ── Product note ─────────────────────────────────────────
    with st.expander("ℹ️ Tesla Megapack 2 XL Product Notes (from Design Manual Rev 2.9)"):
        st.markdown("""
        - **PCS Architecture**: Each battery module has its own **integrated inverter module** — 
          up to 24 per unit, all in parallel on internal AC bus (Section 1.4.2).
          This is distributed — NOT a single central PCS cabinet.
        - **GFM Requirement**: Grid-Forming requires option code **VF01** (must specify at order).
          VF00 = no GFM. For AI data centre + CAT generator → Grid-Connected Microgrid archetype → VF01 mandatory.
        - **Islanding**: Requires external Islanding Controller (SEL-700 or SEL-751). 
          Megapack alone cannot island (Section 2.7).
        - **Power Regulation Accuracy**: <2% (Table 45) — directly matches NVIDIA T4 ≤2% tracking error.
        - **Resonance Warning**: Section 2.9.1 — resonance expected if IT load >20% of Megapack kVA 
          and GPU PSU switching <35 kHz. Mitigate with line reactor or isolation transformer.
        - **Droop for generators**: Tesla requires droop mode for all generators (Section 2.9).
        """)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Megapack Configuration")
        num_units  = st.number_input("Number of Megapack units", 1, 500, 10, 1)
        config     = st.selectbox("Configuration", ["2h", "4h"],
                                  help="2h = higher power, 4h = higher energy")
        cell_opt   = st.selectbox("Cell Option",  ["C010", "C011", "C012"])
        num_mod    = st.slider("Battery modules per unit (EC##)", 8, 24, 24,
                               help="24 = fully populated")
        gfm        = st.checkbox("Grid-Forming enabled (VF01)", value=True,
                                 help="Required for island and microgrid operation. Must order VF01.")
        if not gfm:
            st.warning("VF00 selected — GFM disabled. BESS cannot island or operate in microgrid mode.")
        temp_c = st.number_input("Ambient temperature (°C)", -30, 50, 25, 1)

    with c2:
        st.subheader("Operating Parameters")
        priority  = st.selectbox("P/Q Priority Mode",
                                 ["P-priority", "Q-priority", "Mixed"],
                                 help="How BESS splits current between active and reactive power")
        soc_start = st.slider("Starting SOC (%)", 20, 80, 50)
        st.subheader("Demand Response")
        dr_fast_mw = st.number_input("Fast DR setpoint (MW)", 0.0, 500.0, 5.0, 0.5)
        dr_fast_t  = st.number_input("Fast DR event time (hour)", 0.0, 23.0, 14.0, 0.5) * 3600
        dr_slow_mw = st.number_input("Slow DR setpoint (MW)", 0.0, 500.0, 3.0, 0.5)
        dr_slow_t  = st.number_input("Slow DR event time (hour)", 0.0, 23.0, 20.0, 0.5) * 3600

    # ── Rated capacity display ────────────────────────────────
    cfg_map = {"2h": (MP2XL["config_2h_kw"], MP2XL["config_2h_kwh"]),
               "4h": (MP2XL["config_4h_kw"], MP2XL["config_4h_kwh"])}
    kw_u, kwh_u = cfg_map[config]
    mod_f = num_mod / 24
    mw_r  = kw_u * num_units * mod_f / 1000
    mwh_r = kwh_u * num_units * mod_f / 1000
    st.info(
        f"**Configured capacity**: {mw_r:.1f} MW rated | {mwh_r:.0f} MWh rated | "
        f"Usable (20–80% DoD): **{mwh_r * 0.60:.0f} MWh**"
    )

    if st.button("▶ Run ENV 2 Simulation", type="primary"):
        with st.spinner("Simulating BESS over 24 hours..."):
            state = run_bess(
                state=state,
                num_units=int(num_units),
                config=config,
                cell_option=cell_opt,
                num_modules=int(num_mod),
                gfm_enabled=gfm,
                priority=priority,
                soc_start_pct=float(soc_start),
                dr_fast_mw=float(dr_fast_mw),
                dr_slow_mw=float(dr_slow_mw),
                dr_fast_t_s=float(dr_fast_t),
                dr_slow_t_s=float(dr_slow_t),
                temp_c=float(temp_c),
            )
            st.session_state["state"] = state
        st.success("✅ ENV 2 complete — BESS outputs ready for ENV 3 & 5")

    if state.p_bess_mw is not None:
        st.markdown("---")
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("BESS Rated MW",    f"{state.bess_mw_rated:.1f} MW")
        m2.metric("BESS Rated MWh",   f"{state.bess_mwh_rated:.0f} MWh")
        m3.metric("Tracking Error",   f"{state.tracking_err_pct:.2f}%",
                  delta=f"Limit ≤2%",
                  delta_color="normal" if state.tracking_err_pct <= 2 else "inverse")
        m4.metric("SOC Drift 24h",    f"{state.soc_drift_pct:+.1f}%",
                  delta="Limit ±5%",
                  delta_color="normal" if abs(state.soc_drift_pct) <= 5 else "inverse")
        m5.metric("Fast DR Response", f"{state.dr_fast_resp_s:.1f}s",
                  delta="Limit ≤2s",
                  delta_color="normal" if state.dr_fast_resp_s <= 2 else "inverse")

        # NVIDIA T4 result
        if state.tracking_err_pct <= NVIDIA_REQ["max_tracking_err_pct"]:
            st.success(f"🟢 NVIDIA T4: Tracking error {state.tracking_err_pct:.2f}% ≤ 2% ✓")
        else:
            st.error(f"🔴 NVIDIA T4: Tracking error {state.tracking_err_pct:.2f}% exceeds 2% limit")

        # NVIDIA T11 result
        if abs(state.soc_drift_pct) <= NVIDIA_REQ["max_soc_drift_pct"]:
            st.success(f"🟢 NVIDIA T11: SOC drift {state.soc_drift_pct:+.1f}% within ±5% ✓")
        else:
            st.error(f"🔴 NVIDIA T11: SOC drift {state.soc_drift_pct:+.1f}% exceeds ±5%")

        st.plotly_chart(plot_bess_overview(state), use_container_width=True)
        st.plotly_chart(plot_soc(state), use_container_width=True)

    return state
