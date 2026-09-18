"""Synthetic car: known cabin IR, known 13-band head-unit EQ, known mic tilt.

Used by the tests (ground truth for every stage) and by ``careq simulate`` to
produce realistic fake recordings for dry runs.

Signal chain: stimulus -> head-unit EQ (measured-like: peaking filters,
asymmetric cuts, soft gain limiter; see HeadUnitEq) -> optional amp nonlinearity
-> cabin IR -> mic response -> recorder clock drift -> onset offset + tail ->
pink noise.
"""
from __future__ import annotations

import dataclasses

import numpy as np
from scipy import signal

from .signals import SweepSpec, stimulus, pink_noise


from .biquad import peaking_sos, low_shelf_sos, high_shelf_sos, sos_magnitude_db, peaking_magnitude_db  # noqa: E402


# --------------------------------------------------------------------------- #
# Head-unit EQ
# --------------------------------------------------------------------------- #
def soft_limit_db(x: np.ndarray, knee_db: float, cap_db: float) -> np.ndarray:
    """Odd, monotonic soft limiter on a dB gain curve: identity up to
    ``knee_db``, then tanh-compressed so it never exceeds ``cap_db``."""
    x = np.asarray(x, dtype=float)
    a = np.abs(x)
    over = a > knee_db
    out = a.copy()
    out[over] = knee_db + (cap_db - knee_db) * np.tanh((a[over] - knee_db) / (cap_db - knee_db))
    return np.sign(x) * out


def minimum_phase_fir(mag_db: np.ndarray, nfft: int) -> np.ndarray:
    """Minimum-phase FIR (length ``nfft``) with the given magnitude (dB) on
    the ``rfftfreq(nfft)`` grid, via the real cepstrum."""
    log_mag = np.log(10 ** (np.asarray(mag_db, dtype=float) / 20) + 1e-12)
    cep = np.fft.irfft(log_mag, nfft)
    fold = np.zeros(nfft)
    fold[0] = cep[0]
    fold[1:nfft // 2] = 2 * cep[1:nfft // 2]
    fold[nfft // 2] = cep[nfft // 2]
    return np.fft.irfft(np.exp(np.fft.rfft(fold)), nfft)


@dataclasses.dataclass
class HeadUnitEq:
    """13 peaking filters at fixed centres with per-band Q and dB-per-step,
    a cut/boost asymmetry and a soft limiter on the summed gain curve.

    The limiter is what makes adjacent bands stop adding: the real Mazda unit
    delivers a ~10 dB plateau for two neighbours at +9 where the sum of the
    two single-band curves is ~12 dB (session 2, 2026-09-13). The summed
    magnitude is realised as a minimum-phase FIR, so the EQ is still a
    linear, time-invariant filter for any one setting."""

    fs: int
    fc: np.ndarray
    q: np.ndarray
    db_per_step: np.ndarray
    cut_factor: float = 1.0       # gain of a cut relative to the same boost
    knee_db: float = np.inf       # soft limiter starts here ...
    cap_db: float = np.inf        # ... and never exceeds this
    nfft: int = 16384

    @classmethod
    def mazda_like(cls, fs: int = 48000) -> "HeadUnitEq":
        """Centres, Q, dB/step, cut factor and limiter as measured on a 2021
        Mazda 3 (sessions 1-2, 2026-09-13); see docs/session2_results.md."""
        fc = np.array([40, 63, 100, 160, 250, 500, 1000, 1600, 2500, 4000, 6300, 10000, 16000], dtype=float)
        q = np.array([1.7, 2.0, 2.2, 2.5, 2.1, 2.0, 1.8, 1.8, 2.6, 2.1, 2.8, 1.5, 0.75])
        db = np.array([0.84, 0.92, 0.91, 0.95, 0.84, 0.88, 0.80, 0.85, 0.92, 1.01, 0.84, 0.96, 0.92])
        # cut_factor 0.98 here shows up as ~0.93 after 1/3-octave power
        # smoothing (smoothing shrinks a cut more than a boost), which is what
        # identify measured on the car; the fit works in the smoothed domain.
        return cls(fs, fc, q, db, cut_factor=0.98, knee_db=7.0, cap_db=10.5)

    @classmethod
    def ideal(cls, fs: int = 48000) -> "HeadUnitEq":
        """Independent peaking filters that add exactly (the pre-session model)."""
        eq = cls.mazda_like(fs)
        return cls(fs, eq.fc, eq.q, eq.db_per_step)

    @property
    def n_bands(self) -> int:
        return len(self.fc)

    @property
    def _grid(self) -> np.ndarray:
        return np.fft.rfftfreq(self.nfft, 1 / self.fs)

    def gains_db(self, steps) -> np.ndarray:
        steps = np.asarray(steps, dtype=float)
        return np.where(steps < 0, self.cut_factor, 1.0) * steps * self.db_per_step

    def _mag_db(self, steps, freq: np.ndarray) -> np.ndarray:
        total = np.zeros_like(freq, dtype=float)
        for fc, q, g in zip(self.fc, self.q, self.gains_db(steps)):
            if g != 0:
                total += peaking_magnitude_db(freq, fc, q, g, self.fs)
        if np.isfinite(self.cap_db):
            total = soft_limit_db(total, self.knee_db, self.cap_db)
        return total

    def response_db(self, steps, freq: np.ndarray) -> np.ndarray:
        """Exact magnitude (dB) of the EQ at ``freq``."""
        grid = self._grid
        return np.interp(np.asarray(freq, dtype=float), grid, self._mag_db(steps, grid))

    def impulse_response(self, steps) -> np.ndarray:
        return minimum_phase_fir(self._mag_db(steps, self._grid), self.nfft)

    def apply(self, x: np.ndarray, steps) -> np.ndarray:
        if not np.any(np.asarray(steps)):
            return x.copy()
        return signal.fftconvolve(x, self.impulse_response(steps))[: len(x)]


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
# Woofer excursion limit
# --------------------------------------------------------------------------- #
def woofer_saturation(x: np.ndarray, fs: int, drive: float, f_split: float = 30.0) -> np.ndarray:
    """Level-dependent compression and distortion in the bottom octaves.

    A door woofer runs out of excursion long before anything else does, so as
    the volume rises it delivers progressively less output below ~50 Hz and
    generates harmonics there, while the midrange is untouched. Measured on
    the car on 2026-09-17: band 1 at +9 delivered 1.9 dB less at 35-40 Hz at
    Mazda volume 50 than at volume 30, tapering to 0.24 dB by 63 Hz and
    nothing at all by 80 Hz, with distortion at 40 Hz rising from 1.8 % to
    7.5 % (`docs/level.md`).

    The limit is on *excursion*, not on pressure, and for a given sound
    pressure cone displacement rises as 1/f squared. So the saturation is
    applied to a displacement proxy, the signal through a second-order
    low-pass at ``f_split`` which falls 12 dB per octave above it, and the
    compression it produces is then returned to the pressure domain. That
    puts the loss at the bottom of the range rather than at the cabin-gain
    peak, which is what the car does.

    ``drive`` 0 is linear; the compression grows with the product of
    ``drive`` and the displacement amplitude, so raising the playback level
    engages it exactly as turning the volume up does.
    """
    if drive <= 0:
        return x
    sos = signal.butter(2, f_split, "lowpass", fs=fs, output="sos")
    disp = signal.sosfilt(sos, x)                      # displacement proxy
    loss = disp - np.tanh(disp * drive) / drive        # what the excursion limit removes
    return x - signal.sosfilt(signal.butter(2, f_split, "highpass", fs=fs, output="sos"), loss)


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
    woofer_drive: float = 0.0   # 0 = linear bass; see woofer_saturation

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

    def _render(self, steps, nonlinearity: float = 0.0, playback_db: float = 0.0) -> np.ndarray:
        """Stimulus through EQ, amp nonlinearity, woofer, cabin and mic.

        ``playback_db`` raises the level presented to the woofer, i.e. turns
        the volume up. The recorder gain is divided back out so the recorded
        level is unchanged and only the nonlinearity differs, which is what a
        level-linearity comparison wants."""
        x, _ = stimulus(self.spec)
        y = self.eq.apply(x, steps)
        if nonlinearity:
            y = y - nonlinearity * y ** 3
        k = 10 ** (playback_db / 20)
        if k != 1.0:
            y = y * k
        y = woofer_saturation(y, self.fs, self.woofer_drive)
        y = signal.fftconvolve(y, self.cabin)[: len(x) + len(self.cabin)]
        y = signal.sosfilt(self.mic, y)
        return y * self.gain / k

    def record(self, steps, onset_s: float = 0.7, drift_ppm: float = 0.0, snr_db: float | None = 40.0,
               nonlinearity: float = 0.0, tail_s: float = 1.0, seed: int = 1,
               playback_db: float = 0.0) -> np.ndarray:
        """Produce a fake recording of the stimulus played with ``steps`` set.

        ``playback_db`` turns the volume up into the woofer's excursion limit
        without changing the recorded level; use it to exercise the
        level-linearity check."""
        rng = np.random.default_rng(seed)
        y = self._render(steps, nonlinearity, playback_db)
        if drift_ppm:
            y = lanczos_resample(y, 1.0 + drift_ppm * 1e-6)
        y = np.concatenate([np.zeros(int(onset_s * self.fs)), y, np.zeros(int(tail_s * self.fs))])
        if snr_db is not None:
            sweep_rms = np.sqrt(np.mean(y[int(onset_s * self.fs) + self.spec.n_pre:][: self.spec.n_sweep] ** 2))
            noise = pink_noise(len(y) / self.fs, self.fs, level_dbfs=0.0, seed=int(rng.integers(1 << 30)))
            noise *= sweep_rms * 10 ** (-snr_db / 20) / np.sqrt(np.mean(noise ** 2))
            y = y + noise[: len(y)]
        return np.clip(y, -1.0, 1.0)
