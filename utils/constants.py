# ================================================================
# constants.py
# Sources:
#   Tesla Megapack 2 XL Design and Installation Manual Rev 2.9 (Nov 2025)
#   NVIDIA BESS Self-Qualification Guidelines v0.4 (Feb 2026)
#   IEEE 1547-2018
# ================================================================

MP2XL = {
    # Standard configurations — Table 4, 480V AC
    "config_2h_kva":        2400.0,
    "config_2h_kw":         1927.2,
    "config_2h_kwh":        3854.4,
    "config_4h_kva":        1320.0,
    "config_4h_kw":          979.2,
    "config_4h_kwh":        3916.8,
    "config_4h_kw_c012":    1075.0,
    "config_4h_kwh_c012":   4300.0,
    # Inverter — Table 45
    "nominal_v_ac":          480,
    "output_v_min":          422,
    "output_v_max":          552,
    "freq_range_min":         45,
    "freq_range_max":         66,
    "full_load_eff":         0.983,
    "power_reg_accuracy":    0.02,   # <2% — maps to NVIDIA T4 ≤2%
    "thd_grid_connected":    0.05,
    "thd_grid_forming":      0.08,   # Table 46
    "overload_pct":          1.20,   # 120% for 10s — Section 5.4.1
    "overload_duration_s":   10,
    "overload_recovery_min": 10,
    "max_modules":           24,
    "ip_rating":            "IP66",
    "temp_min_c":           -30,
    "temp_max_c":            50,
    # Resonance threshold — Section 2.9.1 (CRITICAL for AI data centres)
    "resonance_threshold_pct": 0.20,
    "resonance_switching_khz": 35,
    # GFM option codes — Table 2
    "gfm_code":   "VF01",
    "gfl_code":   "VF00",
    # Anti-islanding — Section 5.4.7.1
    "island_detect_s": 2.0,
    # Reconnection — Table 61
    "reconnect_delay_s":    300,
    "reconnect_v_min_pct":  88.33,
    "reconnect_v_max_pct": 105.83,
}

NVIDIA_REQ = {
    "max_ramp_pct_s":      20.0,   # T4 — ≤20% IT load/s at grid
    "max_tracking_err_pct": 2.0,   # T4 — ≤2% tracking error
    "scr_test":             2.0,   # T5 — SCR=2.0
    "scr_amber":            3.0,   # below 3.0 → amber warning
    "fast_dr_s":            2.0,   # T6 — ≤2s fast DR
    "slow_dr_s":           60.0,   # T6 — ≤60s slow DR
    "max_soc_drift_pct":    5.0,   # T11 — ±5% over 24h
    "soc_min_pct":         20.0,   # T11 — DoD min
    "soc_max_pct":         80.0,   # T11 — DoD max
    "modbus_connections":   3,     # T1 — 3 simultaneous
    "log_retention_days":   7,     # T1 — 7-day log
    "oscillation_low_hz":   1.0,   # T9 — dangerous band
    "oscillation_high_hz": 30.0,
    "emt_timestep_us":     50,     # T12 — ≤50µs
    "blackstart_steps":    [10, 25, 50],  # T10
}

# LVRT — Tesla Manual Table 56, IEEE 1547-2018
LVRT_SEGMENTS = [
    # (v_min_pu, v_max_pu, ride_through_s)
    (0.00, 0.30, 0.16),
    (0.30, 0.45, 0.16),
    (0.45, 0.65, 0.32),
    (0.65, 0.88, 20.0),
    (0.88, 1.00, 9999),
]

# HVRT — Tesla Manual Table 55, IEEE 1547-2018
HVRT_SEGMENTS = [
    # (v_min_pu, v_max_pu, ride_through_s)
    (1.000, 1.100, 9999),
    (1.100, 1.150, 1.0),
    (1.150, 1.175, 0.5),
    (1.175, 1.200, 0.2),
    (1.200, 1.300, 0.2),
]

# CAT generator defaults (Caterpillar Application Guide — working assumptions)
CAT_DEFAULTS = {
    "governor_response_s": 10,
    "cold_start_s":        90,
    "warm_start_s":        30,
    "droop_pct":            4.0,  # Tesla requires droop — Design Manual Section 2.9
    "min_load_pct":        30,
}
