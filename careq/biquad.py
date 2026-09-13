"""RBJ cookbook biquads as scipy second-order sections, plus magnitude helpers."""
from __future__ import annotations

import numpy as np
from scipy import signal


def _sos(b, a):
    return np.array([[b[0] / a[0], b[1] / a[0], b[2] / a[0], 1.0, a[1] / a[0], a[2] / a[0]]])


def peaking_sos(fc: float, q: float, gain_db: float, fs: int) -> np.ndarray:
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    return _sos([1 + alpha * A, -2 * c, 1 - alpha * A], [1 + alpha / A, -2 * c, 1 - alpha / A])


def low_shelf_sos(fc: float, q: float, gain_db: float, fs: int) -> np.ndarray:
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    s = 2 * np.sqrt(A) * alpha
    b = [A * ((A + 1) - (A - 1) * c + s), 2 * A * ((A - 1) - (A + 1) * c), A * ((A + 1) - (A - 1) * c - s)]
    a = [(A + 1) + (A - 1) * c + s, -2 * ((A - 1) + (A + 1) * c), (A + 1) + (A - 1) * c - s]
    return _sos(b, a)


def high_shelf_sos(fc: float, q: float, gain_db: float, fs: int) -> np.ndarray:
    A = 10 ** (gain_db / 40)
    w0 = 2 * np.pi * fc / fs
    alpha = np.sin(w0) / (2 * q)
    c = np.cos(w0)
    s = 2 * np.sqrt(A) * alpha
    b = [A * ((A + 1) + (A - 1) * c + s), -2 * A * ((A - 1) + (A + 1) * c), A * ((A + 1) + (A - 1) * c - s)]
    a = [(A + 1) - (A - 1) * c + s, 2 * ((A - 1) - (A + 1) * c), (A + 1) - (A - 1) * c - s]
    return _sos(b, a)


def sos_magnitude_db(sos: np.ndarray, freq: np.ndarray, fs: int) -> np.ndarray:
    _, h = signal.sosfreqz(sos, worN=freq, fs=fs)
    return 20 * np.log10(np.abs(h) + 1e-30)


def peaking_magnitude_db(freq: np.ndarray, fc: float, q: float, gain_db: float, fs: int = 48000) -> np.ndarray:
    """Magnitude (dB) of a digital RBJ peaking filter at ``fs``."""
    if gain_db == 0:
        return np.zeros_like(np.asarray(freq, dtype=float))
    return sos_magnitude_db(peaking_sos(fc, q, gain_db, fs), np.asarray(freq, dtype=float), fs)
