"""Is the head unit's EQ minimum phase? Test it against the measured phase.

The ratio R = H_band / H_baseline is the EQ filter on its own: the cabin, the
microphone and the rest of the chain are common to both recordings and cancel.
If the EQ is a minimum-phase biquad, arg(R) is fully determined by |R| through
the Hilbert transform, up to a pure delay (the two files are aligned only to
the sample their IR peak landed on).

So: derive the minimum phase implied by the measured magnitude, divide it out,
allow one free delay, and look at what is left. That residual is the excess
phase. It is only meaningful next to a control -- baseline2 / baseline, the
same condition recorded twice with no EQ change, through identical code and
identical masks. That is the repeatability floor. Run from the repo root:

    .venv/bin/python results/minphase/check_minphase.py

See docs/minphase.md for the results and for why bands 1 and 13 are reported
as undecidable rather than as numbers.
"""
import numpy as np, sys
sys.path.insert(0, '.')
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
from careq.signals import SweepSpec
from careq.measure import measure_recording, MeasureOptions, frac_octave_average

REC = Path("Recordings/Session_5_cal_mic")
OUT = Path("results/minphase")
GRID = np.geomspace(20, 20000, 600)
TAUS = np.arange(-1e-3, 1e-3, 2e-7)     # delay search, ~1/20 sample resolution
SNR_MIN = 15.0                          # dB, per-band and baseline
LO, HI = 25.0, 19000.0                  # trusted edges of the swept band
# Bands 1 (40 Hz) and 13 (16 kHz) are deliberately absent: see docs/minphase.md.
BANDS = [(5, "B5P9.wav", 250.0), (9, "B9P9.wav", 2500.0)]

spec = SweepSpec.load("stimulus/stimulus.json")
opts = MeasureOptions()


def tf(name):
    """Coherently averaged complex transfer function, plus noise power.

    Coherent (not power) averaging is the point: every IR in a file is windowed
    around its own peak, so the sweeps are aligned and their phase survives.
    """
    m = measure_recording(REC / name, spec, opts)
    H = np.array([s.H for s in m.sweeps])
    noise = np.array([np.abs(s.noise_H) ** 2 for s in m.sweeps]).mean(axis=0)
    coherent_loss = 10 * np.log10(np.abs(H.mean(axis=0)) ** 2
                                  / (np.abs(H) ** 2).mean(axis=0) + 1e-30)
    return m.sweeps[0].f_lin, H.mean(axis=0), (np.abs(H) ** 2).mean(axis=0), noise, coherent_loss


def smooth_c(f, Z, frac=12.0):
    """Vector-average a complex spectrum into 1/12-octave bands."""
    return (frac_octave_average(f, Z.real, frac, GRID)
            + 1j * frac_octave_average(f, Z.imag, frac, GRID))


def min_phase(mag, f, nfft):
    """Minimum phase implied by a magnitude, via the real cepstrum.

    Outside the swept band the ratio is unmeasured, so the magnitude is eased
    to unity over half an octave rather than clamping a boosted value flat to
    DC, which would invent a shelf the head unit does not have.
    """
    taper = (np.clip(np.log2(GRID / (LO / 2 ** .5)) / .5, 0, 1)
             * np.clip(np.log2((HI * 2 ** .5) / GRID) / .5, 0, 1))
    m_lin = np.interp(f, GRID, 1.0 + (mag - 1.0) * taper, left=1.0, right=1.0)
    c = np.fft.irfft(np.log(np.maximum(m_lin, 1e-12)), n=nfft)
    w = np.zeros(nfft)
    w[0] = 1.0
    w[1:nfft // 2] = 2.0
    w[nfft // 2] = 1.0
    phi = np.angle(np.exp(np.fft.rfft(c * w, n=nfft)))
    # minimum phase carries no delay term, so it is smooth and safe to unwrap
    return np.interp(GRID, f, np.unwrap(phi))


def excess_phase(f, H_num, H_den, nfft, good, inactive):
    """Phase of H_num/H_den left over once its own minimum phase and one
    delay are removed. The measured phase is never unwrapped: unwrapping runs
    through out-of-band noise and drags wrap errors into the passband."""
    R = smooth_c(f, H_num / H_den)
    mag = np.abs(R) / np.median(np.abs(R)[inactive])      # kill level drift
    phi = min_phase(mag, f, nfft)
    e = R / np.abs(R) * np.exp(-1j * phi)
    # one free delay, by circular regression with equal weight per octave
    z = good[None, :] * e[None, :] * np.exp(2j * np.pi * np.outer(TAUS, GRID))
    tau = TAUS[np.argmax(np.abs(z.sum(axis=1)))]
    r = e * np.exp(2j * np.pi * GRID * tau)
    k = np.argmax(good)
    return mag, np.angle(r * np.conj(r[k] / abs(r[k]))), phi, tau


def masks(fc, snr_base, snr_band):
    good = (GRID >= 30) & (GRID <= 18000) & (snr_base > SNR_MIN) & (snr_band > SNR_MIN)
    return (good,
            good & (GRID > fc / 2 ** .75) & (GRID < fc * 2 ** .75),          # active
            good & ~((GRID > fc / 2 ** 1.5) & (GRID < fc * 2 ** 1.5)))       # inactive


f, Hb, Pb, Nb, loss = tf("baseline.wav")
_, Hb2, _, _, _ = tf("baseline2.wav")
nfft = 2 * (len(f) - 1)
snr_b = np.interp(GRID, f, 10 * np.log10(Pb / (Nb + 1e-30)))
mid = (f > 100) & (f < 10000)
print(f"baseline.wav coherent-average loss {loss[mid].mean():+.2f} dB "
      f"(0 dB = the three sweeps agree in phase)\n")

print(f"{'band':>5} {'centre':>8} {'gain':>8} | {'excess rms':>11} {'control':>9} | "
      f"{'GD peak meas':>13} {'min-phase':>10} {'delay':>9}")
print("-" * 86)

fig, axes = plt.subplots(2, len(BANDS), figsize=(5.5 * len(BANDS), 7), squeeze=False)
for col, (b, fname, fc) in enumerate(BANDS):
    _, Hk, Pk, Nk, _ = tf(fname)
    snr_k = np.interp(GRID, f, 10 * np.log10(Pk / (Nk + 1e-30)))
    good, active, inactive = masks(fc, snr_b, snr_k)

    mag, res, phi, tau = excess_phase(f, Hk, Hb, nfft, good, inactive)
    _, res_ctl, _, _ = excess_phase(f, Hb2, Hb, nfft, good, inactive)

    idx = np.where(active)[0]
    sl = slice(idx[0], idx[-1] + 1)
    ph_m = np.unwrap(np.angle(smooth_c(f, Hk / Hb)[sl])) - 2 * np.pi * GRID[sl] * tau
    gd_meas = -np.gradient(ph_m, 2 * np.pi * GRID[sl]) * 1e3
    gd_min = -np.gradient(phi[sl], 2 * np.pi * GRID[sl]) * 1e3
    i = np.argmax(np.abs(gd_min))

    deg = lambda x: np.degrees(np.sqrt(np.mean(x[active] ** 2)))
    print(f"{b:>5} {fc:>7.0f}H {20*np.log10(mag[np.argmin(abs(GRID-fc))]):>+6.1f}dB | "
          f"{deg(res):>9.1f}d {deg(res_ctl):>7.1f}d | "
          f"{gd_meas[i]:>10.2f}ms {gd_min[i]:>8.2f}ms {tau*1e6:>7.1f}us")

    ax = axes[0][col]
    ax.semilogx(GRID, 20 * np.log10(mag), color="#2a78d6", label="measured |R|")
    ax.axvspan(GRID[active][0], GRID[active][-1], color="#2a78d6", alpha=.08)
    ax.set_title(f"Band {b} at {fc:.0f} Hz, +9 steps")
    ax.set_ylabel("dB"); ax.set_xlim(30, 18000); ax.grid(alpha=.3); ax.legend(fontsize=8)

    ax = axes[1][col]
    ax.semilogx(GRID, np.degrees(res), color="#d64a2a", label="excess phase (EQ)")
    ax.semilogx(GRID, np.degrees(res_ctl), color="#888", lw=.9,
                label="control (baseline2 / baseline)")
    ax.axvspan(GRID[active][0], GRID[active][-1], color="#2a78d6", alpha=.08)
    ax.set_xlim(30, 18000); ax.set_ylim(-60, 60); ax.grid(alpha=.3)
    ax.set_xlabel("Hz"); ax.set_ylabel("degrees"); ax.legend(fontsize=8)

fig.suptitle("Head-unit EQ vs the minimum phase implied by its own magnitude", fontsize=11)
fig.tight_layout()
fig.savefig(OUT / "minphase.png", dpi=110)
print(f"\nwrote {OUT / 'minphase.png'}")
