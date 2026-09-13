"""Fit integer band settings so that baseline + EQ approaches a target curve.

error(f) = baseline(f) + sum_k g_k * per_step_k(f) + c - target(f)

``c`` is a free level offset (the EQ cannot change overall level, and level is
arbitrary anyway). Bounded, weighted least squares gives the continuous
solution; rounding plus integer coordinate descent repairs rounding damage.
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

    def summary(self) -> str:
        lines = ["band  label    cont   int"]
        for i, (lab, c, g) in enumerate(zip(self.labels_hz, self.steps_cont, self.steps_int)):
            lines.append(f"{i + 1:>4}  {('%g' % lab) if lab else '-':>6}  {c:5.2f}  {g:+d}")
        lines.append("")
        lines.append(f"weighted RMS error vs target: before {self.rms_before:.2f} dB, "
                     f"continuous {self.rms_cont:.2f} dB, integer {self.rms_int:.2f} dB "
                     f"({100 * (1 - self.rms_int / self.rms_before):.0f}% reduction)")
        lines.append("settings (left to right): " + " ".join(f"{g:+d}" for g in self.steps_int))
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "type": "careq-fit",
            "steps": [int(g) for g in self.steps_int],
            "steps_continuous": [round(float(g), 3) for g in self.steps_cont],
            "labels_hz": self.labels_hz,
            "rms_db": {"before": round(self.rms_before, 3), "continuous": round(self.rms_cont, 3),
                       "integer": round(self.rms_int, 3)},
            "freq": [round(float(f), 3) for f in self.freq],
            "baseline_db": [round(float(x), 3) for x in self.baseline.db],
            "predicted_db": [round(float(x), 3) for x in self.predicted_int.db],
            "target_db": [round(float(x), 3) for x in self.target.db],
        }


def _offset(resid_no_c: np.ndarray, w: np.ndarray) -> float:
    return float(-np.sum(w * resid_no_c) / np.sum(w))


def integer_refine(A: np.ndarray, d: np.ndarray, w: np.ndarray, g0: np.ndarray, max_step: int,
                   max_passes: int = 50) -> tuple[np.ndarray, float]:
    """Coordinate descent on integer steps, +-1 moves, offset re-solved each time.

    ``d`` = target - baseline. Minimises weighted RMS of A g + c - d."""
    g = g0.astype(int).copy()

    def cost(gv):
        r = A @ gv - d
        return weighted_rms(r + _offset(r, w), w)

    best = cost(g)
    for _ in range(max_passes):
        improved = False
        for k in range(len(g)):
            for delta in (+1, -1):
                cand = g.copy()
                cand[k] += delta
                if abs(cand[k]) > max_step:
                    continue
                c = cost(cand)
                if c < best - 1e-9:
                    g, best, improved = cand, c, True
        if not improved:
            break
    return g, best


def fit_eq(baseline: Response, model: EqModel, target: Response, weights: np.ndarray | None = None,
           max_step: int = 9, norm_range: tuple[float, float] = (200.0, 2000.0)) -> FitResult:
    freq = model.freq
    b = baseline.interp(freq).normalized(*norm_range)
    t = target.interp(freq).normalized(*norm_range)
    w = default_weights(freq) if weights is None else np.asarray(weights, dtype=float)
    A = model.per_step_matrix()
    d = t.db - b.db
    n = model.n_bands

    sw = np.sqrt(w)
    A_aug = np.hstack([A, np.ones((len(freq), 1))]) * sw[:, None]
    res = lsq_linear(A_aug, d * sw, bounds=([-max_step] * n + [-np.inf], [max_step] * n + [np.inf]))
    g_cont, c_cont = res.x[:n], float(res.x[n])

    rms_before = weighted_rms(-d + _offset(-d, w), w)
    r_cont = A @ g_cont - d
    rms_cont = weighted_rms(r_cont + _offset(r_cont, w), w)

    g_int, rms_int = integer_refine(A, d, w, np.round(g_cont), max_step)
    r_int = A @ g_int - d
    c_int = _offset(r_int, w)

    labels = [bnd.label_hz for bnd in model.bands]
    return FitResult(
        freq, b, t, w, g_cont, g_int, c_cont, c_int, rms_before, rms_cont, rms_int,
        Response(freq, b.db + A @ g_cont + c_cont, "predicted (continuous)"),
        Response(freq, b.db + A @ g_int + c_int, "predicted"),
        labels,
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
    ax.semilogx(result.freq, result.baseline.db, color=blue, linewidth=2, label="measured (EQ flat)")
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
