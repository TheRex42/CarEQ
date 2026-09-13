import numpy as np
import pytest
from scipy.signal import resample_poly

from careq.measure import LOG_GRID, MeasureOptions, measure_signal, load_wav
from careq.signals import SweepSpec, write_wav
from careq.simulate import Scenario
from conftest import max_abs


@pytest.fixture(scope="module")
def full_scenario():
    # the real stimulus: 10 s, 20 Hz - 20 kHz, 48 kHz, 3 repeats
    return Scenario.default(SweepSpec(), seed=0)


@pytest.fixture(scope="module")
def single_scenario():
    return Scenario.default(SweepSpec(repeats=1), seed=0)


@pytest.mark.parametrize("onset_s,drift_ppm,seed", [
    (0.31, 0.0, 1),
    (2.7, +100.0, 2),
    (1.13, -100.0, 3),
    (0.8, +37.0, 4),
])
def test_onset_and_drift_recovered_at_30db_snr(full_scenario, onset_s, drift_ppm, seed):
    sc = full_scenario
    steps = np.zeros(13)
    rec = sc.record(steps, onset_s=onset_s, drift_ppm=drift_ppm, snr_db=30.0, seed=seed)
    m = measure_signal(rec, sc.spec)
    s = m.sweeps[0]
    # correlation locks onto the direct sound, which the synthetic cabin delays by 3 ms
    expected_onset = ((onset_s + sc.spec.pre_silence) * sc.fs + 0.003 * sc.fs) * (1 + drift_ppm * 1e-6)
    # the pre-correction correlation peak is smeared by drift; precise alignment happens after resampling
    assert abs(s.onset - expected_onset) < (0.001 if drift_ppm == 0 else 0.006) * sc.fs
    assert abs(s.drift_ppm - drift_ppm) < 2.0
    assert len(m.sweeps) == 3
    truth = sc.true_response_smoothed(steps)
    diff = m.response().db - truth
    diff -= diff[(LOG_GRID > 200) & (LOG_GRID < 2000)].mean()
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.5


@pytest.mark.parametrize("drift_ppm,seed", [(-100.0, 12), (100.0, 13)])
def test_single_sweep_uncorrected_drift_is_tolerable(single_scenario, drift_ppm, seed):
    """Without repeats there is no clock reference, so drift stays 0; at
    +-100 ppm the 1/3-octave magnitude must still be within 0.5 dB."""
    sc = single_scenario
    steps = np.zeros(13)
    rec = sc.record(steps, onset_s=0.9, drift_ppm=drift_ppm, snr_db=30.0, seed=seed)
    m = measure_signal(rec, sc.spec)
    assert len(m.sweeps) == 1
    assert m.sweeps[0].drift_ppm == 0.0
    truth = sc.true_response_smoothed(steps)
    diff = m.response().db - truth
    diff -= diff[(LOG_GRID > 200) & (LOG_GRID < 2000)].mean()
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.5


def test_drift_correction_sharpens_ir(full_scenario):
    """The estimator maximises IR peak sharpness; 100 ppm over 10 s smears the
    linear IR by ~1 ms, so the corrected IR must be much sharper. (Magnitude in
    a 500 ms window is barely affected by drift - only the IR shape is.)"""
    sc = full_scenario
    steps = np.zeros(13)
    rec = sc.record(steps, onset_s=0.5, drift_ppm=100.0, snr_db=None)
    raw = measure_signal(rec, sc.spec, MeasureOptions(drift="off")).sweeps[-1].ir
    fixed = measure_signal(rec, sc.spec).sweeps[-1].ir
    assert np.max(np.abs(fixed)) > 1.5 * np.max(np.abs(raw))


def test_recording_at_44k1_is_resampled(full_scenario, tmp_path):
    sc = full_scenario
    steps = np.zeros(13)
    rec = sc.record(steps, onset_s=0.6, drift_ppm=20.0, snr_db=40.0)
    rec44 = resample_poly(rec, 147, 160)
    p = tmp_path / "rec44.wav"
    write_wav(p, rec44 * 0.9, 44100)
    x, fs = load_wav(p, fs_target=48000)
    assert fs == 48000
    m = measure_signal(x, sc.spec)
    truth = sc.true_response_smoothed(steps)
    diff = m.response().db - truth
    diff -= diff[(LOG_GRID > 200) & (LOG_GRID < 2000)].mean()
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.5
    assert abs(m.sweeps[0].drift_ppm - 20.0) < 2.0
