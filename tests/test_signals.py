import numpy as np
from scipy.signal import fftconvolve

from careq.signals import SweepSpec, exp_sweep, inverse_filter, stimulus, pink_noise


def test_sweep_inverse_is_delta():
    spec = SweepSpec(duration=2.0)
    s = exp_sweep(spec)
    inv = inverse_filter(spec, s)
    d = fftconvolve(s, inv)
    n = len(s)
    assert np.argmax(np.abs(d)) == n - 1
    assert abs(d[n - 1] - 1.0) < 1e-9
    # spectrum of the "delta" is flat inside the sweep band
    D = np.fft.rfft(d[n - 1 - 2400: n - 1 + 2400] * np.hanning(4800), 1 << 16)
    f = np.fft.rfftfreq(1 << 16, 1 / spec.fs)
    m = (f > 50) & (f < 18000)
    db = 20 * np.log10(np.abs(D[m]))
    assert db.max() - db.min() < 0.6


def test_harmonic_offsets():
    spec = SweepSpec(duration=10.0, f1=20, f2=20000)
    assert abs(spec.harmonic_offset(2) - 10 * np.log(2) / np.log(1000)) < 1e-12
    assert spec.harmonic_offset(2) > 0.9


def test_stimulus_layout():
    spec = SweepSpec(duration=1.0, pre_silence=0.5, post_silence=0.25, repeats=3, level_dbfs=-12)
    x, onsets = stimulus(spec)
    assert len(onsets) == 3
    assert len(x) == spec.n_pre + 3 * (spec.n_sweep + spec.n_post)
    assert abs(np.max(np.abs(x)) - 10 ** (-12 / 20)) < 1e-6
    for o in onsets:
        assert np.all(x[o - 10:o] == 0)
        assert np.any(x[o:o + 1000] != 0)


def test_pink_noise_slope():
    x = pink_noise(20.0, 48000, level_dbfs=-20, seed=3)
    assert abs(20 * np.log10(np.sqrt(np.mean(x ** 2))) + 20) < 0.5
    X = np.abs(np.fft.rfft(x)) ** 2
    f = np.fft.rfftfreq(len(x), 1 / 48000)
    p100 = X[(f > 90) & (f < 110)].mean()
    p1000 = X[(f > 900) & (f < 1100)].mean()
    assert abs(10 * np.log10(p100 / p1000) - 10) < 1.0
