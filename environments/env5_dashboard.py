import streamlit as st
from checks.nvidia_checks import run_all_checks
from utils.plots import plot_combined_dashboard
from utils.export import export_excel

def render(state):
    st.header("📊 ENV 5 — Combined Dashboard & NVIDIA Qualification Check")
    st.caption(
        "Combines all 4 environment outputs and evaluates against "
        "NVIDIA BESS Self-Qualification Guidelines v0.4 (Feb 2026)."
    )

    # ── Combined power chart ──────────────────────────────────
    if state.p_it_mw is not None:
        st.subheader("System Overview — All Power Flows")
        st.plotly_chart(plot_combined_dashboard(state), use_container_width=True)
    else:
        st.info("Run ENV 1 through ENV 4 to populate the dashboard.")

    st.markdown("---")

    # ── NVIDIA Qualification Check ────────────────────────────
    st.subheader("🎯 NVIDIA BESS Qualification — 12-Test Assessment")
    st.caption(
        "Based on simulation results and Tesla Megapack 2 XL Design Manual Rev 2.9. "
        "🟢 = likely pass | 🟡 = needs study | 🔴 = likely fail | 🔵 = hardware/doc only"
    )

    results = run_all_checks(state)
    state.nvidia = results
    st.session_state["state"] = state

    # Counts
    counts = {"PASS": 0, "AMBER": 0, "FAIL": 0, "EMT ONLY": 0, "DOC ONLY": 0}
    for r in results.values():
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🟢 PASS",      counts.get("PASS", 0))
    c2.metric("🟡 AMBER",     counts.get("AMBER", 0))
    c3.metric("🔴 FAIL",      counts.get("FAIL", 0))
    c4.metric("🔵 EMT Only",  counts.get("EMT ONLY", 0))
    c5.metric("🔵 Doc/HW",    counts.get("DOC ONLY", 0))

    # T5 critical banner
    t5 = results.get("T5", {})
    if t5.get("status") == "FAIL":
        st.error(
            "⛔ **T5 CRITICAL FAILURE**: SCR below 2.0. "
            "This means ENTIRE qualification fails regardless of all other results. "
            "EMT study in PSCAD/EMTP-RV is MANDATORY before proceeding."
        )

    # Test cards
    for tid, res in results.items():
        color_map = {"PASS": "success", "FAIL": "error",
                     "AMBER": "warning", "EMT ONLY": "info", "DOC ONLY": "info"}
        fn = getattr(st, color_map.get(res["status"], "info"))
        fn(
            f"{res['color']} **{res['name']}** — _{res['method']}_\n\n"
            f"{res['detail']}"
        )

    st.markdown("---")

    # ── Data Gap Summary ──────────────────────────────────────
    st.subheader("📋 Customer Data Gap Summary")
    gaps = []
    if state.peak_it_mw == 0:   gaps.append(("A1/A4", "IT load profile & ramp rate", "BLOCKING"))
    if state.gen_mw_rated == 0: gaps.append(("B1/B3", "CAT generator specs & governor data", "BLOCKING"))
    if state.grid_mva < 50:     gaps.append(("C2",    "Grid fault level from utility", "BLOCKING"))
    if state.scr > 8:           gaps.append(("C2",    "SCR unconfirmed — use actual utility data", "HIGH"))

    if gaps:
        for item_id, desc, sev in gaps:
            if sev == "BLOCKING":
                st.error(f"🔴 **{item_id}** — {desc} — *BLOCKING: sizing cannot finalise*")
            else:
                st.warning(f"🟡 **{item_id}** — {desc}")
    else:
        st.success("All key input data populated. Review ENV results above.")

    st.markdown("---")

    # ── Export ────────────────────────────────────────────────
    st.subheader("📥 Export Results")
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("Generate Excel Report", type="primary"):
            xls = export_excel(state, results)
            st.download_button(
                label="⬇️ Download Excel (.xlsx)",
                data=xls,
                file_name="bess_simulation_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
    with col_b:
        st.caption(
            "Excel contains: simulation summary, NVIDIA 12-test results, "
            "and 24-hour time-series data (1-min resolution)."
        )

    return state
