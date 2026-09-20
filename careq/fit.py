"""Fit integer band settings so that baseline + EQ approaches a target curve.

error(f) = measured(f) + sum_k per_step_k(f) * (e(x_k) - e(cur_k)) + c - target(f)

``x`` are the settings to find, ``cur`` the settings the measurement was made
with (all zero for a flat-EQ baseline), ``c`` a free level offset (the EQ
cannot change overall level, and level is arbitrary anyway) and

    e(x) = gain_scale * (cut_factor if x < 0 else 1) * x

the effective step count. ``gain_scale`` (default 0.95) is how much of the
single-band gain the head unit delivers when several bands are set at once,
``cut_factor`` (default 0.93, or the value identify measured) how deep a cut
is relative to the same boost; both from the 2021 Mazda 3 sessions of
2026-09-13 (with ALC off two adjacent bands at +9 reach 95-98 % of the sum
of their single-band curves; with ALC on it was 84 %). ``max_boost`` caps
positive steps separately:
boosts eat digital headroom in the head unit and can hit its limiter on
loud material, so cuts are preferred where the fit has the choice. Bounded weighted least squares gives the continuous solution
(re-solved until the signs, which pick the cut factor, are stable); rounding
plus integer coordinate descent repairs rounding damage.

Because the real unit does not superpose exactly, the first fit is an
approximation: measure again with the fitted settings in place and refit
with ``current=`` those settings (``careq fit --current``). The second pass
corrects what the first one missed.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import numpy as np
from scipy.optimize import lsq_linear

from .identify import EqModel
from .measure import LOG_GRID, Response

TARGET_DIR = Path(__file__).parent / "targets"


def list_targets() -> list[str]:
    return sorted(p.stem for p in TARGET_DIR.glob("*.csv"))


def load_target(name_or_path: str | Path, freq: np.ndarray = LOG_GRID) -> Response:
    """Load a target by file path or by the name of a bundled target."""
    p = Path(name_or_path)
    if not p.exists():
        cand = TARGET_DIR / f"{name_or_path}.csv"
        if not cand.exists():
            raise FileNotFoundError(f"target '{name_or_path}' not found; bundled: {list_targets()}")
        p = cand
    return Response.from_csv(p).interp(freq)


def default_weights(freq: np.ndarray = LOG_GRID, f_lo: float = 60.0, f_hi: float = 12000.0,
                    floor: float = 0.05, f_min: float = 30.0, f_max: float = 16000.0) -> np.ndarray:
    """Fit weights: 1.0 inside [f_lo, f_hi], tapering (linearly in log f) to
    ``floor`` at f_min / f_max and staying at ``floor`` beyond. Below ~30 Hz a
    phone mic and the cabin's pressure response dominate, above ~16 kHz the
    mic; neither is what the EQ should chase."""
    lf = np.log(freq)
    w = np.ones_like(freq)
    lo = freq < f_lo
    w[lo] = floor + (1 - floor) * np.clip((lf[lo] - np.log(f_min)) / (np.log(f_lo) - np.log(f_min)), 0, 1)
    hi = freq > f_hi
    w[hi] = floor + (1 - floor) * np.clip((np.log(f_max) - lf[hi]) / (np.log(f_max) - np.log(f_hi)), 0, 1)
    return w


def weighted_rms(resid: np.ndarray, w: np.ndarray) -> float:
    return float(np.sqrt(np.sum(w * resid ** 2) / np.sum(w)))


# Glasberg & Moore (1990): ERB(f) = 24.7 * (4.37 f / 1000 + 1) Hz, so the ERB
# *number* is 21.4 log10(4.37 f / 1000 + 1) and its derivative with respect to
# log f is proportional to f / (f + 228.8).
ERB_F0 = 1000.0 / 4.37      # 228.8 Hz


def erb_density(freq: np.ndarray = LOG_GRID) -> np.ndarray:
    """Auditory bandwidths per unit log-frequency, normalised to 1 well above
    ``ERB_F0``.

    Auditory filter bandwidth is roughly constant below ~500 Hz and
    proportional to frequency above it, so the number of resolvable bands per
    octave falls away in the bass. An error evaluated on a log-uniform grid
    gives every octave equal weight, which over-weights the bass relative to
    how the ear divides the spectrum: the midpoint of 20 Hz-20 kHz is 632 Hz
    on a log axis and about 2 kHz on an ERB axis. Multiplying the fit weights
    by this restores the ear's proportions.

    It measures frequency *resolution*, not importance, so it is reported
    alongside the log-uniform number rather than replacing it.
    """
    f = np.asarray(freq, dtype=float)
    return f / (f + ERB_F0)


def erb_weights(freq: np.ndarray = LOG_GRID, **kw) -> np.ndarray:
    """``default_weights`` scaled by :func:`erb_density`."""
    return default_weights(freq, **kw) * erb_density(freq)


@dataclasses.dataclass
class FitResult:
    freq: np.ndarray
    baseline: Response        # normalised
    target: Response          # normalised
    weights: np.ndarray
    steps_cont: np.ndarray
    steps_int: np.ndarray
    offset_cont: float
    offset_int: float
    rms_before: float
    rms_cont: float
    rms_int: float
    predicted_cont: Response
    predicted_int: Response
    labels_hz: list
    current: np.ndarray = None       # settings the measurement was made with
    gain_scale: float = 1.0
    cut_factor: float = 1.0
    erb_weighted: bool = False       # whether `weights` already include erb_density

    @property
    def change(self) -> np.ndarray:
        return self.steps_int - self.current

    @property
    def band_weights(self) -> np.ndarray:
        """The band-limit weights alone, with any ERB scaling divided back out."""
        return self.weights / erb_density(self.freq) if self.erb_weighted else self.weights

    def errors(self, erb: bool = False) -> tuple[float, float]:
        """(before, after) weighted RMS vs target, with a free level offset.

        ``erb=False`` weights every octave equally, which is what a log
        frequency axis shows. ``erb=True`` scales by auditory bandwidth
        density so the weighting matches how the ear divides the spectrum;
        see :func:`erb_density`. Both are available whichever one the fit
        optimised."""
        w = self.band_weights * (erb_density(self.freq) if erb else 1.0)

        def e(db):
            r = np.asarray(db) - self.target.db
            return weighted_rms(r - np.sum(w * r) / np.sum(w), w)

        return e(self.baseline.db), e(self.predicted_int.db)

    def erb_errors(self) -> tuple[float, float]:
        return self.errors(erb=True)

    def summary(self) -> str:
        iterating = np.any(self.current != 0)
        lines = ["band  label    cont   int" + ("  (was  change)" if iterating else "")]
        for i, (lab, c, g, cur) in enumerate(zip(self.labels_hz, self.steps_cont, self.steps_int, self.current)):
            extra = f"  ({cur:+d}  {g - cur:+d})" if iterating else ""
            lines.append(f"{i + 1:>4}  {('%g' % lab) if lab else '-':>6}  {c:5.2f}  {g:+d}{extra}")
        lines.append("")
        lines.append(f"gain scale {self.gain_scale:.2f}, cut factor {self.cut_factor:.2f}")
        opt = "auditory bandwidth" if self.erb_weighted else "equal per octave"
        lines.append(f"weighted RMS error vs target ({opt}, optimised): before {self.rms_before:.2f} dB, "
                     f"continuous {self.rms_cont:.2f} dB, integer {self.rms_int:.2f} dB "
                     f"({100 * (1 - self.rms_int / self.rms_before):.0f}% reduction)")
        ob, oa = self.errors(erb=not self.erb_weighted)
        other = "equal per octave" if self.erb_weighted else "auditory bandwidth"
        lines.append(f"  same settings, {other}: before {ob:.2f} dB, integer {oa:.2f} dB "
                     f"({100 * (1 - oa / ob):.0f}% reduction)")
        lines.append("settings (left to right): " + " ".join(f"{g:+d}" for g in self.steps_int))
        if iterating:
            lines.append("change from current:      " + " ".join(f"{g:+d}" for g in self.change))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "type": "careq-fit",
            "steps": [int(g) for g in self.steps_int],
            "steps_continuous": [round(float(g), 3) for g in self.steps_cont],
            "current": [int(g) for g in self.current],
            "change": [int(g) for g in self.change],
            "gain_scale": self.gain_scale, "cut_factor": self.cut_factor,
            "labels_hz": self.labels_hz,
            "rms_db": {"before": round(self.rms_before, 3), "continuous": round(self.rms_cont, 3),
                       "integer": round(self.rms_int, 3)},
            "rms_erb_db": dict(zip(("before", "integer"), [round(v, 3) for v in self.errors(erb=True)])),
            "rms_log_db": dict(zip(("before", "integer"), [round(v, 3) for v in self.errors(erb=False)])),
            "optimised_weighting": "erb" if self.erb_weighted else "log",
            "freq": [round(float(f), 3) for f in self.freq],
            "baseline_db": [round(float(x), 3) for x in self.baseline.db],
            "predicted_db": [round(float(x), 3) for x in self.predicted_int.db],
            "target_db": [round(float(x), 3) for x in self.target.db],
        }


def _offset(resid_no_c: np.ndarray, w: np.ndarray) -> float:
    return float(-np.sum(w * resid_no_c) / np.sum(w))


def effective_steps(x, gain_scale: float = 1.0, cut_factor: float = 1.0) -> np.ndarray:
    """e(x): what the head unit delivers, in units of the identified per-step curve."""
    x = np.asarray(x, dtype=float)
    return gain_scale * np.where(x < 0, cut_factor, 1.0) * x


def integer_refine(predict, d: np.ndarray, w: np.ndarray, g0: np.ndarray, max_step: int,
                   max_passes: int = 50, max_boost: int | None = None) -> tuple[np.ndarray, float]:
    """Coordinate descent on integer steps, +-1 moves, offset re-solved each time.

    ``predict(g)`` returns the EQ curve for integer settings ``g``; ``d`` is
    what it should equal. Minimises weighted RMS of predict(g) + c - d."""
    g = g0.astype(int).copy()
    max_boost = max_step if max_boost is None else max_boost
    g = np.clip(g, -max_step, max_boost)

    def cost(gv):
        r = predict(gv) - d
        return weighted_rms(r + _offset(r, w), w)

    best = cost(g)
    for _ in range(max_passes):
        improved = False
        for k in range(len(g)):
            for delta in (+1, -1):
                cand = g.copy()
                cand[k] += delta
                if cand[k] > max_boost or cand[k] < -max_step:
                    continue
                c = cost(cand)
                if c < best - 1e-9:
                    g, best, improved = cand, c, True
        if not improved:
            break
    return g, best


DEFAULT_GAIN_SCALE = 0.95
DEFAULT_CUT_FACTOR = 0.93


def fit_eq(baseline: Response, model: EqModel, target: Response, weights: np.ndarray | None = None,
           max_step: int = 9, norm_range: tuple[float, float] = (200.0, 2000.0),
           current=None, gain_scale: float = DEFAULT_GAIN_SCALE, cut_factor: float | None = None,
           max_boost: int | None = None, erb_weighted: bool = False) -> FitResult:
    """Fit settings so that ``baseline`` (measured with ``current`` set, default
    all zero) plus the change in EQ approaches ``target``. ``cut_factor``
    defaults to the value identify stored in the model's notes, else 0.93.
    ``max_boost`` (default ``max_step``) limits positive steps separately.
    Set ``erb_weighted`` when ``weights`` already include :func:`erb_density`,
    so the summary can report both weightings without double-counting."""
    max_boost = max_step if max_boost is None else min(max_boost, max_step)
    freq = model.freq
    n = model.n_bands
    b = baseline.interp(freq).normalized(*norm_range)
    t = target.interp(freq).normalized(*norm_range)
    w = default_weights(freq) if weights is None else np.asarray(weights, dtype=float)
    A = model.per_step_matrix()
    cur = np.zeros(n, dtype=int) if current is None else np.asarray(current, dtype=int)
    if cur.shape != (n,):
        raise ValueError(f"current must have {n} entries")
    if np.any(np.abs(cur) > max_step):
        raise ValueError("current settings exceed max_step")
    if cut_factor is None:
        cut_factor = float(model.notes.get("cut_factor", DEFAULT_CUT_FACTOR))
    e = lambda x: effective_steps(x, gain_scale, cut_factor)
    predict = lambda x: A @ e(x)

    d = t.db - b.db                      # what the EQ *change* must supply
    d_abs = d + predict(cur)             # what the absolute settings must supply
    sw = np.sqrt(w)

    # continuous: bounded LSQ, columns scaled by e'(x); re-solve until the
    # signs (which choose the cut factor) stop changing
    scale = np.full(n, gain_scale)
    for _ in range(8):
        A_aug = np.hstack([A * scale, np.ones((len(freq), 1))]) * sw[:, None]
        res = lsq_linear(A_aug, d_abs * sw, bounds=([-max_step] * n + [-np.inf], [max_boost] * n + [np.inf]))
        g_cont, c_cont = res.x[:n], float(res.x[n])
        new_scale = gain_scale * np.where(g_cont < 0, cut_factor, 1.0)
        if np.allclose(new_scale, scale):
            break
        scale = new_scale

    rms_before = weighted_rms(-d + _offset(-d, w), w)
    r_cont = predict(g_cont) - d_abs
    rms_cont = weighted_rms(r_cont + _offset(r_cont, w), w)

    g_int, rms_int = integer_refine(predict, d_abs, w, np.round(g_cont), max_step, max_boost=max_boost)
    r_int = predict(g_int) - d_abs
    c_int = _offset(r_int, w)

    labels = [bnd.label_hz for bnd in model.bands]
    return FitResult(
        freq, b, t, w, g_cont, g_int, c_cont, c_int, rms_before, rms_cont, rms_int,
        Response(freq, b.db + predict(g_cont) - predict(cur) + c_cont, "predicted (continuous)"),
        Response(freq, b.db + predict(g_int) - predict(cur) + c_int, "predicted"),
        labels, cur, gain_scale, cut_factor, erb_weighted,
    )


def plot_fit(result: FitResult, path: str | Path, title: str = "") -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import ticker

    blue, orange, aqua, ink, muted = "#2a78d6", "#eb6834", "#1baf7a", "#0b0b0b", "#8a8985"
    fig, (ax, axb) = plt.subplots(2, 1, figsize=(10, 8), gridspec_kw={"height_ratios": [3, 1]})
    fig.patch.set_facecolor("#fcfcfb")
    for a in (ax, axb):
        a.set_facecolor("#fcfcfb")
        a.grid(True, which="major", color="#e6e5e1", linewidth=0.8)
        a.grid(True, which="minor", color="#f0efec", linewidth=0.5)
        for s in ("top", "right"):
            a.spines[s].set_visible(False)
    ax.semilogx(result.freq, result.target.db, color=ink, linestyle="--", linewidth=1.5, label="target")
    ax.semilogx(result.freq, result.baseline.db, color=blue, linewidth=2,
                label="measured (EQ flat)" if not np.any(result.current) else "measured (current EQ)")
    ax.semilogx(result.freq, result.predicted_int.db, color=orange, linewidth=2, label="predicted with fitted EQ")
    ax.semilogx(result.freq, result.predicted_int.db - result.target.db, color=aqua, linewidth=1.5,
                label="residual (predicted - target)")
    ax.set_xlim(20, 20000)
    ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.set_ylabel("dB (relative)")
    ax.set_title(title or "Before / predicted after / target", loc="left")
    ax.legend(frameon=False, loc="lower left")
    ax.text(0.99, 0.02, f"weighted RMS: {result.rms_before:.2f} dB -> {result.rms_int:.2f} dB",
            transform=ax.transAxes, ha="right", va="bottom", color=muted)

    x = np.arange(len(result.steps_int))
    axb.bar(x, result.steps_int, width=0.6, color=orange, edgecolor="#fcfcfb", linewidth=2)
    axb.plot(x, result.steps_cont, linestyle="none", marker="o", markersize=5, color=ink, label="continuous")
    axb.set_xticks(x)
    axb.set_xticklabels([f"{i + 1}\n{('%g' % l) if l else ''}" for i, l in enumerate(result.labels_hz)])
    axb.set_ylim(-9.5, 9.5)
    axb.set_ylabel("steps")
    axb.set_xlabel("band / label (Hz)")
    for xi, g in zip(x, result.steps_int):
        axb.text(xi, g + (0.4 if g >= 0 else -0.4), f"{g:+d}", ha="center", va="bottom" if g >= 0 else "top",
                 fontsize=9, color=ink)
    axb.legend(frameon=False, loc="upper right")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
