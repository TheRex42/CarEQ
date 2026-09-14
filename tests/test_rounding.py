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


def test_erb_density_and_both_weightings_reported():
    """ERB density follows auditory bandwidth, and both error numbers are
    available and consistent whichever weighting the fit optimised."""
    from careq.fit import erb_density, erb_weights, ERB_F0

    d = erb_density(LOG_GRID)
    assert np.all(np.diff(d) > 0)                       # monotonic in frequency
    assert 0 < d[0] < 0.1 and d[-1] > 0.98              # small in the bass, ~1 up top
    assert abs(erb_density(np.array([ERB_F0]))[0] - 0.5) < 1e-9

    # the midpoint of 20 Hz-20 kHz is ~632 Hz on a log axis, ~2 kHz on an ERB axis
    erb_no = lambda f: 21.4 * np.log10(4.37 * f / 1000 + 1)
    half = (erb_no(20.0) + erb_no(20000.0)) / 2
    f_mid = LOG_GRID[np.argmin(np.abs(erb_no(LOG_GRID) - half))]
    assert 1800 < f_mid < 2200, f_mid

    rng = np.random.default_rng(5)
    model = random_model(rng)
    base = random_baseline(rng)
    target = Response(LOG_GRID, np.zeros_like(LOG_GRID))

    r_log = fit_eq(base, model, target)
    r_erb = fit_eq(base, model, target, weights=erb_weights(LOG_GRID), erb_weighted=True)

    # the continuous solve is a genuine optimum, so each wins on its own metric
    def werr(resp, w):
        r = resp.db - target.db
        return weighted_rms(r - np.sum(w * r) / np.sum(w), w)

    we, wl = erb_weights(LOG_GRID), default_weights(LOG_GRID)
    assert werr(r_erb.predicted_cont, we) <= werr(r_log.predicted_cont, we) + 1e-6
    assert werr(r_log.predicted_cont, wl) <= werr(r_erb.predicted_cont, wl) + 1e-6
    # the integer stage is +-1 coordinate descent, a heuristic, so it can land a
    # little the wrong side of the other fit; it must still be close, and far
    # inside the ~1 dB / ~1 step resolution of the method as a whole
    assert abs(r_erb.errors(erb=True)[1] - r_log.errors(erb=True)[1]) < 0.15
    assert np.abs(r_erb.steps_int - r_log.steps_int).max() <= 3
    # the optimised number matches the correspondingly weighted one
    assert abs(r_log.errors(erb=False)[1] - r_log.rms_int) < 1e-9
    assert abs(r_erb.errors(erb=True)[1] - r_erb.rms_int) < 1e-9
    # band_weights recovers the un-scaled weights
    assert np.allclose(r_erb.band_weights, default_weights(LOG_GRID))
    for r in (r_log, r_erb):
        assert "rms_erb_db" in r.to_dict() and "rms_log_db" in r.to_dict()
