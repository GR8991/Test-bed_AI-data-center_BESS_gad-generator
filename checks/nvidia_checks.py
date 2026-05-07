"""
nvidia_checks.py
Evaluates simulation outputs against NVIDIA BESS Self-Qualification
Guidelines v0.4 (Feb 2026).

Results:
  "PASS"       – simulation suggests criteria likely met
  "AMBER"      – borderline or needs study beyond simulation
  "FAIL"       – simulation shows criteria not met
  "EMT ONLY"   – cannot assess in RMS simulation; EMT study mandatory
  "DOC ONLY"   – documentation/hardware test; not simulatable
"""
import numpy as np
from utils.constants import NVIDIA_REQ, MP2XL

def run_all_checks(state) -> dict:
    results = {}
    results["T1"]  = check_t1(state)
    results["T2"]  = check_t2(state)
    results["T3"]  = check_t3(state)
    results["T4"]  = check_t4(state)
    results["T5"]  = check_t5(state)
    results["T6"]  = check_t6(state)
    results["T7"]  = check_t7(state)
    results["T8"]  = check_t8(state)
    results["T9"]  = check_t9(state)
    results["T10"] = check_t10(state)
    results["T11"] = check_t11(state)
    results["T12"] = check_t12(state)
    return results

# ── Individual test checks ────────────────────────────────────

def check_t1(s):
    return {
        "name": "T1 — Telemetry Verification",
        "method": "Hardware",
        "status": "DOC ONLY",
        "color": "🔵",
        "detail": (
            "Requires physical Modbus TCP client test with 3 simultaneous connections, "
            "≤5ms time alignment, 1ms timestamps, 7-day log. "
            "Tesla Megapack 2 XL communicates via Modbus TCP/DNP3/REST API. "
            "Cannot be assessed in this simulation."
        ),
    }

def check_t2(s):
    if s.freq_hz is None or s.p_bess_mw is None:
        status, detail = "AMBER", "Run ENV 3 (Generator) to assess GFM island stability."
    else:
        f_dev = np.max(np.abs(s.freq_hz - 50.0))
        if f_dev < 1.0:
            status = "PASS"
            detail = f"Max frequency deviation {f_dev:.2f} Hz — within 1 Hz. BESS holding island."
        elif f_dev < 2.0:
            status = "AMBER"
            detail = f"Max frequency deviation {f_dev:.2f} Hz — borderline. Hardware test required."
        else:
            status = "FAIL"
            detail = f"Max frequency deviation {f_dev:.2f} Hz — exceeds acceptable limit."
    return {
        "name": "T2 — GFM V/f Regulation (Islanded)",
        "method": "Hardware",
        "status": status, "color": _col(status), "detail": detail,
    }

def check_t3(s):
    return {
        "name": "T3 — Current Limit P/Q/Mixed",
        "method": "Hardware + EMT",
        "status": "AMBER",
        "color": "🟡",
        "detail": (
            "Megapack 2 XL has 120% overload for 10s (Table 45). "
            "P/Q priority configurable at commissioning. "
            "Limit-cycle oscillation check requires EMT model + FFT analysis. "
            "This simulation models priority logic at RMS level only."
        ),
    }

def check_t4(s):
    if s.p_bess_mw is None or s.p_it_mw is None:
        return {"name": "T4 — AI Buffering Fast Ramp", "method": "Hardware",
                "status": "AMBER", "color": "🟡",
                "detail": "Run ENV 1 and ENV 2 first."}

    # Grid-side ramp rate
    p_grid = s.p_grid_mw if s.p_grid_mw is not None else s.p_it_mw
    dp = np.abs(np.diff(p_grid, prepend=p_grid[0])) / s.dt_s
    max_ramp_pct = (np.max(dp) / max(s.peak_it_mw, 0.001)) * 100

    track_ok = s.tracking_err_pct <= NVIDIA_REQ["max_tracking_err_pct"]
    ramp_ok  = max_ramp_pct <= NVIDIA_REQ["max_ramp_pct_s"]

    if ramp_ok and track_ok:
        status = "PASS"
        detail = (f"Grid ramp {max_ramp_pct:.1f}% IT/s (≤20% ✓). "
                  f"Tracking error {s.tracking_err_pct:.2f}% (≤2% ✓).")
    elif ramp_ok:
        status = "AMBER"
        detail = (f"Grid ramp OK ({max_ramp_pct:.1f}%). "
                  f"Tracking error {s.tracking_err_pct:.2f}% — borderline.")
    else:
        status = "FAIL"
        detail = (f"Grid ramp {max_ramp_pct:.1f}% exceeds 20%/s. "
                  f"BESS not absorbing ramp fully. Increase BESS MW or reduce ramp rate.")
    return {"name": "T4 — AI Buffering Fast Ramp", "method": "Hardware",
            "status": status, "color": _col(status), "detail": detail}

def check_t5(s):
    scr = s.scr
    if scr < NVIDIA_REQ["scr_test"]:
        status = "FAIL"
        detail = (f"SCR={scr:.1f} — below SCR=2.0. T5 EMT study critical. "
                  "Section 2.9.1 of Tesla manual: resonance expected with data centre PSUs.")
    elif scr < NVIDIA_REQ["scr_amber"]:
        status = "AMBER"
        detail = (f"SCR={scr:.1f} — below 3.0, approaching weak grid. "
                  "T5 EMT study in PSCAD/EMTP-RV mandatory. "
                  "Tesla Section 2.9.1 resonance warning applies.")
    else:
        status = "AMBER"
        detail = (f"SCR={scr:.1f} — moderate grid. T5 EMT study still required "
                  "regardless of SCR. This simulation cannot replace PSCAD. "
                  "⚠️ T5 failure = ENTIRE qualification fails.")
    return {
        "name": "T5 — AI Buffering EMT SCR=2.0 ⚠️ CRITICAL",
        "method": "EMT ONLY",
        "status": status, "color": _col(status), "detail": detail,
    }

def check_t6(s):
    fast_ok = s.dr_fast_resp_s <= NVIDIA_REQ["fast_dr_s"]
    slow_ok = s.dr_slow_resp_s <= NVIDIA_REQ["slow_dr_s"]
    if fast_ok and slow_ok:
        status = "PASS"
        detail = (f"Fast DR {s.dr_fast_resp_s:.1f}s (≤2s ✓). "
                  f"Slow DR {s.dr_slow_resp_s:.1f}s (≤60s ✓).")
    elif fast_ok:
        status = "AMBER"
        detail = f"Fast DR OK. Slow DR {s.dr_slow_resp_s:.1f}s — check setpoint."
    else:
        status = "FAIL"
        detail = f"Fast DR {s.dr_fast_resp_s:.1f}s exceeds 2s limit."
    return {"name": "T6 — Demand Response Dispatch", "method": "Hardware",
            "status": status, "color": _col(status), "detail": detail}

def check_t7(s):
    if not s.lvrt_active and not s.hvrt_active:
        return {"name": "T7 — LVRT / HVRT Ride-Through", "method": "Hardware / HIL",
                "status": "AMBER", "color": "🟡",
                "detail": "Enable LVRT or HVRT event in ENV 4 to assess."}
    detail = ("Megapack 2 XL certified IEEE 1547-2018 Category II and III "
              "(Tables 55/56 of Design Manual). LVRT/HVRT curves hardcoded from Tesla spec. "
              "Hardware test with programmable voltage source required for formal qualification.")
    return {"name": "T7 — LVRT / HVRT Ride-Through", "method": "Hardware / HIL",
            "status": "AMBER", "color": "🟡", "detail": detail}

def check_t8(s):
    return {
        "name": "T8 — Seamless Grid / Island Transition",
        "method": "Hardware",
        "status": "DOC ONLY",
        "color": "🔵",
        "detail": (
            "Tesla Megapack 2 XL requires VF01 option code for GFM. "
            "Islanding requires external Islanding Controller (SEL-700 or SEL-751) — "
            "NOT autonomous in Megapack alone (Design Manual Section 2.7). "
            "Anti-islanding: Sandia Frequency Shift, detects within 2s. "
            "Synchrocheck is in the SEL relay, not Megapack. "
            "Full GFL→GFM→GFL cycle hardware test required."
        ),
    }

def check_t9(s):
    if s.freq_hz is None:
        return {"name": "T9 — Generator Following (EMT)", "method": "EMT ONLY",
                "status": "EMT ONLY", "color": "🔵",
                "detail": "Run ENV 3 to see frequency during N-1 event. EMT study (PSCAD) mandatory."}
    f_dev = np.max(np.abs(s.freq_hz - 50.0))
    # FFT of frequency signal to check 1-30Hz oscillation
    fft_vals = np.abs(np.fft.rfft(s.freq_hz - 50.0))
    fft_freqs = np.fft.rfftfreq(len(s.freq_hz), d=s.dt_s)
    mask = (fft_freqs >= 1.0) & (fft_freqs <= 30.0)
    osc_energy = np.sum(fft_vals[mask]**2) if np.any(mask) else 0
    if osc_energy > 10:
        status = "FAIL"
        detail = f"Oscillatory energy in 1–30 Hz band detected. EMT study mandatory. f_dev={f_dev:.2f}Hz."
    else:
        status = "AMBER"
        detail = (f"RMS sim shows f_dev={f_dev:.2f} Hz. "
                  "Tesla requires droop mode for generator (Design Manual Section 2.9). "
                  "EMT simulation in PSCAD mandatory for T9 formal result.")
    return {"name": "T9 — Generator Following (EMT)", "method": "EMT ONLY",
            "status": status, "color": _col(status), "detail": detail}

def check_t10(s):
    if s.p_gen_mw is None:
        return {"name": "T10 — Black Start", "method": "Hardware",
                "status": "AMBER", "color": "🟡", "detail": "Run ENV 3 with black start enabled."}
    detail = (
        f"Generator capacity: {s.gen_mw_rated:.1f} MW. "
        f"Black start step sequence: 10%→25%→50% rated load. "
        "Megapack 2 XL provides power from stored energy during generator cold start "
        f"(default ~{90}s). Hardware test on real equipment required."
    )
    return {"name": "T10 — Black Start", "method": "Hardware",
            "status": "AMBER", "color": "🟡", "detail": detail}

def check_t11(s):
    if s.soc_pct is None:
        return {"name": "T11 — SOC Drift 24h", "method": "Simulation",
                "status": "AMBER", "color": "🟡", "detail": "Run ENV 2 to simulate 24h SOC."}
    drift = abs(s.soc_drift_pct)
    if drift <= NVIDIA_REQ["max_soc_drift_pct"]:
        status = "PASS"
        detail = f"SOC drift = {s.soc_drift_pct:+.1f}% (limit ±5% ✓). Active SOC management confirmed."
    else:
        status = "FAIL"
        detail = (f"SOC drift = {s.soc_drift_pct:+.1f}% exceeds ±5% limit. "
                  "Increase BESS capacity or improve SOC management logic.")
    return {"name": "T11 — SOC Drift & Energy Management 24h", "method": "Simulation",
            "status": status, "color": _col(status), "detail": detail}

def check_t12(s):
    return {
        "name": "T12 — Control Transparency Package",
        "method": "Document Review",
        "status": "DOC ONLY",
        "color": "🔵",
        "detail": (
            "Requires: (1) Runnable EMT model of Megapack 2 XL distributed inverter architecture "
            "(24 parallel inverter modules per unit). "
            "(2) dq impedance plots at ≥4 operating points. "
            "(3) Nyquist/passivity stability certificate. "
            "(4) Complete parameter list (Kp, Ki, virtual impedance, droop coefficients). "
            "All in Tesla Controls and Communications Manual — "
            "available on Tesla Partner Portal under NDA."
        ),
    }

def _col(status: str) -> str:
    return {"PASS": "🟢", "FAIL": "🔴", "AMBER": "🟡",
            "EMT ONLY": "🔵", "DOC ONLY": "🔵"}.get(status, "⚪")
