import streamlit as st
from models.grid_model import run_grid, check_lvrt_compliance, check_hvrt_compliance
from utils.plots import plot_voltage, plot_lvrt_envelope
from utils.constants import NVIDIA_REQ, MP2XL

def render(state):
    st.header("⚡ ENV 4 — Grid Connection")
    st.caption(
        "Models grid interaction — SCR, LVRT/HVRT ride-through per IEEE 1547-2018, "
        "and Demand Response. LVRT/HVRT curves sourced from Tesla Manual Tables 55/56."
    )

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Grid Parameters")
        grid_mva = st.number_input("Grid fault level at PCC (MVA)", 10.0, 5000.0, 200.0, 10.0,
                                   help="Obtain from utility — not estimated. "
                                        "Used to calculate SCR.")
        bess_kva = state.bess_mw_rated * 1000 if state.bess_mw_rated > 0 else 2400.0
        scr = grid_mva / max(bess_kva / 1000, 0.001)
        nominal_kv = st.selectbox("Grid voltage (kV)", [11, 33, 66, 110, 132, 220], index=1)

        st.metric("Calculated SCR", f"{scr:.1f}")
        if scr < NVIDIA_REQ["scr_test"]:
            st.error(f"🔴 SCR={scr:.1f} < 2.0 — T5 EMT study CRITICAL. "
                     "Tesla Section 2.9.1 resonance warning. Failure = entire qualification fails.")
        elif scr < NVIDIA_REQ["scr_amber"]:
            st.warning(f"🟡 SCR={scr:.1f} — weak grid. T5 EMT study mandatory in PSCAD.")
        else:
            st.success(f"🟢 SCR={scr:.1f} — moderate grid strength.")

        state.scr     = float(scr)
        state.grid_mva = float(grid_mva)

    with c2:
        st.subheader("LVRT Event (Tesla Manual Table 56 / IEEE 1547-2018)")
        apply_lvrt = st.checkbox("Apply LVRT event", value=True)
        lvrt_v     = st.slider("Voltage sag depth (pu)", 0.0, 0.90, 0.50, 0.05)
        lvrt_dur   = st.number_input("Sag duration (s)", 0.1, 30.0, 0.32, 0.01)
        lvrt_t     = st.number_input("Sag start time (hour)", 0.0, 23.0, 6.0, 0.5) * 3600

        st.subheader("HVRT Event (Tesla Manual Table 55 / IEEE 1547-2018)")
        apply_hvrt = st.checkbox("Apply HVRT event", value=False)
        hvrt_v     = st.slider("Voltage swell level (pu)", 1.05, 1.30, 1.15, 0.01)
        hvrt_dur   = st.number_input("Swell duration (s)", 0.01, 10.0, 0.5, 0.01)
        hvrt_t     = st.number_input("Swell start time (hour)", 0.0, 23.0, 12.0, 0.5) * 3600

    # LVRT compliance check
    if apply_lvrt:
        compliance = check_lvrt_compliance(lvrt_v, lvrt_dur)
        if compliance["inside_envelope"]:
            st.success(
                f"🟢 LVRT: {lvrt_v:.2f} pu for {lvrt_dur:.2f}s — "
                f"within IEEE 1547-2018 ride-through envelope "
                f"(allowed {compliance['allowed_s']:.2f}s at this voltage). "
                f"Megapack must stay connected."
            )
        else:
            st.error(
                f"🔴 LVRT: {lvrt_v:.2f} pu for {lvrt_dur:.2f}s — "
                f"OUTSIDE ride-through envelope "
                f"(only {compliance['allowed_s']:.2f}s allowed). "
                f"Megapack should trip — verify protection settings."
            )

    if apply_hvrt:
        compliance = check_hvrt_compliance(hvrt_v, hvrt_dur)
        if compliance["inside_envelope"]:
            st.success(f"🟢 HVRT: {hvrt_v:.2f} pu for {hvrt_dur:.2f}s — within envelope.")
        else:
            st.error(f"🔴 HVRT: {hvrt_v:.2f} pu for {hvrt_dur:.2f}s — outside envelope. Trip expected.")

    if state.p_it_mw is None:
        st.info("Run ENV 1 first to enable full grid simulation.")

    if st.button("▶ Run ENV 4 Simulation", type="primary"):
        it_len = len(state.p_it_mw) if state.p_it_mw is not None else int(86400 / state.dt_s)
        if state.p_it_mw is None:
            import numpy as np
            state.p_it_mw = numpy.zeros(it_len)
            state.time_s  = numpy.arange(0, it_len * state.dt_s, state.dt_s)

        with st.spinner("Simulating grid events..."):
            state = run_grid(
                state=state,
                grid_mva=float(grid_mva),
                bess_kva=float(bess_kva),
                nominal_kv=float(nominal_kv),
                apply_lvrt=apply_lvrt,
                lvrt_depth_pu=float(lvrt_v),
                lvrt_dur_s=float(lvrt_dur),
                lvrt_t_s=float(lvrt_t),
                apply_hvrt=apply_hvrt,
                hvrt_level_pu=float(hvrt_v),
                hvrt_dur_s=float(hvrt_dur),
                hvrt_t_s=float(hvrt_t),
                dt_s=state.dt_s,
            )
            st.session_state["state"] = state
        st.success("✅ ENV 4 complete")

    if state.v_pu is not None:
        st.plotly_chart(plot_voltage(state), use_container_width=True)

    st.plotly_chart(plot_lvrt_envelope(), use_container_width=True)
    st.caption("LVRT envelope sourced from Tesla Megapack 2 XL Design Manual Table 56 / IEEE 1547-2018.")

    # Resonance section
    st.markdown("---")
    st.subheader("⚠️ Resonance Risk — Section 2.9.1, Tesla Design Manual")
    st.warning(
        "**Tesla confirms**: Excessive resonance is expected when Megapack is connected to a "
        "480V AC bus with data centre power supplies if: "
        "(1) IT load exceeds 20% of Megapack apparent power rating, AND "
        "(2) GPU PSU switching frequency <35 kHz. "
        "Mitigation: line reactor, isolation transformer, or relocate equipment."
    )

    return state
