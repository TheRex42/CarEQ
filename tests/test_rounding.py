"""Integer solution is never much worse than the continuous one."""
import numpy as np

from careq.measure import LOG_GRID, Response
from careq.identify import EqModel, Band
from careq.biquad import peaking_magnitude_db
from careq.fit import fit_eq, default_weights, weighted_rms, effective_steps


def random_model(rng, n=13):
    fcs = 40 * 2 ** (np.arange(n) * 2 / 3)
    bands = []
    for k, fc in enumerate(fcs):
        q = rng.uniform(0.9, 2.0)
        g = rng.uniform(0.7, 1.2) * 9
        bands.append(Band(k, float(fc), 9, peaking_magnitude_db(LOG_GRID, fc * rng.uniform(0.9, 1.1), q, g)))
    return EqModel(LOG_GRID.copy(), bands)


def random_baseline(rng):
    lf = np.log2(LOG_GRID / 1000)
    y = rng.normal(0, 3) * lf / 5 + rng.normal(0, 2) * lf ** 2 / 25
    for _ in range(4):
        y += peaking_magnitude_db(LOG_GRID, 10 ** rng.uniform(1.5, 4.2), rng.uniform(0.7, 3), rng.normal(0, 4))
    return Response(LOG_GRID, y)


def test_integer_not_much_worse_than_continuous():
    rng = np.random.default_rng(0)
    target = Response(LOG_GRID, np.zeros_like(LOG_GRID))
    worst_gap, worst_vs_naive = 0.0, 0.0
    for _ in range(30):
        model = random_model(rng)
        base = random_baseline(rng)
        r = fit_eq(base, model, target)
        gap = r.rms_int - r.rms_cont
        worst_gap = max(worst_gap, gap)
        assert gap < 0.5, f"integer solution {gap:.2f} dB RMS worse than continuous"
        assert r.rms_int <= r.rms_before + 1e-9
        # never worse than naive rounding
        A = model.per_step_matrix()
        w = default_weights(LOG_GRID)
        d = r.target.db - r.baseline.db
        res = A @ effective_steps(np.round(r.steps_cont), r.gain_scale, r.cut_factor) - d
        naive = weighted_rms(res - np.sum(w * res) / np.sum(w), w)
        worst_vs_naive = max(worst_vs_naive, r.rms_int - naive)
        assert r.rms_int <= naive + 1e-9
    print(f"worst int-cont gap {worst_gap:.3f} dB")


def test_bounds_respected():
    rng = np.random.default_rng(1)
    model = random_model(rng)
    base = Response(LOG_GRID, 30 * np.log2(LOG_GRID / 1000) / 10)  # 3 dB/oct tilt: needs big corrections
    r = fit_eq(base, model, Response(LOG_GRID, np.zeros_like(LOG_GRID)))
    assert np.all(np.abs(r.steps_int) <= 9)
    assert np.all(np.abs(r.steps_cont) <= 9 + 1e-9)
    assert np.any(np.abs(r.steps_int) == 9)
