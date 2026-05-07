import streamlit as st
from models.generator_model import run_generator
from utils.plots import plot_power_split, plot_frequency
from utils.constants import CAT_DEFAULTS

def render(state):
    st.header("⚙️ ENV 3 — Caterpillar Gas Generator")
    st.caption(
        "Simulates the CAT gas generator governor response alongside the BESS. "
        "BESS handles fast dynamics. Generator ramps slowly via droop. "
        "**Run ENV 1 and ENV 2 first for best results.**"
    )

    with st.expander("ℹ️ CAT Generator Integration Notes"):
        st.markdown("""
        - **Droop is required**: Tesla Design Manual Section 2.9 explicitly states 
          "Droop is Tesla's required operational mode for generators for optimal operation."
        - **Generator controller**: Must be from **Tesla Approved Vendor List (AVL)**.
          Verify CAT controller model is on the AVL before specifying.
        - **Archetype**: AI data centre + CAT + BESS + grid = **Grid-Connected Microgrid** archetype.
        - **T9 (Generator Following)**: EMT simulation in PSCAD mandatory. This simulation models 
          first-order governor dynamics only — cannot detect 1–30 Hz oscillation modes.
        - **Default values** are indicative (Caterpillar Application Guide). 
          Replace with actual CAT data sheet values for your specific model.
        """)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Generator Specification")
        gen_mw   = st.number_input("Generator rated MW (per unit)", 0.5, 50.0,
                                   float(CAT_DEFAULTS.get("governor_response_s", 2.0) * 0 + 2.0),
                                   0.5)
        num_gens = st.number_input("Number of generator units", 1, 20, 2, 1)
        droop    = st.slider("Governor droop (%)", 2.0, 10.0,
                             float(CAT_DEFAULTS["droop_pct"]), 0.5,
                             help="Tesla requires droop mode")

    with c2:
        st.subheader("Response Parameters")
        gov_s     = st.number_input("Governor response time (s)", 2.0, 30.0,
                                    float(CAT_DEFAULTS["governor_response_s"]), 0.5,
                                    help="Time for governor to reach 90% setpoint. "
                                         "Typical CAT gas: 5–15s. Replace with actual CAT data.")
        cold_s    = st.number_input("Cold start time (s)", 20.0, 300.0,
                                    float(CAT_DEFAULTS["cold_start_s"]), 5.0,
                                    help="Time from cold start command to full load. "
                                         "Typical 60–180s. BESS must bridge this.")
        n1_t      = st.number_input("N-1 trip event time (hour, 0=disabled)", 0.0, 23.0, 10.0, 0.5)
        n1_t_s    = n1_t * 3600 if n1_t > 0 else 0.0
        blackstart = st.checkbox("Simulate black start sequence", value=False,
                                 help="Shows 0→10%→25%→50% step load sequence (NVIDIA T10)")

    st.info(
        f"**Total generator capacity**: {gen_mw * num_gens:.1f} MW | "
        f"BESS must bridge governor lag of {gov_s:.0f}s during load steps."
    )

    if st.button("▶ Run ENV 3 Simulation", type="primary"):
        if state.p_it_mw is None:
            st.error("Run ENV 1 first to generate IT load profile.")
            return state
        with st.spinner("Simulating generator response..."):
            state = run_generator(
                state=state,
                gen_mw=float(gen_mw),
                num_gens=int(num_gens),
                governor_s=float(gov_s),
                droop_pct=float(droop),
                cold_start_s=float(cold_s),
                n1_trip_t_s=float(n1_t_s),
                do_blackstart=blackstart,
                dt_s=state.dt_s,
            )
            st.session_state["state"] = state
        st.success("✅ ENV 3 complete — generator outputs ready")

    if state.p_gen_mw is not None:
        st.markdown("---")
        import numpy as np
        freq = state.freq_hz if state.freq_hz is not None else []
        f_dev = float(np.max(np.abs(np.array(freq) - 50.0))) if len(freq) else 0

        m1, m2, m3 = st.columns(3)
        m1.metric("Generator Capacity", f"{state.gen_mw_rated:.1f} MW")
        m2.metric("Max Freq Deviation", f"{f_dev:.2f} Hz")
        m3.metric("Units", str(state.num_gens))

        if f_dev < 1.0:
            st.success(f"🟢 Frequency deviation {f_dev:.2f} Hz — stable island operation")
        elif f_dev < 2.0:
            st.warning(f"🟡 Frequency deviation {f_dev:.2f} Hz — borderline. EMT study recommended.")
        else:
            st.error(f"🔴 Frequency deviation {f_dev:.2f} Hz — instability risk. "
                     f"T9 EMT study mandatory in PSCAD.")

        if n1_t > 0:
            st.warning(
                f"⚡ N-1 generator trip simulated at {n1_t:.1f}h. "
                f"BESS must absorb {gen_mw:.1f} MW step instantly. "
                f"Formal T9 assessment requires PSCAD EMT simulation."
            )

        st.plotly_chart(plot_power_split(state), use_container_width=True)
        st.plotly_chart(plot_frequency(state), use_container_width=True)

        st.info(
            "⚠️ **RMS simulation only** — first-order governor lag model. "
            "Cannot detect 1–30 Hz oscillatory modes between BESS and generator. "
            "NVIDIA T9 requires formal EMT study in PSCAD/EMTP-RV."
        )

    return state
