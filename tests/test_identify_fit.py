"""Synthetic end-to-end: known cabin + known 13-band EQ + known mic tilt.

identify must recover each band's basis within 0.5 dB of the true filter, fit
must reduce the weighted error to the target by >80 %, and the prediction must
agree with a re-simulation using the fitted integer settings.
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
        # dB/step is recovered (peak of per-step curve vs the true dB/step, within 10 %)
        assert abs(np.max(np.abs(band.per_step_db)) - sc.eq.db_per_step[k]) < 0.1 * sc.eq.db_per_step[k] + 0.02
    print(f"worst basis error {worst:.3f} dB")


def test_shape_description_is_plausible(session):
    sc, _, model = session
    for k, band in enumerate(model.bands):
        s = band.shape
        assert abs(np.log2(s["fc"] / sc.eq.fc[k])) < 0.15, (k, s)
        assert s["rms_err_db"] < 0.4


def test_symmetry_and_linearity_checks(session):
    _, _, model = session
    checks = model.bands[3].checks
    kinds = {c["kind"] for c in checks}
    assert kinds == {"symmetry", "linearity"}
    assert all(c["rms_dev_db"] < 0.3 for c in checks), checks
    assert model.notes["symmetry_ok"] and model.notes["linearity_ok"]
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

    # closed loop: simulate the car with the fitted settings and compare
    after = measure_signal(sc.record(result.steps_int, onset_s=0.9, drift_ppm=-63.0, snr_db=35.0, seed=999),
                           sc.spec).response().normalized()
    pred = result.predicted_int
    pred_n = pred.db - pred.level()
    diff = after.db - pred_n
    assert rms(diff, LOG_GRID, 40, 16000) < 0.3
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.7

    # and the real (simulated) result is genuinely close to the target
    w = default_weights(LOG_GRID)
    r = after.db - result.target.db
    r -= np.sum(w * r) / np.sum(w)
    assert weighted_rms(r, w) < 0.35 * result.rms_before


def test_model_roundtrip(session, tmp_path):
    from careq.identify import EqModel
    _, _, model = session
    model.save(tmp_path / "m.json")
    m2 = EqModel.load(tmp_path / "m.json")
    assert np.allclose(m2.per_step_matrix(), model.per_step_matrix(), atol=1e-3)
    assert m2.bands[3].checks == model.bands[3].checks
