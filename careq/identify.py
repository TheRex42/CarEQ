"""System identification of the head unit's graphic EQ.

Given a baseline measurement (all bands at 0) and one measurement per band
with that band at a known setting (normally +9), recover each band's basis
curve

    basis_k(f) = 10 log10( P_k(f) / P_baseline(f) )

bin-by-bin on the linear FFT grid (the cabin and mic cancel exactly there,
provided the phone did not move), then smooth to a fractional-octave log grid.
Bins where the baseline sits in a deep null get down-weighted because their
ratio is dominated by noise.

Optional extra runs (same band at -9, or at +3) are turned into symmetry and
linearity checks and stored in the model's notes. The fit assumes
``gain_db(f) = steps * per_step_db(f)`` unless those checks say otherwise.

The model is written to ``eq_model.json``.
"""
from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

from .biquad import peaking_magnitude_db
from .measure import LOG_GRID, EPS, Measurement, Response, frac_octave_average

N_BANDS_DEFAULT = 13
# Slider labels only; the shapes are measured. Verify against the head unit
# screen -- these are a guess for the 2019+ Mazda Connect 13-band EQ.
DEFAULT_LABELS_HZ = [40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000]


def basis_from_measurements(band: Measurement, baseline: Measurement, frac: float = 3.0,
                            freq: np.ndarray = LOG_GRID) -> np.ndarray:
    """dB difference band/baseline: both power spectra are smoothed to ``freq``
    first, then divided. This is exactly the quantity the fit adds to the
    smoothed baseline, so predictions stay consistent."""
    if not np.array_equal(band.f_lin, baseline.f_lin):
        raise ValueError("measurements must share the same FFT grid")
    p_k = frac_octave_average(band.f_lin, band.power, frac, freq)
    p_b = frac_octave_average(baseline.f_lin, baseline.power, frac, freq)
    return 10 * np.log10((p_k + EPS) / (p_b + EPS))


def level_offset_db(basis: np.ndarray, freq: np.ndarray = LOG_GRID, f_lo: float = 40.0, f_hi: float = 16000.0) -> float:
    """Median of a basis over the audio band. One band at +9 leaves most of the
    band untouched, so this should be ~0; a large value means the recorder gain
    changed between recordings (AGC?) or the phone moved."""
    m = (freq >= f_lo) & (freq <= f_hi)
    return float(np.median(basis[m]))


def fit_peaking(freq: np.ndarray, db: np.ndarray, fc0: float | None = None, fs: int = 48000) -> dict:
    """Describe a measured basis as one digital peaking filter (at ``fs``):
    {fc, q, gain_db, rms_err_db}. Diagnostic only; the fit uses the measured curve."""
    i = int(np.argmax(np.abs(db)))
    fc0 = fc0 or float(freq[i])
    g0 = float(db[i])

    def resid(p):
        return peaking_magnitude_db(freq, np.exp(p[0]), np.exp(p[1]), p[2], fs) - db

    r = least_squares(resid, [np.log(fc0), np.log(1.4), g0],
                      bounds=([np.log(10.0), np.log(0.2), -30], [np.log(0.49 * fs), np.log(10.0), 30]))
    return {"fc": float(np.exp(r.x[0])), "q": float(np.exp(r.x[1])), "gain_db": float(r.x[2]),
            "rms_err_db": float(np.sqrt(np.mean(r.fun ** 2)))}


@dataclasses.dataclass
class Band:
    index: int                    # 0-based band number as shown on the head unit (left to right)
    label_hz: float | None
    ident_steps: int              # setting used for the primary run (normally +9)
    basis_db: np.ndarray          # measured curve at ident_steps
    checks: list[dict] = dataclasses.field(default_factory=list)
    shape: dict | None = None     # peaking-filter description of per_step_db * 9

    @property
    def per_step_db(self) -> np.ndarray:
        return self.basis_db / self.ident_steps


@dataclasses.dataclass
class EqModel:
    freq: np.ndarray
    bands: list[Band]
    notes: dict = dataclasses.field(default_factory=dict)

    @property
    def n_bands(self) -> int:
        return len(self.bands)

    def per_step_matrix(self, freq: np.ndarray | None = None) -> np.ndarray:
        """(n_freq, n_bands) matrix A such that eq_db = A @ steps."""
        cols = []
        for b in self.bands:
            r = Response(self.freq, b.per_step_db)
            cols.append(r.interp(freq).db if freq is not None else b.per_step_db)
        return np.stack(cols, axis=1)

    def eq_response(self, steps, freq: np.ndarray | None = None) -> Response:
        f = self.freq if freq is None else freq
        return Response(f, self.per_step_matrix(freq) @ np.asarray(steps, dtype=float), "eq")

    def predict(self, baseline: Response, steps) -> Response:
        b = baseline.interp(self.freq)
        return Response(self.freq, b.db + self.per_step_matrix() @ np.asarray(steps, dtype=float), "predicted")

    def describe(self) -> str:
        lines = ["band  label     fc(Hz)   Q     dB/step  peak@ident  fit-err"]
        for b in self.bands:
            s = b.shape or {}
            lab = f"{b.label_hz:g}" if b.label_hz else "-"
            lines.append(f"{b.index + 1:>4}  {lab:>7}  {s.get('fc', float('nan')):7.0f}  "
                         f"{s.get('q', float('nan')):4.2f}  {s.get('gain_db', float('nan')) / 9:7.2f}  "
                         f"{np.max(np.abs(b.basis_db)):9.2f}  {s.get('rms_err_db', float('nan')):6.2f}")
        for k, v in self.notes.items():
            lines.append(f"{k}: {v}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "type": "careq-eq-model",
            "freq": [round(float(f), 3) for f in self.freq],
            "bands": [{
                "index": b.index, "label_hz": b.label_hz, "ident_steps": b.ident_steps,
                "basis_db": [round(float(x), 4) for x in b.basis_db],
                "checks": b.checks, "shape": b.shape,
            } for b in self.bands],
            "notes": self.notes,
        }

    def save(self, path: str | Path) -> None:
        Path(path).write_text(json.dumps(self.to_dict(), indent=1))

    @classmethod
    def load(cls, path: str | Path) -> "EqModel":
        d = json.loads(Path(path).read_text())
        freq = np.asarray(d["freq"], dtype=float)
        bands = [Band(b["index"], b.get("label_hz"), b["ident_steps"], np.asarray(b["basis_db"]),
                      b.get("checks", []), b.get("shape")) for b in d["bands"]]
        return cls(freq, bands, d.get("notes", {}))


def _rms(x: np.ndarray, freq: np.ndarray, f_lo: float, f_hi: float) -> float:
    m = (freq >= f_lo) & (freq <= f_hi)
    return float(np.sqrt(np.mean(x[m] ** 2)))


def identify(baseline: Measurement, runs: list[tuple[int, int, Measurement]], n_bands: int = N_BANDS_DEFAULT,
             labels_hz: list[float] | None = None, frac: float = 3.0,
             check_range: tuple[float, float] = (40.0, 16000.0), level_warn_db: float = 0.75) -> EqModel:
    """Build an :class:`EqModel` from a baseline and per-band runs.

    ``runs`` is a list of (band_index, steps, measurement). For every band the
    run with the largest |steps| becomes the basis; other runs become
    symmetry/linearity checks.
    """
    labels = labels_hz if labels_hz is not None else (DEFAULT_LABELS_HZ if n_bands == N_BANDS_DEFAULT else [None] * n_bands)
    by_band: dict[int, list[tuple[int, Measurement]]] = {}
    for idx, steps, m in runs:
        if not 0 <= idx < n_bands:
            raise ValueError(f"band index {idx} out of range 0..{n_bands - 1}")
        if steps == 0:
            raise ValueError("a band run must use a non-zero setting")
        by_band.setdefault(idx, []).append((steps, m))
    missing = [i for i in range(n_bands) if i not in by_band]

    bands: list[Band] = []
    sym_err, lin_err = [], []
    level_warnings: list[int] = []
    for idx in range(n_bands):
        if idx in missing:
            bands.append(Band(idx, labels[idx], 9, np.zeros_like(LOG_GRID), [{"warning": "not measured"}]))
            continue
        items = sorted(by_band[idx], key=lambda t: -abs(t[0]))
        steps0, m0 = items[0]
        basis = basis_from_measurements(m0, baseline, frac)
        band = Band(idx, labels[idx], steps0, basis)
        off = level_offset_db(basis)
        if abs(off) > level_warn_db:
            band.checks.append({"warning": f"level offset {off:+.2f} dB vs baseline - recorder gain changed (AGC?) "
                                           f"or phone moved; basis not trusted"})
            level_warnings.append(idx + 1)
        band.shape = fit_peaking(LOG_GRID, basis / steps0 * 9)
        per_step = basis / steps0
        for steps, m in items[1:]:
            other = basis_from_measurements(m, baseline, frac)
            dev = other - per_step * steps
            err = _rms(dev, LOG_GRID, *check_range)
            kind = "symmetry" if np.sign(steps) != np.sign(steps0) else "linearity"
            band.checks.append({"steps": steps, "kind": kind, "rms_dev_db": round(err, 3),
                                "max_dev_db": round(float(np.max(np.abs(dev[(LOG_GRID >= check_range[0]) & (LOG_GRID <= check_range[1])]))), 3)})
            (sym_err if kind == "symmetry" else lin_err).append(err)
        bands.append(band)

    notes: dict = {"smoothing": f"1/{frac:g} octave", "check_range_hz": list(check_range)}
    if missing:
        notes["missing_bands"] = [i + 1 for i in missing]
    if level_warnings:
        notes["level_offset_warning_bands"] = level_warnings
    if sym_err:
        notes["symmetry_rms_db"] = round(float(np.mean(sym_err)), 3)
        notes["symmetry_ok"] = bool(max(sym_err) < 0.75)
    if lin_err:
        notes["linearity_rms_db"] = round(float(np.mean(lin_err)), 3)
        notes["linearity_ok"] = bool(max(lin_err) < 0.75)
    snr = baseline.snr_db(frac)
    m = (LOG_GRID >= 40) & (LOG_GRID <= 16000)
    notes["baseline_min_snr_db_40_16k"] = round(float(np.min(snr[m])), 1)
    notes["drift_ppm"] = [round(s.drift_ppm, 1) for s in baseline.sweeps]
    return EqModel(LOG_GRID.copy(), bands, notes)
