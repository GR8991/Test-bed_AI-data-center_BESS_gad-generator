import numpy as np
from models.sim_state import SimState
from utils.constants import NVIDIA_REQ

def build_ai_load(
    num_gpus: int,
    tdp_kw: float,
    util_pct: float,
    num_clusters: int,
    ramp_rate_mw_s: float,
    jobs_per_day: int,
    pue: float,
    dt_s: float = 1.0,
) -> SimState:
    state = SimState(dt_s=dt_s)
    N = int(86400 / dt_s)
    state.time_s = np.arange(0, N * dt_s, dt_s)

    gpus_per_cluster = max(num_gpus // max(num_clusters, 1), 1)
    peak_mw_cluster  = gpus_per_cluster * tdp_kw * (util_pct / 100.0) / 1000.0
    peak_mw_total    = peak_mw_cluster * num_clusters
    idle_mw          = peak_mw_total * 0.20

    p_it = np.full(N, idle_mw)

    ramp_events = []
    np.random.seed(42)

    if jobs_per_day > 0:
        biz_s = int(6 * 3600 / dt_s)
        biz_e = int(22 * 3600 / dt_s)
        n_biz   = int(jobs_per_day * 0.70)
        n_night = jobs_per_day - n_biz

        t_biz   = sorted(np.random.choice(range(biz_s, biz_e), min(n_biz, biz_e - biz_s), replace=False))
        night_pool = list(range(0, biz_s)) + list(range(biz_e, N))
        t_night = sorted(np.random.choice(night_pool, min(n_night, len(night_pool)), replace=False))
        all_starts = sorted(t_biz + t_night)

        ramp_steps = max(int(peak_mw_cluster / max(ramp_rate_mw_s, 0.001)), 1)

        for idx, t0 in enumerate(all_starts):
            cluster_mw = peak_mw_cluster
            job_dur = int(np.random.uniform(1800, 10800) / dt_s)
            t_up   = min(t0 + ramp_steps, N)
            t_top  = min(t_up + job_dur, N)
            t_dn   = min(t_top + ramp_steps, N)

            for i in range(t0, t_up):
                frac = (i - t0) / ramp_steps
                p_it[i] = min(p_it[i] + frac * cluster_mw, peak_mw_total)
            for i in range(t_up, t_top):
                p_it[i] = min(p_it[i] + cluster_mw, peak_mw_total)
            for i in range(t_top, t_dn):
                frac = 1.0 - (i - t_top) / ramp_steps
                p_it[i] = min(p_it[i] + frac * cluster_mw, peak_mw_total)

            ramp_events.append({
                "t_s":        t0 * dt_s,
                "t_hhmm":     _fmt_time(t0 * dt_s),
                "cluster":    (idx % num_clusters) + 1,
                "delta_mw":   cluster_mw,
                "ramp_mw_s":  ramp_rate_mw_s,
                "ramp_pct_s": (ramp_rate_mw_s / max(peak_mw_total, 0.001)) * 100,
            })

    p_it     = np.clip(p_it, idle_mw, peak_mw_total)
    p_site   = p_it * pue
    dp       = np.abs(np.diff(p_it, prepend=p_it[0])) / dt_s
    max_ramp = (np.max(dp) / max(peak_mw_total, 0.001)) * 100

    state.p_it_mw      = p_it
    state.p_site_mw    = p_site
    state.peak_it_mw   = float(np.max(p_it))
    state.avg_it_mw    = float(np.mean(p_it))
    state.daily_mwh    = float(np.sum(p_it) * dt_s / 3600)
    state.ramp_events  = ramp_events
    state.max_ramp_pct_s = float(max_ramp)
    return state

def _fmt_time(t_s: float) -> str:
    h = int(t_s // 3600)
    m = int((t_s % 3600) // 60)
    return f"{h:02d}:{m:02d}"
