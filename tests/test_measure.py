import numpy as np

from careq.measure import (LOG_GRID, Response, MeasureOptions, frac_octave_average, measure_signal,
                           average_power, window_ir)
from careq.signals import SweepSpec, exp_sweep, inverse_filter
from careq.simulate import Scenario
from conftest import max_abs, rms


def test_frac_octave_average_flat_and_slope():
    f = np.fft.rfftfreq(1 << 16, 1 / 48000)
    flat = np.full_like(f, 3.0)
    assert np.allclose(frac_octave_average(f, flat, 3), 3.0)
    # a straight line in log f averages to itself (window symmetric in log f)
    line = np.zeros_like(f)
    line[1:] = 2.0 * np.log2(f[1:] / 1000)
    out = frac_octave_average(f, line, 3, LOG_GRID)
    m = (LOG_GRID > 200) & (LOG_GRID < 15000)
    assert np.max(np.abs(out[m] - 2.0 * np.log2(LOG_GRID[m] / 1000))) < 0.05


def test_frac_octave_weights_ignore_zero_weight_bins():
    f = np.fft.rfftfreq(1 << 14, 1 / 48000)
    v = np.zeros_like(f)
    w = np.ones_like(f)
    v[(f > 4000) & (f < 4100)] = 100.0
    w[(f > 4000) & (f < 4100)] = 0.0
    out = frac_octave_average(f, v, 3, np.array([4050.0]), weights=w)
    assert abs(out[0]) < 1e-9


def test_response_csv_roundtrip(tmp_path):
    r = Response(LOG_GRID, np.sin(np.log(LOG_GRID)), "x")
    r.to_csv(tmp_path / "r.csv")
    r2 = Response.from_csv(tmp_path / "r.csv")
    assert np.allclose(r.db, r2.db, atol=1e-3)


def test_response_parses_umik_style_cal(tmp_path):
    p = tmp_path / "cal.txt"
    p.write_text('"Sens Factor =-1.2dB, SERNO: 7001234"\n20.0\t-3.1\t0\n100 -0.5 0\n1000\t0.0\n10000 1.2 12\n')
    r = Response.from_csv(p)
    assert list(r.freq) == [20.0, 100.0, 1000.0, 10000.0]
    assert r.db[0] == -3.1 and r.db[-1] == 1.2


def test_average_power():
    a = Response(LOG_GRID, np.zeros_like(LOG_GRID))
    b = Response(LOG_GRID, np.full_like(LOG_GRID, 10.0))
    avg = average_power([a, b])
    assert abs(avg.db[0] - 10 * np.log10((1 + 10) / 2)) < 1e-9


def test_window_ir_shape():
    h = np.zeros(48000)
    h[1000] = 1.0
    w = window_ir(h, 1000, 48000, pre_ms=5, post_ms=100)
    assert len(w) == 240 + 4800
    assert w[240] == 1.0
    assert w[0] == 0.0 and abs(w[-1]) < 1e-6


def test_clean_measurement_matches_truth(scenario, short_spec):
    steps = np.zeros(13)
    rec = scenario.record(steps, onset_s=0.5, drift_ppm=0.0, snr_db=None)
    m = measure_signal(rec, short_spec, MeasureOptions(drift="off"))
    assert len(m.sweeps) == short_spec.repeats
    truth = scenario.true_response_smoothed(steps)
    got = m.response().db
    diff = (got - truth)
    diff -= diff[(LOG_GRID > 200) & (LOG_GRID < 2000)].mean()
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.3


def test_repeats_are_all_found_and_averaged(scenario):
    spec = SweepSpec(duration=3.0, pre_silence=0.5, post_silence=1.0, repeats=3)
    sc = Scenario.default(spec, seed=0)
    rec = sc.record(np.zeros(13), onset_s=0.4, snr_db=30.0)
    m = measure_signal(rec, spec, MeasureOptions(drift="off"))
    assert len(m.sweeps) == 3
    onsets = np.array([s.onset for s in m.sweeps])
    assert np.allclose(np.diff(onsets), spec.n_sweep + spec.n_post, atol=3)
    truth = sc.true_response_smoothed(np.zeros(13))
    diff = m.response().db - truth
    diff -= diff[(LOG_GRID > 200) & (LOG_GRID < 2000)].mean()
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.4


def test_harmonic_distortion_is_rejected(short_spec):
    sc = Scenario.default(short_spec, seed=0)
    steps = np.zeros(13)
    clean = measure_signal(sc.record(steps, snr_db=None), short_spec, MeasureOptions(drift="off")).response().db
    dirty = measure_signal(sc.record(steps, snr_db=None, nonlinearity=0.3), short_spec,
                           MeasureOptions(drift="off")).response().db
    diff = dirty - clean
    diff -= diff[(LOG_GRID > 200) & (LOG_GRID < 2000)].mean()
    # a cubic nonlinearity of this size puts 3rd harmonics ~-20 dB below the fundamental;
    # the Farina separation must keep them out of the linear response
    assert max_abs(diff, 0, LOG_GRID, 40, 16000) < 0.3


def test_snr_estimate_is_sane(scenario, short_spec):
    rec = scenario.record(np.zeros(13), onset_s=0.5, snr_db=30.0)
    m = measure_signal(rec, short_spec, MeasureOptions(drift="off"))
    snr = m.snr_db()
    band = (LOG_GRID > 100) & (LOG_GRID < 10000)
    assert np.min(snr[band]) > 20  # deconvolution gain: the estimate must not be pessimistic
    assert np.max(snr[band]) < 120


def test_pink_noise_rta_recovers_a_known_filter():
    """A continuous-noise measurement must recover a known magnitude response,
    and must still do so when the 'microphone' moves during the take."""
    import numpy as np
    from scipy import signal as sg
    from careq.signals import pink_noise
    from careq.measure import measure_noise_signal, LOG_GRID
    from careq.biquad import peaking_sos, low_shelf_sos, sos_magnitude_db

    fs = 48000
    stim = pink_noise(30.0, fs, level_dbfs=-20.0, seed=3)
    sos = np.vstack([low_shelf_sos(120.0, 0.7, 6.0, fs),
                     peaking_sos(400.0, 1.5, -5.0, fs),
                     peaking_sos(3000.0, 2.0, 4.0, fs)])
    truth = sos_magnitude_db(sos, LOG_GRID, fs)
    rec = sg.sosfilt(sos, stim)
    rec = np.concatenate([np.zeros(fs), rec, np.zeros(fs)])          # silence either side

    got = measure_noise_signal(rec, fs, stim).response(3.0)
    m = (LOG_GRID >= 40) & (LOG_GRID <= 16000)
    err = (got.db - got.db[m].mean()) - (truth - truth[m].mean())
    assert np.sqrt(np.mean(err[m] ** 2)) < 0.5, np.sqrt(np.mean(err[m] ** 2))
    assert np.max(np.abs(err[m])) < 1.5, np.max(np.abs(err[m]))

    # a slowly time-varying gain, standing in for a moving microphone, must not
    # break it: a sweep would smear this into the frequency axis, noise averages it
    t = np.arange(len(rec)) / fs
    moved = rec * 10 ** (1.5 * np.sin(2 * np.pi * 0.2 * t) / 20)
    got2 = measure_noise_signal(moved, fs, stim).response(3.0)
    err2 = (got2.db - got2.db[m].mean()) - (truth - truth[m].mean())
    assert np.sqrt(np.mean(err2[m] ** 2)) < 0.6, np.sqrt(np.mean(err2[m] ** 2))
