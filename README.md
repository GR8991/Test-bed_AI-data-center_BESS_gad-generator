# BESS Virtual Simulation Tool

**Tesla Megapack 2 XL + CAT Gas Generator + AI Data Centre + Grid**

Pre-feasibility virtual simulation tool for Battery Energy Storage System integration
with AI data centres, Caterpillar gas generators, and utility grid connection.

## Sources
- Tesla Megapack 2 XL Design and Installation Manual Rev 2.9 (Nov 2025)
- NVIDIA BESS Self-Qualification Guidelines v0.4 (Feb 2026)
- IEEE 1547-2018

## 5 Environments
| Env | Simulates | NVIDIA Tests |
|-----|-----------|--------------|
| ENV 1 | AI GPU cluster load profile & ramp events | T4 |
| ENV 2 | Megapack 2XL SOC, AI buffering, DR dispatch | T4, T6, T11 |
| ENV 3 | CAT governor response, N-1 trip, black start | T9, T10 |
| ENV 4 | SCR, LVRT/HVRT IEEE 1547-2018, resonance risk | T5, T7 |
| ENV 5 | Combined dashboard + all 12 NVIDIA checks + Excel export | All 12 |

## Deploy to Streamlit Cloud
1. Fork this repo
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. New app → select this repo → main file: `app.py`
4. Deploy

## Run Locally
```bash
pip install -r requirements.txt
streamlit run app.py
```

## Disclaimer
RMS-level energy dispatch model only. NOT EMT simulation.
Results are indicative — cannot substitute for PSCAD/ETAP studies
or NVIDIA hardware qualification tests.
