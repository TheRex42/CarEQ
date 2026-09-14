"""What the fixed 13-band graphic EQ costs against free parametric filters.

Same baseline, target, weighting and free level offset; the only change is
replacing the 13 measured fixed-centre bands with N peaking filters whose
centre, Q and gain are all free. Run from the repo root:

    .venv/bin/python results/parametric/compare_parametric.py
"""
import numpy as np, sys, time
sys.path.insert(0, '.')
from scipy.optimize import least_squares
from careq.measure import Response, LOG_GRID as G
from careq.identify import EqModel
from careq.fit import fit_eq, load_target, default_weights, weighted_rms, effective_steps

model = EqModel.load('results/session3/eq_model.json')
base = Response.from_csv('results/session4/baseline_pooled_18.csv').normalized()
tgt = load_target('mazda_neutral').normalized()
w = default_weights(G); sw = np.sqrt(w)
d = tgt.db - base.db; W2 = (2 * np.pi * G) ** 2


def wrms(r):
    return weighted_rms(r - np.sum(w * r) / np.sum(w), w)


def peak_db(fc, q, g):
    """Analogue peaking-filter magnitude, vectorised over the log grid."""
    if g == 0.0:
        return np.zeros_like(G)
    A = 10 ** (g / 40.0); w0 = 2 * np.pi * fc
    x = (w0 ** 2 - W2) ** 2; y = W2 * w0 ** 2
    return 10 * np.log10((x + y * (A / q) ** 2) / (x + y / (A * q) ** 2))


def curve(p, n):
    t = np.full_like(G, p[-1])
    for i in range(n):
        t = t + peak_db(np.exp(p[3 * i]), np.exp(p[3 * i + 1]), p[3 * i + 2])
    return t


def fit_peq(n, qmax, restarts=2, seed=0):
    rng = np.random.default_rng(seed); best = None
    lo = [np.log(30.0), np.log(0.3), -9.0] * n + [-30.0]
    hi = [np.log(16000.0), np.log(qmax), 9.0] * n + [30.0]
    for k in range(restarts):
        fc0 = np.geomspace(45, 12000, n) * (1.0 if k == 0 else np.exp(rng.normal(0, 0.3, n)))
        p0 = np.concatenate([np.stack([np.log(np.clip(fc0, 31, 15900)),
                                       np.full(n, np.log(min(2.0, qmax * 0.9))),
                                       np.zeros(n)], 1).ravel(), [0.0]])
        r = least_squares(lambda p: (curve(p, n) - d) * sw, p0, bounds=(lo, hi), max_nfev=1500)
        e = wrms(curve(r.x, n) - d)
        if best is None or e < best[0]:
            best = (e, r.x.copy(), curve(r.x, n))
    return best


if __name__ == "__main__":
    ref = fit_eq(base, model, tgt, max_boost=4); ref9 = fit_eq(base, model, tgt)
    for lbl, v in (("no EQ", wrms(-d)),
                   ("13 fixed bands, integer, boosts<=+4 (ours)", ref.rms_int),
                   ("13 fixed bands, integer, boosts<=+9", ref9.rms_int),
                   ("13 fixed bands, continuous gains", ref9.rms_cont)):
        print(f"{lbl:48}{v:9.2f} dB")
    print()
    for n, qmax in ((13, 3.0), (5, 10.0), (8, 10.0), (13, 10.0), (20, 10.0)):
        t = time.time(); e, x, tot = fit_peq(n, qmax)
        print(f"{f'{n:2d} parametric, free fc/Q/gain, Q<={qmax:g}':48}{e:9.2f} dB   ({time.time()-t:.0f}s)")
