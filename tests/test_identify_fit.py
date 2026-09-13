"""Synthetic end-to-end: known cabin + known 13-band EQ + known mic tilt.

identify must recover each band's basis within 0.5 dB of the true filter and
the cut factor within 0.03; fit must reduce the weighted error to the target
by >80 % of what an oracle can; and, because the synthetic head unit (like the
real one) does not superpose exactly, a second measure-and-refit pass with
``current=`` must land within 0.3 dB rms of its own prediction.
"""
import numpy as np
import pytest

from careq.measure import LOG_GRID, Measurement, Response, measure_signal
from careq.identify import identify
from careq.fit import fit_eq, load_target, default_weights, weighted_rms
from careq.simulate import Scenario
from conftest import max_abs, rms


@pytest.fixture(scope="module")
def session(scenario):
    """Baseline (2 recordings) + 13 bands at +9, band 4 also at -9 and +3."""
    sc = scenario
    n = sc.eq.n_bands
    rng = np.random.default_rng(7)
    drift = -63.0  # same phone, same car: constant across the session

    def rec(steps, seed):
        return measure_signal(sc.record(steps, onset_s=float(rng.uniform(0.3, 1.5)), drift_ppm=drift,
                                        snr_db=35.0, seed=seed), sc.spec)

    baseline = Measurement.combine([rec(np.zeros(n), 100), rec(np.zeros(n), 101)])
    runs = []
    for k in range(n):
        s = np.zeros(n); s[k] = 9
        runs.append((k, 9, rec(s, 200 + k)))
    s = np.zeros(n); s[3] = -9
    runs.append((3, -9, rec(s, 300)))
    s = np.zeros(n); s[3] = 3
    runs.append((3, 3, rec(s, 301)))
    model = identify(baseline, runs, n_bands=n, labels_hz=list(sc.eq.fc))
    return sc, baseline, model


def test_bases_match_known_filters(session):
    sc, baseline, model = session
    n = sc.eq.n_bands
    worst = 0.0
    for k, band in enumerate(model.bands):
        steps = np.zeros(n); steps[k] = 9
        truth = sc.true_response_smoothed(steps) - sc.true_response_smoothed(np.zeros(n))
        err = max_abs(band.basis_db, truth, LOG_GRID, 40, 16000)
        worst = max(worst, err)
        assert err < 0.5, f"band {k + 1}: max basis error {err:.2f} dB"
        # dB/step is recovered (peak of per-step curve vs the true single-band peak, within 5 %)
        true_step = np.max(np.abs(truth)) / 9
        assert abs(np.max(np.abs(band.per_step_db)) - true_step) < 0.05 * true_step + 0.02
    print(f"worst basis error {worst:.3f} dB")


def test_shape_description_is_plausible(session):
    sc, _, model = session
    for k, band in enumerate(model.bands):
        s = band.shape
        assert abs(np.log2(s["fc"] / sc.eq.fc[k])) < 0.15, (k, s)
        assert s["rms_err_db"] < 0.4


def test_symmetry_and_linearity_checks(session):
    sc, _, model = session
    checks = model.bands[3].checks
    kinds = {c["kind"] for c in checks if "kind" in c}
    assert kinds == {"symmetry", "linearity"}
    assert all(c["rms_dev_db"] < 0.3 for c in checks if "kind" in c), checks
    assert model.notes["symmetry_ok"] and model.notes["linearity_ok"]
    # the cut/boost asymmetry is recovered, in the smoothed domain the fit
    # works in (power smoothing shrinks a cut more than a boost, so this is
    # a little below the unit's own cut_factor)
    n = sc.eq.n_bands
    t0 = sc.true_response_smoothed(np.zeros(n))
    s = np.zeros(n); s[3] = 9
    tb = sc.true_response_smoothed(s) - t0
    s[3] = -9
    tc = sc.true_response_smoothed(s) - t0
    near = (LOG_GRID >= sc.eq.fc[3] / 2) & (LOG_GRID <= sc.eq.fc[3] * 2)
    truth_ratio = -np.sum(tc[near] * tb[near]) / np.sum(tb[near] ** 2)
    assert abs(model.notes["cut_factor"] - truth_ratio) < 0.03, (model.notes["cut_factor"], truth_ratio)
    assert truth_ratio < sc.eq.cut_factor
    lin = [c for c in checks if c.get("kind") == "linearity"][0]
    assert abs(lin["ratio_to_linear"] - 1.0) < 0.05, lin
    assert all(abs(d + 63.0) < 3 for d in model.notes["drift_ppm"])


def test_fit_reduces_error_and_prediction_matches_resimulation(session):
    sc, baseline, model = session
    n = sc.eq.n_bands
    target = load_target("harman_car")
    base_resp = baseline.response()
    result = fit_eq(base_resp, model, target)
    print(result.summary())

    # Oracle: a fit that knows the true filters and the true baseline exactly.
    # The synthetic cabin has features 13 bands of Q~1.5 cannot null (a Q 1.0
    # dip between band centres, sub-bass below band 1), so the oracle itself
    # only removes ~75 % of the weighted error. The pipeline must remove >80 %
    # of what the oracle can remove, and >65 % in absolute terms.
    from careq.identify import Band, EqModel
    t0 = sc.true_response_smoothed(np.zeros(n))
    truth_bands = []
    for k in range(n):
        s = np.zeros(n); s[k] = 9
        truth_bands.append(Band(k, float(sc.eq.fc[k]), 9, sc.true_response_smoothed(s) - t0))
    oracle = fit_eq(Response(LOG_GRID, t0), EqModel(LOG_GRID.copy(), truth_bands), target)
    reducible = result.rms_before - oracle.rms_int
    achieved = result.rms_before - result.rms_int
    print(f"oracle {oracle.rms_int:.2f} dB, pipeline {result.rms_int:.2f} dB, before {result.rms_before:.2f} dB")
    assert achieved > 0.8 * reducible, (achieved, reducible)
    assert result.rms_int < 0.35 * result.rms_before, result.summary()
    assert np.all(np.abs(result.steps_int) <= 9)
    assert result.rms_int <= result.rms_cont + 0.5

    # closed loop, pass 1: the fit's linear model (gain scale, cut factor) is
    # only an approximation of a unit whose bands do not add exactly, so the
    # first prediction is allowed to miss by up to ~1 dB rms ...
    def resim(steps, seed):
        return measure_signal(sc.record(steps, onset_s=0.9, drift_ppm=-63.0, snr_db=35.0, seed=seed),
                              sc.spec).response()

    after1 = resim(result.steps_int, 999)
    diff1 = after1.normalized().db - (result.predicted_int.db - result.predicted_int.level())
    err1 = rms(diff1, LOG_GRID, 40, 16000)
    assert err1 < 1.0, err1

    # ... and pass 2 (measure with the settings in, refit with current=) must
    # land close to its own prediction and not be worse than pass 1
    w = default_weights(LOG_GRID)

    def err_vs_target(resp):
        r = resp.db - result.target.db
        r -= np.sum(w * r) / np.sum(w)
        return weighted_rms(r, w)

    result2 = fit_eq(after1, model, target, current=result.steps_int)
    print(result2.summary())
    assert np.all(np.abs(result2.steps_int) <= 9)
    after2 = resim(result2.steps_int, 998)
    diff2 = after2.normalized().db - (result2.predicted_int.db - result2.predicted_int.level())
    err2 = rms(diff2, LOG_GRID, 40, 16000)
    print(f"prediction error pass 1 {err1:.2f} dB, pass 2 {err2:.2f} dB; "
          f"vs target: pass 1 {err_vs_target(after1):.2f}, pass 2 {err_vs_target(after2):.2f}, "
          f"before {result.rms_before:.2f}")
    assert err2 < 0.3, err2
    # where several bands cut together the summed gain sits inside the
    # limiter's compression and a linear step delivers only part of its
    # nominal gain, so a single point may still miss by up to ~1 dB ...
    assert max_abs(diff2, 0, LOG_GRID, 40, 16000) < 1.0
    assert err_vs_target(after2) <= err_vs_target(after1) + 0.05
    assert err_vs_target(after2) < 0.35 * result.rms_before

    # ... and a third pass keeps converging
    result3 = fit_eq(after2, model, target, current=result2.steps_int)
    after3 = resim(result3.steps_int, 997)
    diff3 = after3.normalized().db - (result3.predicted_int.db - result3.predicted_int.level())
    err3 = rms(diff3, LOG_GRID, 40, 16000)
    print(f"pass 3: prediction error {err3:.2f} dB, max {max_abs(diff3, 0, LOG_GRID, 40, 16000):.2f} dB, "
          f"vs target {err_vs_target(after3):.2f}")
    assert err3 <= err2 + 0.05
    assert max_abs(diff3, 0, LOG_GRID, 40, 16000) < 0.7
    assert err_vs_target(after3) <= err_vs_target(after2) + 0.05


def test_iterate_is_consistent_with_direct_fit():
    """With an exactly linear synthetic model, fitting from any current setting
    must give the same answer as fitting from flat."""
    from careq.identify import Band, EqModel
    from careq.biquad import peaking_magnitude_db
    rng = np.random.default_rng(3)
    fcs = [40, 63, 100, 160, 250, 500, 1000, 1600, 2500, 4000, 6300, 10000, 16000]
    bands = [Band(k, float(fc), 9, peaking_magnitude_db(LOG_GRID, fc, 2.0, 8.5)) for k, fc in enumerate(fcs)]
    model = EqModel(LOG_GRID.copy(), bands)
    A = model.per_step_matrix()
    from careq.fit import effective_steps
    base = Response(LOG_GRID, 3 * np.log2(LOG_GRID / 1000) + peaking_magnitude_db(LOG_GRID, 120, 1.0, 5))
    target = Response(LOG_GRID, np.zeros_like(LOG_GRID))
    direct = fit_eq(base, model, target, gain_scale=0.87, cut_factor=0.93)
    for _ in range(3):
        cur = rng.integers(-4, 5, size=13)
        measured = Response(LOG_GRID, base.db + A @ effective_steps(cur, 0.87, 0.93))
        it = fit_eq(measured, model, target, current=cur, gain_scale=0.87, cut_factor=0.93)
        assert np.all(it.change == it.steps_int - cur)
        assert abs(it.rms_int - direct.rms_int) < 0.05, (it.rms_int, direct.rms_int)
        assert np.sum(np.abs(it.steps_int - direct.steps_int)) <= 2, (it.steps_int, direct.steps_int)


def test_model_roundtrip(session, tmp_path):
    from careq.identify import EqModel
    _, _, model = session
    model.save(tmp_path / "m.json")
    m2 = EqModel.load(tmp_path / "m.json")
    assert np.allclose(m2.per_step_matrix(), model.per_step_matrix(), atol=1e-3)
    assert m2.bands[3].checks == model.bands[3].checks
