"""Synthetic car: known cabin IR, known 13-band head-unit EQ, known mic tilt.

Used by the tests (ground truth for every stage) and by ``careq simulate`` to
produce realistic fake recordings for dry runs.

Signal chain: stimulus -> head-unit EQ (biquads) -> optional amp nonlinearity
-> cabin IR -> mic response -> recorder clock drift -> onset offset + tail ->
pink noise.
"""
from __future__ import annotations

import dataclasses

import numpy as np
from scipy import signal

from .signals import SweepSpec, stimulus, pink_noise


from .biquad import peaking_sos, low_shelf_sos, high_shelf_sos, sos_magnitude_db  # noqa: E402


# --------------------------------------------------------------------------- #
# Head-unit EQ
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class HeadUnitEq:
    """13 peaking filters at fixed centres with per-band Q and dB-per-step."""

    fs: int
    fc: np.ndarray
    q: np.ndarray
    db_per_step: np.ndarray

    @classmethod
    def mazda_like(cls, fs: int = 48000) -> "HeadUnitEq":
        fc = np.array([40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000], dtype=float)
        q = np.array([1.2, 1.4, 1.4, 1.5, 1.5, 1.6, 1.6, 1.6, 1.5, 1.5, 1.4, 1.3, 1.1])
        db = np.array([0.8, 0.9, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.95, 0.85])
        return cls(fs, fc, q, db)

    @property
    def n_bands(self) -> int:
        return len(self.fc)

    def sos(self, steps) -> np.ndarray:
        steps = np.asarray(steps, dtype=float)
        rows = [peaking_sos(fc, q, s * d, self.fs) for fc, q, s, d in zip(self.fc, self.q, steps, self.db_per_step)
                if s != 0]
        return np.vstack(rows) if rows else np.array([[1, 0, 0, 1, 0, 0]], dtype=float)

    def response_db(self, steps, freq: np.ndarray) -> np.ndarray:
        return sos_magnitude_db(self.sos(steps), freq, self.fs)

    def apply(self, x: np.ndarray, steps) -> np.ndarray:
        if not np.any(np.asarray(steps)):
            return x.copy()
        return signal.sosfilt(self.sos(steps), x)


# --------------------------------------------------------------------------- #
# Cabin and mic
# --------------------------------------------------------------------------- #
def cabin_coloration_sos(fs: int) -> np.ndarray:
    """Speaker + cabin broadband colouration: door-speaker roll-off, cabin gain
    in the bass, modes and dips of moderate Q, treble roll-off. Chosen so that
    a 13-band EQ with Q~1.5 bands can correct most of it (the end-to-end test
    asserts >80 % error reduction); real cabins have sharper features too,
    which no graphic EQ can fix and which the fit weights down."""
    return np.vstack([
        signal.butter(2, 20.0, "highpass", fs=fs, output="sos"),
        signal.butter(2, 17000.0, "lowpass", fs=fs, output="sos"),
        low_shelf_sos(100.0, 0.7, 4.0, fs),       # cabin gain
        peaking_sos(63.0, 1.0, 3.0, fs),          # first cabin mode
        peaking_sos(160.0, 1.0, -3.0, fs),        # floor bounce dip
        peaking_sos(420.0, 1.2, 3.0, fs),
        peaking_sos(1000.0, 1.2, -2.5, fs),
        peaking_sos(1700.0, 1.2, 2.0, fs),
        peaking_sos(3000.0, 1.2, 3.0, fs),        # tweeter/dash reflection
        peaking_sos(6300.0, 1.2, -2.5, fs),
    ])


def cabin_ir(fs: int = 48000, seed: int = 0, length_s: float = 0.35, rt60_s: float = 0.08,
             reflection_scale: float = 0.5) -> np.ndarray:
    """Direct sound, a handful of discrete reflections, a diffuse tail, coloured.

    ``reflection_scale`` sets the strength of the discrete reflections; they
    comb-filter the response with ~50-100 Hz ripple that no graphic EQ can
    remove, so the default keeps them moderate."""
    rng = np.random.default_rng(seed)
    n = int(length_s * fs)
    h = np.zeros(n)
    arrivals = [(3.0, 1.0), (5.1, -0.55), (7.3, 0.40), (9.8, -0.30), (12.5, 0.25), (17.0, 0.20), (23.0, -0.15)]
    for ms, amp in arrivals:
        h[int(ms / 1000 * fs)] += amp if ms == 3.0 else amp * reflection_scale
    t = np.arange(n) / fs
    # diffuse tail: weak, and only above ~250 Hz (a small cabin's low end is
    # modal, which the colouration filters below represent, not diffuse)
    tail = rng.standard_normal(n) * np.exp(-t * np.log(1000) / rt60_s) * 0.06
    tail = signal.sosfilt(signal.butter(2, 250.0, "highpass", fs=fs, output="sos"), tail)
    tail[: int(0.008 * fs)] = 0.0
    h += tail
    h = signal.sosfilt(cabin_coloration_sos(fs), h)
    return h / np.max(np.abs(h))


def mic_sos(fs: int = 48000) -> np.ndarray:
    """Phone-like mic: slight bass loss, gently rising treble, 9 kHz resonance."""
    return np.vstack([
        low_shelf_sos(150.0, 0.7, -2.0, fs),
        high_shelf_sos(2000.0, 0.7, 1.5, fs),
        peaking_sos(9000.0, 1.5, 2.0, fs),
    ])


# --------------------------------------------------------------------------- #
# Recorder imperfections
# --------------------------------------------------------------------------- #
def lanczos_resample(x: np.ndarray, ratio: float, a: int = 8, chunk: int = 65536) -> np.ndarray:
    """Resample so that the output has ``len(x) * ratio`` samples (windowed-sinc
    interpolation; independent of the FFT method used for correction)."""
    n_out = int(round(len(x) * ratio))
    xp = np.concatenate([np.zeros(a), x, np.zeros(a + 1)])
    out = np.empty(n_out)
    k = np.arange(-a + 1, a + 1)
    for s in range(0, n_out, chunk):
        m = np.arange(s, min(n_out, s + chunk))
        pos = m / ratio
        base = np.floor(pos).astype(int)
        frac = (pos - base)[:, None]
        d = frac - k[None, :]
        w = np.sinc(d) * np.sinc(d / a)
        w[np.abs(d) >= a] = 0.0
        idx = base[:, None] + k[None, :] + a
        out[s:s + len(m)] = np.sum(xp[idx] * w, axis=1)
    return out


@dataclasses.dataclass
class Scenario:
    spec: SweepSpec
    eq: HeadUnitEq
    cabin: np.ndarray
    mic: np.ndarray
    fs: int = 48000
    gain: float = 0.6   # recorder gain; the baseline sweep then peaks around -6 dBFS

    @classmethod
    def default(cls, spec: SweepSpec | None = None, seed: int = 0) -> "Scenario":
        spec = spec or SweepSpec()
        sc = cls(spec, HeadUnitEq.mazda_like(spec.fs), cabin_ir(spec.fs, seed), mic_sos(spec.fs), spec.fs)
        # pick the recorder gain from a dry run of the baseline so it peaks near -6 dBFS
        sc.gain = 1.0
        peak = np.max(np.abs(sc._render(np.zeros(sc.eq.n_bands))))
        sc.gain = 0.5 / peak
        return sc

    def true_response_db(self, steps, freq: np.ndarray) -> np.ndarray:
        """Exact magnitude of eq*cabin*mic at ``freq`` (dB), unsmoothed."""
        nfft = 1 << 18
        Hc = np.fft.rfft(self.cabin, nfft)
        fl = np.fft.rfftfreq(nfft, 1 / self.fs)
        cab = np.interp(freq, fl, 20 * np.log10(np.abs(Hc) + 1e-30))
        return cab + sos_magnitude_db(self.mic, freq, self.fs) + self.eq.response_db(steps, freq)

    def true_response_smoothed(self, steps, frac: float = 3.0, freq=None) -> np.ndarray:
        from .measure import LOG_GRID, frac_octave_average
        freq = LOG_GRID if freq is None else freq
        nfft = 1 << 18
        fl = np.fft.rfftfreq(nfft, 1 / self.fs)[1:]
        p = 10 ** (self.true_response_db(steps, fl) / 10)
        return 10 * np.log10(frac_octave_average(fl, p, frac, freq))

    def _render(self, steps, nonlinearity: float = 0.0) -> np.ndarray:
        """Stimulus through EQ, amp nonlinearity, cabin and mic at recorder gain (no clipping)."""
        x, _ = stimulus(self.spec)
        y = self.eq.apply(x, steps)
        if nonlinearity:
            y = y - nonlinearity * y ** 3
        y = signal.fftconvolve(y, self.cabin)[: len(x) + len(self.cabin)]
        y = signal.sosfilt(self.mic, y)
        return y * self.gain

    def record(self, steps, onset_s: float = 0.7, drift_ppm: float = 0.0, snr_db: float | None = 40.0,
               nonlinearity: float = 0.0, tail_s: float = 1.0, seed: int = 1) -> np.ndarray:
        """Produce a fake phone recording of the stimulus played with ``steps`` set."""
        rng = np.random.default_rng(seed)
        y = self._render(steps, nonlinearity)
        if drift_ppm:
            y = lanczos_resample(y, 1.0 + drift_ppm * 1e-6)
        y = np.concatenate([np.zeros(int(onset_s * self.fs)), y, np.zeros(int(tail_s * self.fs))])
        if snr_db is not None:
            sweep_rms = np.sqrt(np.mean(y[int(onset_s * self.fs) + self.spec.n_pre:][: self.spec.n_sweep] ** 2))
            noise = pink_noise(len(y) / self.fs, self.fs, level_dbfs=0.0, seed=int(rng.integers(1 << 30)))
            noise *= sweep_rms * 10 ** (-snr_db / 20) / np.sqrt(np.mean(noise ** 2))
            y = y + noise[: len(y)]
        return np.clip(y, -1.0, 1.0)
