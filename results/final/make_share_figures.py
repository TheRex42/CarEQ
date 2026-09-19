"""Shareable figures for other owners: one per profile plus an overview.

Profiles revised 2026-09-18: By ear, Harman in-car, Trained listener (see docs/targets.md).

Reads only committed data (the calibrated session 6 baseline, the band model,
the targets and settings.json) and writes
results/final/share/*.png.

    .venv/bin/python results/final/make_share_figures.py
"""
import json, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, '.')
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker
from careq.measure import Response, LOG_GRID as G
from careq.identify import EqModel
from careq.fit import load_target, default_weights, weighted_rms, effective_steps

OUT = Path("results/final/share"); OUT.mkdir(parents=True, exist_ok=True)

# palette: reference categorical slots 1-3 (validated all-pairs), text/surface tokens
SURFACE, INK, INK2, MUTED, GRID = "#fcfcfb", "#0b0b0b", "#52514e", "#8a8985", "#e6e5e1"
FLAT = "#a3a29c"
CUT, BOOST, MID = "#2a78d6", "#e34948", "#f0efec"      # diverging pair + neutral midpoint
PROFILES = [  # key, name, target, blurb, colour
    ("A  By ear", "By ear", "mazda_by_ear",
     "the owner's by-ear preference: +4 dB bass shelf, flat mids, treble falling 3.25 dB/octave above 4 kHz", "#2a78d6"),
    ("B  Harman in-car", "Harman in-car", "olive_welti_car",
     "Olive & Welti's in-car target (Harman research): about +8 dB bass, flat mids, -5 dB at 20 kHz", "#eb6834"),
    ("C  Trained listener", "Trained listener", "olive2013_room_trained",
     "Olive et al. 2013, trained listeners' preferred room curve: +3.5 dB bass, treble falling to -5 dB", "#1baf7a"),
]
VERIFIED = ("Predicted from per-band measurements of this head unit. Checked the same way, the first "
            "calibrated profile measured 1.81 dB from its target against 1.93 predicted.")
LABELS = ["40", "63", "100", "160", "250", "500", "1k", "1.6k", "2.5k", "4k", "6.3k", "10k", "16k"]
CAR = "2021 Mazda3 Hatchback, standard (non-Bose) audio"
CONDITIONS = ("Settings for the head unit's 13-band Customize EQ, with ALC off and fader/balance centred.\n"
              "Measured at the driver's seat with a calibrated microphone (Dayton iMM-6) in one car, at volume 30.")
CAVEAT = ("One car, one seat. Yours will differ somewhat, and targets are taste: "
          "treat these as a measured starting point, not a measurement of your car.")

plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": INK, "axes.labelcolor": INK2,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.edgecolor": GRID,
                     "figure.facecolor": SURFACE, "axes.facecolor": SURFACE})

settings = json.load(open("results/final/settings.json"))
model = EqModel.load("results/session3/eq_model.json"); A = model.per_step_matrix()
w = default_weights(G)
band = (G >= 200) & (G <= 2000)


def norm(db):
    return db - db[band].mean()


flat = norm(Response.from_csv("results/session6/baseline_move_pooled.csv").interp(G).db)


def predicted(steps):
    return norm(flat + A @ effective_steps(np.array(steps), 0.95, 0.93))


def werr(db, tgt):
    r = db - tgt; r = r - np.sum(w * r) / np.sum(w)
    return weighted_rms(r, w)


def freq_axis(ax):
    ax.set_xscale("log"); ax.set_xlim(25, 20000)
    ax.set_xticks([30, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v / 1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.xaxis.set_minor_formatter(ticker.NullFormatter())
    ax.grid(True, which="major", color=GRID, lw=0.7); ax.grid(True, which="minor", axis="x", color=GRID, lw=0.35)
    ax.set_xlabel("Frequency, Hz", fontsize=10)
    for s in ("top", "right"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0, labelsize=9.5)


def reach_note(ax, y):
    ax.axvspan(25, 45, color=MID, zorder=0, lw=0)
    # bottom of the band: every curve sits above about -13 dB from 29 Hz up, so the note never collides
    ax.text(29, -15.5, "below what the\ndoor speakers\ncan reach", fontsize=7.5, color=MUTED, va="top")


def slider_axes(ax, steps, colour):
    x = np.arange(13)
    ax.bar(x, steps, 0.62, color=colour, zorder=3, linewidth=0)
    ax.axhline(0, color=INK2, lw=0.9, zorder=4)
    for xi, v in zip(x, steps):
        ax.text(xi, v + (0.55 if v >= 0 else -0.55), f"{v:+d}" if v else "0", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=13, weight="bold", color=INK)
    ax.set_ylim(-12, 9.5); ax.set_yticks([-9, -6, -3, 0, 3, 6, 9])
    ax.set_xticks(x); ax.set_xticklabels([f"{l} Hz" for l in LABELS], fontsize=9.5)
    ax.set_xlim(-0.6, 12.6)
    ax.grid(True, axis="y", color=GRID, lw=0.7, zorder=0)
    for s in ("top", "right", "bottom"): ax.spines[s].set_visible(False)
    ax.tick_params(length=0, labelsize=9.5); ax.set_ylabel("EQ step", fontsize=10)


def header(fig, title, sub):
    fig.text(0.035, 0.965, title, fontsize=19 if len(title) <= 62 else 16.5, weight="bold", va="top")
    fig.text(0.035, 0.925, sub, fontsize=11.5, color=INK2, va="top")


def footer(fig, extra=""):
    fig.text(0.035, 0.035, CONDITIONS + ("\n" + extra if extra else "") + "\n" + CAVEAT,
             fontsize=8.8, color=INK2, va="bottom", linespacing=1.5)


# ---- one figure per profile --------------------------------------------------
def profile_figure(name, tname, blurb, col, steps, note):
    tgt = norm(load_target(tname).interp(G).db)
    pred = predicted(steps)
    after = pred
    e0, e1 = werr(flat, tgt), werr(after, tgt)

    fig = plt.figure(figsize=(12, 10.2))
    header(fig, f"{name} EQ  ·  {CAR}", f"Target: {blurb}")
    gs = fig.add_gridspec(2, 1, height_ratios=[1, 1.35], hspace=0.42, left=0.075, right=0.965, top=0.845, bottom=0.17)

    ax = fig.add_subplot(gs[0]); slider_axes(ax, steps, col)
    ax.set_title("Set the sliders", loc="left", fontsize=12.5, color=INK, pad=12)

    ax = fig.add_subplot(gs[1]); freq_axis(ax)
    reach_note(ax, 13.5)
    ax.plot(G, tgt, color=INK, lw=1.4, ls=(0, (5, 3)), label="target", zorder=3)
    ax.plot(G, flat, color=FLAT, lw=1.6, label="EQ flat (measured)", zorder=2)
    ax.plot(G, after, color=col, lw=2.2, zorder=4, label=f"{name} set (predicted)")
    ax.set_ylim(-20, max(15, float(np.ceil(tgt[G >= 25].max() + 1.5)))); ax.set_ylabel("Level, dB (relative)", fontsize=10); freq_axis(ax)
    ax.legend(frameon=False, fontsize=9.5, loc="lower center", ncol=3, bbox_to_anchor=(0.5, -0.02))
    # selective direct labels: the cabin hump and what the EQ did to it
    i = np.argmin(np.abs(G - 85))
    ax.annotate("cabin bass hump", (G[i], flat[i]), (160, 12.5), fontsize=9, color=INK2,
                arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
    ax.set_title(f"What it does at the driver's seat   ·   error vs target {e0:.1f} dB flat → {e1:.1f} dB predicted",
                 loc="left", fontsize=12.5, color=INK, pad=12)
    footer(fig, note)
    fig.savefig(OUT / f"mazda3_eq_{slug(name)}.png", dpi=150)
    plt.close(fig)


def slug(name):
    return name.lower().replace(' ', '_').replace('-', '_')


for key, name, tname, blurb, col in PROFILES:
    profile_figure(name, tname, blurb, col, settings[key], VERIFIED)

# ---- overview ------------------------------------------------------------------
fig = plt.figure(figsize=(14, 11))
header(fig, f"Three measured EQ profiles  ·  {CAR}",
       "All three cut the cabin bass hump and let the treble fall. By ear is the owner's choice; the other two are\n"
       "published research targets that bracket it: Harman in-car has more bass, Trained listener a slightly darker top.")
gs = fig.add_gridspec(2, 1, height_ratios=[0.62, 1.25], hspace=0.30, left=0.19, right=0.965, top=0.80, bottom=0.165)

ax = fig.add_subplot(gs[0])
for r, (key, name, tname, blurb, col) in enumerate(PROFILES):
    steps = settings[key]
    for c, v in enumerate(steps):
        t = min(abs(v) / 9, 1) * 0.62
        pole = np.array(matplotlib.colors.to_rgb(BOOST if v > 0 else CUT))
        fill = (1 - t) * np.array(matplotlib.colors.to_rgb(MID)) + t * pole
        ax.add_patch(plt.Rectangle((c + 0.04, r + 0.06), 0.92, 0.88, color=fill, lw=0))
        ax.text(c + 0.5, r + 0.5, f"{v:+d}" if v else "0", ha="center", va="center", fontsize=14, weight="bold", color=INK)
    ax.add_patch(plt.Rectangle((-2.42, r + 0.2), 0.14, 0.6, color=col, lw=0, clip_on=False))
    ax.text(-2.2, r + 0.5, name, ha="left", va="center", fontsize=12.5, weight="bold", color=INK, clip_on=False)
ax.set_xlim(0, 13); ax.set_ylim(3, 0)
ax.set_xticks(np.arange(13) + 0.5); ax.set_xticklabels([f"{l} Hz" for l in LABELS], fontsize=10)
ax.xaxis.tick_top(); ax.set_yticks([]); ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("EQ steps  (blue = cut, red = boost)", loc="left", fontsize=12.5, pad=30, x=-0.185)

ax = fig.add_subplot(gs[1]); freq_axis(ax); reach_note(ax, 14)
ax.plot(G, flat, color=FLAT, lw=1.6, label="EQ flat (measured)", zorder=2)
ends = []
for key, name, tname, blurb, col in PROFILES:
    ax.plot(G, predicted(settings[key]), color=col, lw=2.1, label=f"{name} (predicted)", zorder=3)
ax.set_ylim(-20, 15.5); ax.set_ylabel("Level, dB (relative)", fontsize=10); freq_axis(ax)
ax.legend(frameon=False, fontsize=10, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02))
i = np.argmin(np.abs(G - 85))
ax.annotate("cabin bass hump, EQ flat", (G[i], flat[i]), (170, 13), fontsize=9, color=INK2,
            arrowprops=dict(arrowstyle="-", color=MUTED, lw=0.8))
ax.set_title("Response at the driver's seat", loc="left", fontsize=12.5, pad=12)
errs = []
for key, name, tname, blurb, col in PROFILES:
    tgt = norm(load_target(tname).interp(G).db)
    after = predicted(settings[key])
    errs.append(f"{name} {werr(flat, tgt):.1f} → {werr(after, tgt):.1f} dB")
footer(fig, "Error vs each profile's own target, flat → set (predicted):  " + "   ·   ".join(errs) + "\n" + VERIFIED)
fig.savefig(OUT / "mazda3_eq_overview.png", dpi=150)
plt.close(fig)
print("wrote", *sorted(p.name for p in OUT.glob("*.png")))


# ---- ResoNix (added 2026-09-18) -------------------------------------------------
# Nick Apicella / ResoNix Sound Solutions publishes REW house curves for car audio
# (careq/targets/resonix_*.csv, provenance in their headers). Fitted here with the
# same model, baseline and +6 boost cap as the final profiles.
from careq.fit import fit_eq
VIOLET, MAGENTA = "#4a3aa7", "#e87ba4"      # categorical slots 7 and 5; with blue: worst CVD dE 13, normal 16.3
RESONIX = [  # name, target, blurb, colour
    ("ResoNix 2026", "resonix_2026",
     "ResoNix Sound Solutions' current car target: about +10 dB bass, a 4-6 dB dip at 2-3 kHz, treble -3 dB", VIOLET),
    ("ResoNix Laid Back", "resonix_laid_back_2025",
     "ResoNix's 2025 'Laid Back' car target: about +10 dB bass, 2-3 kHz dip, treble -5 to -6 dB", MAGENTA),
]
RESONIX_NOTE = ("ResoNix targets are written for DSP systems with a subwoofer; below 45 Hz this car's door speakers cannot follow, "
                "and their 2-3 kHz dip is tuned to the author's own car.\n" + VERIFIED)
model_steps = {}
for name, tname, blurb, col in RESONIX:
    f = fit_eq(Response.from_csv("results/session6/baseline_move_pooled.csv"), model, load_target(tname), max_boost=6)
    model_steps[name] = [int(v) for v in f.steps_int]
    profile_figure(name, tname, blurb, col, model_steps[name], RESONIX_NOTE)
json.dump(model_steps, open("results/final/resonix_settings.json", "w"), indent=1)

rows = [("By ear", settings["A  By ear"], PROFILES[0][4], "mazda_by_ear")] + \
       [(n, model_steps[n], c, t) for n, t, b, c in RESONIX]
fig = plt.figure(figsize=(14, 11))
header(fig, f"ResoNix car targets vs By ear  ·  {CAR}",
       "ResoNix's published car curves ask for about twice the bass and a 2-3 kHz dip. On this head unit that means\n"
       "cutting 1-2.5 kHz to the limit, so they fit less closely than the owner's or the research targets.")
gs = fig.add_gridspec(2, 1, height_ratios=[0.62, 1.25], hspace=0.30, left=0.19, right=0.965, top=0.80, bottom=0.165)
ax = fig.add_subplot(gs[0])
for r, (name, steps, col, tname) in enumerate(rows):
    for c, v in enumerate(steps):
        t = min(abs(v) / 9, 1) * 0.62
        pole = np.array(matplotlib.colors.to_rgb(BOOST if v > 0 else CUT))
        fill = (1 - t) * np.array(matplotlib.colors.to_rgb(MID)) + t * pole
        ax.add_patch(plt.Rectangle((c + 0.04, r + 0.06), 0.92, 0.88, color=fill, lw=0))
        ax.text(c + 0.5, r + 0.5, f"{v:+d}" if v else "0", ha="center", va="center", fontsize=14, weight="bold", color=INK)
    ax.add_patch(plt.Rectangle((-2.42, r + 0.2), 0.14, 0.6, color=col, lw=0, clip_on=False))
    ax.text(-2.2, r + 0.5, name, ha="left", va="center", fontsize=12.5, weight="bold", color=INK, clip_on=False)
ax.set_xlim(0, 13); ax.set_ylim(3, 0)
ax.set_xticks(np.arange(13) + 0.5); ax.set_xticklabels([f"{l} Hz" for l in LABELS], fontsize=10)
ax.xaxis.tick_top(); ax.set_yticks([]); ax.tick_params(length=0)
for sp in ax.spines.values(): sp.set_visible(False)
ax.set_title("EQ steps  (blue = cut, red = boost)", loc="left", fontsize=12.5, pad=30, x=-0.185)
ax = fig.add_subplot(gs[1]); freq_axis(ax); reach_note(ax, 14)
ax.plot(G, flat, color=FLAT, lw=1.6, label="EQ flat (measured)", zorder=2)
errs = []
for name, steps, col, tname in rows:
    y = predicted(steps); ax.plot(G, y, color=col, lw=2.1, label=f"{name} (predicted)", zorder=3)
    tgt = norm(load_target(tname).interp(G).db); errs.append(f"{name} {werr(flat, tgt):.1f} → {werr(y, tgt):.1f} dB")
ax.set_ylim(-20, 15.5); ax.set_ylabel("Level, dB (relative)", fontsize=10); freq_axis(ax)
ax.legend(frameon=False, fontsize=10, loc="lower center", ncol=4, bbox_to_anchor=(0.5, -0.02))
ax.set_title("Response at the driver's seat", loc="left", fontsize=12.5, pad=12)
footer(fig, "Error vs each profile's own target, flat → set (predicted):  " + "   ·   ".join(errs) + "\n" + RESONIX_NOTE)
fig.savefig(OUT / "mazda3_eq_resonix_vs_by_ear.png", dpi=150)
plt.close(fig)
print("wrote ResoNix figures:", model_steps)
