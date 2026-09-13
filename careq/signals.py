"""Test-signal generation.

Exponential (Farina) sine sweep, its inverse filter, full stimulus assembly
(silence + sweep, optionally repeated), pink noise for the live-RTA phase, and
WAV export.

Conventions
-----------
* All signals are float64 numpy arrays in the range [-1, 1].
* ``exp_sweep`` returns a unit-amplitude sweep; the stimulus applies the level.
* ``inverse_filter`` is normalised so that ``fftconvolve(sweep, inv)`` has a
  peak of exactly 1.0 at index ``len(sweep) - 1`` (full linear convolution).
  When a recording segment starting at the sweep onset is deconvolved, the
  linear impulse response therefore lands at index ``len(sweep) - 1`` plus the
  acoustic delay, and the k-th harmonic distortion response lands
  ``duration * ln(k) / ln(f2 / f1)`` seconds *before* it (Farina 2000).
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import fftconvolve


@dataclasses.dataclass
class SweepSpec:
    """Parameters that fully define the stimulus (and hence the inverse filter)."""

    fs: int = 48000
    f1: float = 20.0
    f2: float = 20000.0
    duration: float = 10.0
    level_dbfs: float = -12.0
    pre_silence: float = 1.0
    post_silence: float = 2.0
    repeats: int = 3          # >= 2 lets the recorder clock drift be measured from sweep spacing
    fade_in: float = 0.1
    fade_out: float = 0.005

    @property
    def n_sweep(self) -> int:
        return int(round(self.duration * self.fs))

    @property
    def n_pre(self) -> int:
        return int(round(self.pre_silence * self.fs))

    @property
    def n_post(self) -> int:
        return int(round(self.post_silence * self.fs))

    @property
    def amplitude(self) -> float:
        return 10 ** (self.level_dbfs / 20)

    @property
    def log_ratio(self) -> float:
        return float(np.log(self.f2 / self.f1))

    def harmonic_offset(self, k: int) -> float:
        """Seconds *before* the linear IR at which the k-th harmonic IR appears."""
        return self.duration * np.log(k) / self.log_ratio

    def onsets(self) -> list[int]:
        """Sample index of each sweep start within the stimulus file."""
        period = self.n_sweep + self.n_post
        return [self.n_pre + i * period for i in range(self.repeats)]

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "SweepSpec":
        known = {f.name for f in dataclasses.fields(cls)}
        return cls(**{k: v for k, v in d.items() if k in known})

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps({"type": "careq-stimulus", **self.to_dict()}, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "SweepSpec":
        return cls.from_dict(json.loads(Path(path).read_text()))


def _half_hann(n: int, rising: bool) -> np.ndarray:
    if n <= 0:
        return np.zeros(0)
    w = 0.5 - 0.5 * np.cos(np.pi * np.arange(n) / n)
    return w if rising else w[::-1]


def exp_sweep(spec: SweepSpec) -> np.ndarray:
    """Unit-amplitude exponential sine sweep with short raised-cosine fades."""
    n = spec.n_sweep
    t = np.arange(n) / spec.fs
    L = spec.log_ratio
    T = spec.duration
    phase = 2 * np.pi * spec.f1 * T / L * (np.exp(t * L / T) - 1.0)
    x = np.sin(phase)
    n_in = int(round(spec.fade_in * spec.fs))
    n_out = int(round(spec.fade_out * spec.fs))
    if n_in > 0:
        x[:n_in] *= _half_hann(n_in, rising=True)
    if n_out > 0:
        x[-n_out:] *= _half_hann(n_out, rising=False)
    return x


def inverse_filter(spec: SweepSpec, sweep: np.ndarray | None = None) -> np.ndarray:
    """Time-reversed sweep with a -6 dB/oct amplitude envelope (Farina inverse).

    Normalised so that the linear convolution of sweep and inverse filter peaks
    at exactly 1.0 at index ``len(sweep) - 1``.
    """
    if sweep is None:
        sweep = exp_sweep(spec)
    n = len(sweep)
    t = np.arange(n) / spec.fs
    env = np.exp(-t * spec.log_ratio / spec.duration)
    inv = sweep[::-1] * env
    ref = fftconvolve(sweep, inv)
    inv /= ref[n - 1]
    return inv


def stimulus(spec: SweepSpec) -> tuple[np.ndarray, list[int]]:
    """Full playback signal: pre-silence, then ``repeats`` x (sweep, post-silence).

    Returns (signal, onset sample indices).
    """
    sweep = exp_sweep(spec) * spec.amplitude
    parts = [np.zeros(spec.n_pre)]
    for _ in range(spec.repeats):
        parts.append(sweep)
        parts.append(np.zeros(spec.n_post))
    return np.concatenate(parts), spec.onsets()


def pink_noise(duration: float, fs: int, level_dbfs: float = -20.0, f_lo: float = 20.0,
               f_hi: float = 20000.0, seed: int | None = 0) -> np.ndarray:
    """Band-limited pink noise (1/f power) at the given RMS level, FFT-shaped."""
    rng = np.random.default_rng(seed)
    n = int(round(duration * fs))
    spec = rng.standard_normal(n // 2 + 1) + 1j * rng.standard_normal(n // 2 + 1)
    f = np.fft.rfftfreq(n, 1 / fs)
    shape = np.zeros_like(f)
    band = (f >= f_lo) & (f <= f_hi)
    shape[band] = 1 / np.sqrt(f[band])
    x = np.fft.irfft(spec * shape, n)
    x *= 10 ** (level_dbfs / 20) / np.sqrt(np.mean(x ** 2))
    peak = np.max(np.abs(x))
    if peak > 0.99:
        x *= 0.99 / peak
    return x


def write_wav(path: str | Path, x: np.ndarray, fs: int, subtype: str = "PCM_24") -> None:
    x = np.asarray(x, dtype=np.float64)
    if np.max(np.abs(x)) > 1.0:
        raise ValueError("signal exceeds full scale")
    sf.write(str(path), x, fs, subtype=subtype)


def generate(out_dir: str | Path, spec: SweepSpec, pink_seconds: float = 0.0) -> dict[str, Path]:
    """Write the stimulus WAV(s) and the stimulus.json needed to process recordings."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    x, _ = stimulus(spec)
    paths = {}
    wav = out / f"careq_sweep_{spec.fs // 1000}k_{int(spec.duration)}s_x{spec.repeats}.wav"
    write_wav(wav, x, spec.fs)
    paths["sweep"] = wav
    meta = out / "stimulus.json"
    spec.save(meta)
    paths["stimulus"] = meta
    if pink_seconds > 0:
        pn = out / f"careq_pink_{spec.fs // 1000}k_{int(pink_seconds)}s.wav"
        write_wav(pn, pink_noise(pink_seconds, spec.fs), spec.fs)
        paths["pink"] = pn
    return paths
