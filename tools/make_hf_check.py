"""Generate a high-frequency audibility check for the car.

Ten tones, 8 kHz to 18 kHz, each level-compensated for the car's measured
response *and* the EQ settings currently loaded, so every tone arrives at
the listening position at the same SPL. Where the tones stop being audible
is then a property of the listener, not of the car.

    .venv/bin/python tools/make_hf_check.py [--steps "+6 -9 -9 ..."]
"""
from __future__ import annotations
import argparse, sys
import numpy as np
sys.path.insert(0, '.')
from careq.measure import Response, LOG_GRID as G
from careq.identify import EqModel
from careq.fit import effective_steps
from careq.signals import write_wav

TONES = [8000, 10000, 11000, 12000, 13000, 14000, 15000, 16000, 17000, 18000]
NEUTRAL_PLUS6 = [6, -9, -9, 3, -1, 4, 3, -7, 0, 4, -2, -2, -1]

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--steps", default=None, help='13 integers, e.g. "+6 -9 -9 +3 -1 +4 +3 -7 0 +4 -2 -2 -1"')
    ap.add_argument("--baseline", default="results/session4/baseline_pooled_18.csv")
    ap.add_argument("--model", default="results/session3/eq_model.json")
    ap.add_argument("--out", default="stimulus/careq_hf_check_48k.wav")
    ap.add_argument("--level", type=float, default=-26.0, help="dBFS of the reference tone")
    ap.add_argument("--max-comp", type=float, default=12.0, help="cap on compensation (dB)")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--gap", type=float, default=1.2)
    a = ap.parse_args()

    steps = np.array([int(v) for v in a.steps.replace(",", " ").split()]) if a.steps else np.array(NEUTRAL_PLUS6)
    model = EqModel.load(a.model)
    resp = Response.from_csv(a.baseline).normalized().db + model.per_step_matrix() @ effective_steps(steps, 0.95, 0.93)
    ref = np.interp(np.log(8000.0), np.log(G), resp)

    fs = 48000
    parts = [np.zeros(int(0.5 * fs))]
    print(f"{'tone':>8}  {'car response':>13}  {'compensation':>13}  {'level':>8}")
    for f in TONES:
        r = float(np.interp(np.log(f), np.log(G), resp))
        comp = float(np.clip(ref - r, -a.max_comp, a.max_comp))
        amp = 10 ** ((a.level + comp) / 20)
        n = int(a.seconds * fs)
        t = np.arange(n) / fs
        x = amp * np.sin(2 * np.pi * f * t)
        k = int(0.05 * fs)
        x[:k] *= np.linspace(0, 1, k); x[-k:] *= np.linspace(1, 0, k)
        parts += [x, np.zeros(int(a.gap * fs))]
        print(f"{f/1000:6.0f}k  {r - ref:+12.1f}  {comp:+12.1f}  {a.level + comp:+7.1f} dBFS")
    y = np.concatenate(parts)
    write_wav(a.out, y, fs)
    print(f"\nwrote {a.out}  ({len(y)/fs:.0f} s, {len(TONES)} tones)")
    print("Tones in order: " + ", ".join(f"{f//1000}k" for f in TONES))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
