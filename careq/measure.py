"""Recording ingestion: sync, drift correction, deconvolution, windowing, smoothing.

Two stimuli are supported. Swept sines (most of this module) give an impulse
response, hence phase, distortion separation, windowing and large processing
gain. Continuous pink noise (:func:`measure_noise_signal`) gives magnitude
only, but tolerates the microphone moving during acquisition, which makes a
continuous spatial average possible in one take.

Pipeline for one recording (see :func:`measure_recording`):

1. Load mono WAV, resample to the stimulus rate if the recorder used another.
2. Cross-correlate with the sweep to find every sweep onset (no clock sync).
3. Estimate the recorder/player clock mismatch (ppm). With two or more
   sweeps in the file the spacing between their impulse responses is compared
   with the known playback spacing (sub-sample precision, ~1 ppm, no
   assumptions about the cabin). A single sweep gives no clock reference, so
   drift is left at 0 (or the value passed with --drift-ppm); at +-100 ppm
   this costs well under 0.5 dB in a 1/3-octave magnitude within a 500 ms
   window. Each sweep segment is then resampled to correct the drift.
4. Deconvolve with the Farina inverse filter, locate the linear IR peak,
   window it (short pre-window, ~500 ms post-window with a raised-cosine
   tail). Harmonic distortion products land before the pre-window and are
   discarded.
5. FFT -> complex transfer function on a linear grid. Smoothing to a
   fractional-octave log grid is done lazily by :meth:`Measurement.response`.

Everything is *relative*: the mic response, the cabin and the head unit are all
folded into the result. Absolute level is arbitrary.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy import signal
from scipy.fft import next_fast_len, rfft, irfft, rfftfreq

from .signals import SweepSpec, exp_sweep, inverse_filter

# Common log-frequency grid used for smoothed responses, bases and targets.
LOG_GRID = np.geomspace(20.0, 20000.0, 480)
EPS = 1e-30


# --------------------------------------------------------------------------- #
# Smoothed responses on a log grid
# --------------------------------------------------------------------------- #
def frac_octave_average(f_lin: np.ndarray, values: np.ndarray, frac: float,
                        out_freq: np.ndarray = LOG_GRID,
                        weights: np.ndarray | None = None) -> np.ndarray:
    """Average ``values`` (given on a linear frequency grid) over a 1/``frac``
    octave window centred on every ``out_freq``. Optional per-bin weights.

    Where the window spans fewer than two bins (low frequencies with coarse
    FFT resolution) the value is linearly interpolated instead.
    """
    f_lin = np.asarray(f_lin, dtype=float)
    values = np.asarray(values, dtype=float)
    out_freq = np.asarray(out_freq, dtype=float)
    half = 2 ** (1.0 / (2.0 * frac))
    i0 = np.searchsorted(f_lin, out_freq / half, side="left")
    i1 = np.searchsorted(f_lin, out_freq * half, side="right")
    w = np.ones_like(values) if weights is None else np.asarray(weights, dtype=float)
    cw = np.concatenate([[0.0], np.cumsum(w)])
    cwv = np.concatenate([[0.0], np.cumsum(w * values)])
    n = i1 - i0
    sw = cw[i1] - cw[i0]
    with np.errstate(invalid="ignore", divide="ignore"):
        mean = (cwv[i1] - cwv[i0]) / sw
    fallback = np.interp(out_freq, f_lin, values)
    ok = (n >= 2) & (sw > 0) & np.isfinite(mean)
    return np.where(ok, mean, fallback)


@dataclasses.dataclass
class Response:
    """A magnitude response in dB on a frequency grid (usually LOG_GRID)."""

    freq: np.ndarray
    db: np.ndarray
    name: str = ""

    def __post_init__(self):
        self.freq = np.asarray(self.freq, dtype=float)
        self.db = np.asarray(self.db, dtype=float)
        if self.freq.shape != self.db.shape:
            raise ValueError("freq and db must have the same shape")

    def interp(self, freq: np.ndarray = LOG_GRID) -> "Response":
        """Resample onto another grid, linear in log-frequency, flat extrapolation."""
        db = np.interp(np.log(freq), np.log(self.freq), self.db)
        return Response(freq, db, self.name)

    def level(self, f_lo: float = 200.0, f_hi: float = 2000.0) -> float:
        m = (self.freq >= f_lo) & (self.freq <= f_hi)
        return float(np.mean(self.db[m]))

    def normalized(self, f_lo: float = 200.0, f_hi: float = 2000.0) -> "Response":
        return Response(self.freq, self.db - self.level(f_lo, f_hi), self.name)

    def __sub__(self, other: "Response") -> "Response":
        o = other.interp(self.freq)
        return Response(self.freq, self.db - o.db, f"{self.name}-{other.name}")

    def __add__(self, other: "Response") -> "Response":
        o = other.interp(self.freq)
        return Response(self.freq, self.db + o.db, f"{self.name}+{other.name}")

    def to_csv(self, path: str | Path) -> None:
        with open(path, "w") as fh:
            fh.write("frequency,raw\n")
            for f, d in zip(self.freq, self.db):
                fh.write(f"{f:.3f},{d:.4f}\n")

    @classmethod
    def from_csv(cls, path: str | Path, name: str | None = None) -> "Response":
        """Read frequency/dB pairs from a text file.

        Accepts AutoEq CSV (``frequency,raw`` header), HouseCurve ``.txt``
        (``Hz dB`` header, comment lines), REW / UMIK-1 calibration text
        (``freq dB [phase]``, ``"Sens Factor..."`` header line) and any other
        file whose data lines start with two numbers.
        """
        freq, db = [], []
        for line in Path(path).read_text(errors="replace").splitlines():
            parts = line.replace(",", " ").replace("\t", " ").split()
            if len(parts) < 2:
                continue
            try:
                f, d = float(parts[0]), float(parts[1])
            except ValueError:
                continue
            if f > 0:
                freq.append(f)
                db.append(d)
        if len(freq) < 2:
            raise ValueError(f"no numeric frequency/dB pairs found in {path}")
        order = np.argsort(freq)
        return cls(np.asarray(freq)[order], np.asarray(db)[order], name or Path(path).stem)


def average_power(responses: list[Response], freq: np.ndarray = LOG_GRID) -> Response:
    """Power-domain average of several responses (multi-position averaging)."""
    if not responses:
        raise ValueError("no responses to average")
    p = np.mean([10 ** (r.interp(freq).db / 10) for r in responses], axis=0)
    return Response(freq, 10 * np.log10(p + EPS), "average")


# --------------------------------------------------------------------------- #
# Raw signal helpers
# --------------------------------------------------------------------------- #
def load_wav(path: str | Path, fs_target: int | None = None, channel: int = 0) -> tuple[np.ndarray, int]:
    """Load a WAV as float64 mono. Multi-channel files use ``channel``.

    If ``fs_target`` differs from the file rate the signal is resampled
    (polyphase, exact rational ratio)."""
    x, fs = sf.read(str(path), dtype="float64", always_2d=True)
    x = x[:, min(channel, x.shape[1] - 1)]
    if fs_target is not None and fs != fs_target:
        g = np.gcd(int(fs_target), int(fs))
        x = signal.resample_poly(x, int(fs_target) // g, int(fs) // g)
        fs = int(fs_target)
    return x, int(fs)


def resample_by_ratio(x: np.ndarray, ratio: float) -> tuple[np.ndarray, float]:
    """Band-limited (FFT) resampling by a ratio close to 1.

    Returns (signal, ratio actually realised). The realised ratio is quantised
    to 1/len(x), i.e. ~2 ppm for a 10 s segment, which is negligible for
    magnitude measurements."""
    n = len(x)
    m = int(round(n * ratio))
    if m == n:
        return x.copy(), 1.0
    pad = next_fast_len(n)
    xp = np.concatenate([x, np.zeros(pad - n)]) if pad != n else x
    mp = int(round(pad * ratio))
    y = signal.resample(xp, mp)
    return y[:m], mp / pad


def find_onsets(rec: np.ndarray, sweep: np.ndarray, min_separation: int,
                rel_threshold: float = 0.5, max_count: int | None = None) -> tuple[list[int], float]:
    """Locate sweep onsets by cross-correlation with the unit sweep.

    Returns (sorted onset sample indices, peak-to-median correlation ratio of
    the strongest peak, a rough sync quality figure)."""
    c = signal.correlate(rec, sweep, mode="full", method="fft")
    lag0 = len(sweep) - 1
    env = np.abs(c)
    quality = float(env.max() / (np.median(env) + EPS))
    peaks = []
    work = env.copy()
    first = work.max()
    while True:
        i = int(np.argmax(work))
        if work[i] < rel_threshold * first or work[i] <= 0:
            break
        peaks.append(i - lag0)
        lo, hi = max(0, i - min_separation), min(len(work), i + min_separation)
        work[lo:hi] = 0.0
        if max_count is not None and len(peaks) >= max_count:
            break
    return sorted(peaks), quality


def deconvolve(seg: np.ndarray, inv: np.ndarray, _cache: dict | None = None) -> np.ndarray:
    """Full linear convolution of ``seg`` with the inverse filter via FFT."""
    n = len(seg) + len(inv) - 1
    nfft = next_fast_len(n)
    if _cache is not None and nfft in _cache:
        inv_f = _cache[nfft]
    else:
        inv_f = rfft(inv, nfft)
        if _cache is not None:
            _cache[nfft] = inv_f
    return irfft(rfft(seg, nfft) * inv_f, nfft)[:n]


def window_ir(h: np.ndarray, peak: int, fs: int, pre_ms: float = 5.0, post_ms: float = 500.0,
              taper_frac: float = 0.3) -> np.ndarray:
    """Cut ``h`` around ``peak``: half-Hann rise over ``pre_ms``, flat, then a
    half-Hann fall over the last ``taper_frac`` of ``post_ms``. Zero-padded if
    the IR is shorter than the window."""
    n_pre = int(round(pre_ms / 1000 * fs))
    n_post = int(round(post_ms / 1000 * fs))
    start = peak - n_pre
    seg = np.zeros(n_pre + n_post)
    lo, hi = max(0, start), min(len(h), start + len(seg))
    seg[lo - start:hi - start] = h[lo:hi]
    w = np.ones_like(seg)
    if n_pre > 0:
        w[:n_pre] = 0.5 - 0.5 * np.cos(np.pi * np.arange(n_pre) / n_pre)
    n_tap = int(round(taper_frac * n_post))
    if n_tap > 0:
        w[-n_tap:] = 0.5 + 0.5 * np.cos(np.pi * np.arange(n_tap) / n_tap)
    return seg * w


# --------------------------------------------------------------------------- #
# Results
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class SweepResult:
    """One deconvolved sweep."""

    fs: int
    onset: int                 # sample index of the sweep in the (rate-matched) recording
    drift_ppm: float           # recorder clock relative to player clock
    ir: np.ndarray             # windowed impulse response (starts pre_ms before the peak)
    peak_offset: int           # IR peak position relative to the correlation onset (samples)
    f_lin: np.ndarray          # linear frequency grid of H
    H: np.ndarray              # complex transfer function
    noise_H: np.ndarray        # spectrum of an equal-length noise-only window (SNR estimate)
    corr_quality: float        # cross-correlation peak / median
    clip_fraction: float       # fraction of samples at |x| >= 0.99 in the sweep segment

    @property
    def power(self) -> np.ndarray:
        return np.abs(self.H) ** 2

    def response(self, frac: float = 3.0, freq: np.ndarray = LOG_GRID) -> Response:
        return Response(freq, 10 * np.log10(frac_octave_average(self.f_lin, self.power, frac, freq) + EPS))

    def snr_db(self, frac: float = 3.0, freq: np.ndarray = LOG_GRID) -> np.ndarray:
        s = frac_octave_average(self.f_lin, self.power, frac, freq)
        n = frac_octave_average(self.f_lin, np.abs(self.noise_H) ** 2, frac, freq)
        return 10 * np.log10((s + EPS) / (n + EPS))


@dataclasses.dataclass
class Measurement:
    """All sweeps found in one or more recordings, plus the power-averaged spectrum."""

    fs: int
    sweeps: list[SweepResult]
    source: str = ""

    @property
    def f_lin(self) -> np.ndarray:
        return self.sweeps[0].f_lin

    @property
    def power(self) -> np.ndarray:
        return np.mean([s.power for s in self.sweeps], axis=0)

    @property
    def noise_power(self) -> np.ndarray:
        return np.mean([np.abs(s.noise_H) ** 2 for s in self.sweeps], axis=0) / len(self.sweeps)

    def response(self, frac: float = 3.0, freq: np.ndarray = LOG_GRID) -> Response:
        return Response(freq, 10 * np.log10(frac_octave_average(self.f_lin, self.power, frac, freq) + EPS),
                        self.source)

    def snr_db(self, frac: float = 3.0, freq: np.ndarray = LOG_GRID) -> np.ndarray:
        s = frac_octave_average(self.f_lin, self.power, frac, freq)
        n = frac_octave_average(self.f_lin, self.noise_power, frac, freq)
        return 10 * np.log10((s + EPS) / (n + EPS))

    def ir(self) -> np.ndarray:
        """Average windowed impulse response (aligned at the peak)."""
        return np.mean([s.ir for s in self.sweeps], axis=0)

    @staticmethod
    def combine(measurements: list["Measurement"]) -> "Measurement":
        """Pool sweeps from several recordings (e.g. several mic positions)."""
        if not measurements:
            raise ValueError("nothing to combine")
        fs = measurements[0].fs
        if any(m.fs != fs for m in measurements):
            raise ValueError("sample rates differ")
        sweeps = [s for m in measurements for s in m.sweeps]
        return Measurement(fs, sweeps, " + ".join(m.source for m in measurements))

    def save(self, path: str | Path) -> None:
        np.savez_compressed(
            path, fs=self.fs, source=self.source, f_lin=self.f_lin,
            H=np.array([s.H for s in self.sweeps]),
            noise_H=np.array([s.noise_H for s in self.sweeps]),
            ir=np.array([s.ir for s in self.sweeps]),
            meta=np.array([[s.onset, s.drift_ppm, s.peak_offset, s.corr_quality, s.clip_fraction]
                           for s in self.sweeps]),
        )

    @classmethod
    def load(cls, path: str | Path) -> "Measurement":
        z = np.load(path, allow_pickle=False)
        sweeps = []
        for H, nH, ir, meta in zip(z["H"], z["noise_H"], z["ir"], z["meta"]):
            sweeps.append(SweepResult(int(z["fs"]), int(meta[0]), float(meta[1]), ir, int(meta[2]),
                                      z["f_lin"], H, nH, float(meta[3]), float(meta[4])))
        return cls(int(z["fs"]), sweeps, str(z["source"]))


# --------------------------------------------------------------------------- #
# Core per-sweep processing
# --------------------------------------------------------------------------- #
@dataclasses.dataclass
class MeasureOptions:
    pre_ms: float = 20.0
    post_ms: float = 500.0
    taper_frac: float = 0.3
    nfft: int = 2 ** 17
    drift: str | float = "auto"       # "auto" (from the spacing of repeated sweeps), "off" or a fixed ppm
    drift_max_ppm: float = 500.0      # estimates beyond this are clipped (something else is wrong)
    segment_margin_s: float = 0.2     # taken before the correlation onset
    segment_tail_s: float = 1.5       # taken after the sweep end (room tail + noise window)
    noise_window_offset_s: float = 0.9  # where (after the IR peak) the noise-only window starts


def _ir_window_for_sync(rec: np.ndarray, onset: int, spec: SweepSpec, inv: np.ndarray, cache: dict,
                        half_ms: float = 50.0) -> np.ndarray:
    n_sweep = spec.n_sweep
    margin = int(0.2 * spec.fs)
    start, stop = onset - margin, onset + n_sweep + margin
    seg = np.zeros(stop - start)
    lo, hi = max(0, start), min(len(rec), stop)
    seg[lo - start:hi - start] = rec[lo:hi]
    h = deconvolve(seg, inv, cache)
    expect = margin + n_sweep - 1
    n = int(half_ms / 1000 * spec.fs)
    return h[expect - n: expect + n]


def estimate_drift_from_repeats(rec: np.ndarray, onsets: list[int], spec: SweepSpec, inv: np.ndarray,
                                cache: dict | None = None) -> float:
    """Clock offset (ppm) from the spacing of repeated sweeps.

    Consecutive sweeps are ``n_sweep + n_post`` player samples apart. Their
    deconvolved IRs are identical in shape, so cross-correlating them gives the
    recorded spacing to a fraction of a sample. A linear fit of IR position vs
    sweep index over all repeats yields the stretch factor."""
    cache = {} if cache is None else cache
    irs = [_ir_window_for_sync(rec, on, spec, inv, cache) for on in onsets]
    pos = [0.0]
    for k in range(1, len(irs)):
        c = signal.correlate(irs[k], irs[0], mode="full")
        i = int(np.argmax(c))
        d = 0.0
        if 0 < i < len(c) - 1:
            a, b, cc = c[i - 1], c[i], c[i + 1]
            den = a - 2 * b + cc
            d = 0.5 * (a - cc) / den if den != 0 else 0.0
        pos.append(onsets[k] - onsets[0] + (i + d - (len(irs[0]) - 1)))
    nominal = (spec.n_sweep + spec.n_post) * np.arange(len(onsets), dtype=float)
    stretch = float(np.linalg.lstsq(nominal[:, None], np.asarray(pos), rcond=None)[0][0])
    return (stretch - 1.0) * 1e6


def process_sweep(rec: np.ndarray, onset: int, spec: SweepSpec, sweep: np.ndarray, inv: np.ndarray,
                  opts: MeasureOptions, corr_quality: float, cache: dict | None = None,
                  drift_ppm: float | None = None) -> SweepResult:
    """Deconvolve one sweep. ``drift_ppm`` overrides the per-sweep estimate
    (used when the session-wide value from repeated sweeps is known)."""
    fs = spec.fs
    n_sweep = spec.n_sweep
    margin = int(round(opts.segment_margin_s * fs))
    tail = int(round(opts.segment_tail_s * fs))
    start = onset - margin
    stop = onset + n_sweep + tail
    seg = np.zeros(stop - start)
    lo, hi = max(0, start), min(len(rec), stop)
    seg[lo - start:hi - start] = rec[lo:hi]
    local_onset = onset - start
    clip = float(np.mean(np.abs(seg[local_onset:local_onset + n_sweep]) >= 0.99))

    # --- drift -----------------------------------------------------------
    if drift_ppm is not None:
        ppm = float(drift_ppm)
    elif opts.drift in ("auto", "off"):
        ppm = 0.0   # a single sweep gives no clock reference; see estimate_drift_from_repeats
    else:
        ppm = float(opts.drift)
    if ppm != 0.0:
        seg, _ = resample_by_ratio(seg, 1.0 / (1.0 + ppm * 1e-6))
        # re-align precisely after resampling
        on, _ = find_onsets(seg, sweep, n_sweep // 2, max_count=1)
        if on:
            local_onset = on[0]

    # --- deconvolve + window --------------------------------------------
    h = deconvolve(seg, inv, cache)
    expect = local_onset + n_sweep - 1
    win = int(0.02 * fs)
    lo, hi = max(0, expect - win), min(len(h), expect + win)
    peak = lo + int(np.argmax(np.abs(h[lo:hi])))
    ir = window_ir(h, peak, fs, opts.pre_ms, opts.post_ms, opts.taper_frac)
    H = rfft(ir, opts.nfft)
    f_lin = rfftfreq(opts.nfft, 1 / fs)

    # noise-only window of identical shape, taken after the IR has decayed
    n_off = int(round(opts.noise_window_offset_s * fs))
    noise = window_ir(h, peak + n_off, fs, opts.pre_ms, opts.post_ms, opts.taper_frac)
    noise_H = rfft(noise, opts.nfft)

    return SweepResult(fs, onset, ppm, ir, peak - expect, f_lin, H, noise_H, corr_quality, clip)


def measure_signal(rec: np.ndarray, spec: SweepSpec, opts: MeasureOptions | None = None,
                   source: str = "") -> Measurement:
    """Run the full pipeline on an in-memory recording already at ``spec.fs``."""
    opts = opts or MeasureOptions()
    sweep = exp_sweep(spec)
    inv = inverse_filter(spec, sweep)
    onsets, quality = find_onsets(rec, sweep, min_separation=spec.n_sweep // 2)
    if not onsets:
        raise RuntimeError("no sweep found in recording")
    cache: dict = {}
    session_ppm = None
    if opts.drift == "auto" and len(onsets) >= 2:
        session_ppm = estimate_drift_from_repeats(rec, onsets, spec, inv, cache)
        session_ppm = float(np.clip(session_ppm, -opts.drift_max_ppm, opts.drift_max_ppm))
    sweeps = [process_sweep(rec, on, spec, sweep, inv, opts, quality, cache, session_ppm) for on in onsets]
    return Measurement(spec.fs, sweeps, source)


def measure_recording(path: str | Path, spec: SweepSpec, opts: MeasureOptions | None = None,
                      channel: int = 0) -> Measurement:
    """Load a recording (any sample rate) and measure it."""
    rec, _ = load_wav(path, fs_target=spec.fs, channel=channel)
    return measure_signal(rec, spec, opts, source=Path(path).name)


def measure_files(paths: list[str | Path], spec: SweepSpec, opts: MeasureOptions | None = None) -> Measurement:
    """Measure several recordings (e.g. several mic positions) and pool them."""
    ms = []
    for p in paths:
        p = Path(p)
        ms.append(Measurement.load(p) if p.suffix.lower() == ".npz" else measure_recording(p, spec, opts))
    return Measurement.combine(ms)


# --------------------------------------------------------------------------- #
# Continuous-noise (RTA) measurement
# --------------------------------------------------------------------------- #
def trim_to_signal(x: np.ndarray, fs: int, block_s: float = 0.1, drop_db: float = 20.0,
                   guard_s: float = 0.3) -> np.ndarray:
    """Cut leading/trailing silence from a continuous-noise recording.

    Keeps the span of 100 ms blocks within ``drop_db`` of the loudest one, then
    pulls in ``guard_s`` from each end to clear fades and the moment the play
    button was pressed."""
    n = int(round(block_s * fs))
    if len(x) < 4 * n:
        return x
    k = len(x) // n
    rms = np.sqrt(np.mean(x[: k * n].reshape(k, n) ** 2, axis=1) + EPS)
    loud = rms >= rms.max() * 10 ** (-drop_db / 20)
    if not loud.any():
        return x
    i0, i1 = int(np.argmax(loud)) * n, (k - int(np.argmax(loud[::-1]))) * n
    g = int(round(guard_s * fs))
    i0, i1 = i0 + g, i1 - g
    return x[i0:i1] if i1 - i0 > fs else x


def welch_psd(x: np.ndarray, fs: int, nperseg: int = 32768) -> tuple[np.ndarray, np.ndarray]:
    nperseg = min(nperseg, len(x))
    f, p = signal.welch(x, fs=fs, nperseg=nperseg, noverlap=nperseg // 2,
                        window="hann", detrend=False, scaling="density")
    return f, p


@dataclasses.dataclass
class NoiseMeasurement:
    """A continuous-noise (pink) measurement: recording PSD over stimulus PSD."""

    fs: int
    f_lin: np.ndarray
    power: np.ndarray            # recording PSD / stimulus PSD, linear
    noise_power: np.ndarray      # same ratio for the pre-signal silence, for SNR
    source: str = ""
    n_files: int = 1

    def response(self, frac: float = 3.0, freq: np.ndarray = LOG_GRID) -> Response:
        return Response(freq, 10 * np.log10(frac_octave_average(self.f_lin, self.power, frac, freq) + EPS),
                        self.source)

    def snr_db(self, frac: float = 3.0, freq: np.ndarray = LOG_GRID) -> np.ndarray:
        s = frac_octave_average(self.f_lin, self.power, frac, freq)
        n = frac_octave_average(self.f_lin, self.noise_power, frac, freq)
        return 10 * np.log10((s + EPS) / (n + EPS))


def measure_noise_signal(rec: np.ndarray, fs: int, stim: np.ndarray | None = None,
                         nperseg: int = 32768, source: str = "") -> NoiseMeasurement:
    """Response from one continuous-noise recording.

    Magnitude only: the ratio of the recording's power spectrum to the
    stimulus's. No time alignment, so the microphone may be moved throughout,
    which is the point -- a slow pass through the seat volume gives a
    continuous spatial average instead of a handful of discrete positions.

    Unlike a sweep this has no processing gain against steady noise, gives no
    impulse response, no phase and no distortion separation, and cannot be
    windowed to exclude late room energy. Use it for spatial averaging and
    quick verification; use sweeps for identification and for anything
    needing the time domain.
    """
    body = trim_to_signal(rec, fs)
    # silence before the noise starts, for an SNR estimate
    head = rec[: int(0.5 * fs)] if len(rec) > int(1.5 * fs) else body[:1]
    f, p = welch_psd(body, fs, nperseg)
    _, pn = welch_psd(head, fs, min(nperseg, max(256, len(head))))
    pn = np.interp(f, _, pn)
    if stim is not None:
        fs_, ps = welch_psd(stim, fs, nperseg)
        ps = np.interp(f, fs_, ps)
        # Only bins the stimulus actually excites. The bundled pink noise is
        # band-limited to 20 Hz-20 kHz; outside that the ratio is recorder
        # noise over nothing (+40 dB and more), and the 1/3-octave windows
        # centred at 17.8 kHz and above, and at 20 Hz, would average it in.
        keep = ps > ps.max() * 1e-8
        f, p, pn, ps = f[keep], p[keep], pn[keep], ps[keep]
    else:                                        # ideal pink, 1/f power
        ps = np.where(f > 0, 1.0 / np.maximum(f, 1e-9), 1.0)
    ratio = p / (ps + EPS)
    return NoiseMeasurement(fs, f, ratio, pn / (ps + EPS), source)


def measure_noise_files(paths: list[str | Path], fs: int = 48000, stim_path: str | Path | None = None,
                        nperseg: int = 32768) -> NoiseMeasurement:
    """Measure and pool several continuous-noise recordings (power average)."""
    stim = None
    if stim_path is not None:
        stim, _ = load_wav(stim_path, fs_target=fs)
    ms = []
    for p in paths:
        rec, _ = load_wav(p, fs_target=fs)
        ms.append(measure_noise_signal(rec, fs, stim, nperseg, source=Path(p).name))
    f = ms[0].f_lin
    pw = np.mean([np.interp(f, m.f_lin, m.power) for m in ms], axis=0)
    nw = np.mean([np.interp(f, m.f_lin, m.noise_power) for m in ms], axis=0)
    return NoiseMeasurement(fs, f, pw, nw, " + ".join(m.source for m in ms), len(ms))


def apply_mic_cal(resp: Response, cal: Response | None) -> Response:
    """Subtract a microphone calibration curve (UMIK-1 / REW text format)."""
    if cal is None:
        return resp
    return Response(resp.freq, resp.db - cal.interp(resp.freq).db, resp.name)
