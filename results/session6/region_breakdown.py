"""Where the remaining error lives, from the session 6 measured verification.

Produces the table in docs/method.md, "What remains, and why". Both curves
are real measurements: the calibrated moving-mic baseline, and the same car
recorded again with the verified Neutral settings in place. Run from the
repo root:

    .venv/bin/python results/session6/region_breakdown.py

The one thing to get right is the level offset. The fit is free to shift the
whole response, so the error is defined after removing ONE global weighted
offset. Computing an offset per region instead silently subtracts each
region's mean error, which makes a bass hump disappear -- the overall figures
printed here reproduce the 4.30 -> 1.81 dB in the session 6 write-up, which
is the check that it is being done the same way as `careq fit`.
"""
import numpy as np, sys
sys.path.insert(0, '.')
from careq.measure import Response, LOG_GRID as G
from careq.fit import load_target, default_weights, erb_weights

REGIONS = ((20, 50, '20-50 Hz'), (50, 120, '50-120 Hz'), (120, 300, '120-300 Hz'),
           (300, 1000, '300 Hz-1 kHz'), (1000, 1600, '1-1.6 kHz'),
           (1600, 4000, '1.6-4 kHz'), (4000, 10000, '4-10 kHz'),
           (10000, 20000, '10-20 kHz'))
NORM = (200.0, 2000.0)


def residual(resp, target, w):
    """target - response, with one global weighted level offset removed."""
    d = target.db - resp.db
    return d - np.sum(w * d) / np.sum(w)


def rms(d, w, m=None):
    m = slice(None) if m is None else m
    return float(np.sqrt(np.sum(w[m] * d[m] ** 2) / np.sum(w[m])))


w, w_erb = default_weights(G), erb_weights(G)
flat = Response.from_csv('results/session6/baseline_move_pooled.csv').normalized(*NORM)
after = Response.from_csv('results/session6/verify_pooled.csv').normalized(*NORM)
target = load_target('mazda_neutral').normalized(*NORM)

d_flat, d_after = residual(flat, target, w), residual(after, target, w)
print(f"overall {rms(d_flat, w):.2f} -> {rms(d_after, w):.2f} dB log-uniform, "
      f"{rms(residual(flat, target, w_erb), w_erb):.2f} -> "
      f"{rms(residual(after, target, w_erb), w_erb):.2f} ERB")
print("(session 6 write-up: 4.30 -> 1.81 and 3.62 -> 1.56)\n")

total = np.sum(w * d_after ** 2)
print(f"{'region':>14} {'flat':>8} {'after':>8} {'gained':>8} {'share':>7}")
for lo, hi, label in REGIONS:
    m = (G >= lo) & (G < hi)
    a, b = rms(d_flat, w, m), rms(d_after, w, m)
    print(f"{label:>14} {a:>6.2f}dB {b:>6.2f}dB {a - b:>+7.2f} "
          f"{100 * np.sum(w[m] * d_after[m] ** 2) / total:>6.0f}%")
