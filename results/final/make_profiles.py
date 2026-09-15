"""Final three profiles, with the by-ear treble calibration folded in.

The owner tuned bands 11-13 by ear to -4 -4 -2 where the uncorrected fit gave
-2 -2 -1, which places the SoloCast about 1.5 dB low above 6 kHz (see
docs/targets.md). That is applied as a microphone correction to the baseline
and all three targets are refitted, so each gets the treble it deserves rather
than having one target's by-ear answer pasted onto the others.

Band 1 is then set to +6 by hand: the fit caps boosts at +4 for headroom, and
+6 was chosen by listening, clean on everything except the deepest sub-bass
(docs/distortion.md).

    .venv/bin/python results/final/make_profiles.py
"""
import numpy as np, sys, json
sys.path.insert(0, '.')
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import ticker
sys.path.insert(0, '.')
from careq.measure import Response, LOG_GRID as G
from careq.identify import EqModel
from careq.fit import fit_eq, load_target, default_weights, weighted_rms, effective_steps, plot_fit

MIC_CORRECTION_DB = 1.5      # SoloCast reads this much low above 6 kHz, from the by-ear result
BAND1 = 6                    # chosen by listening, not by the fit
# Bands 11-13 of the neutral profile were settled by ear on female vocals,
# listening for sibilance and cymbals. That is a direct result and stands as
# measured; the correction above is only the inference drawn FROM it, used to
# carry the finding across to the two profiles that have not been listened to.
BY_EAR = {'mazda_neutral': {10: -4, 11: -4, 12: -2}}
LABELS = [40, 63, 100, 160, 250, 500, 1000, 1600, 2500, 4000, 6300, 10000, 16000]
TARGETS = {'mazda_neutral': ('A  Neutral', 'flat mids, +3 dB bass shelf, gentle treble tilt', '#2a78d6'),
           'mazda_warm':    ('B  Warm', '+5 dB bass to 100 Hz, treble down 5 dB by 20 kHz', '#eb6834'),
           'mazda_bass':    ('C  Bass-forward', '+7 dB below 60 Hz, flat mids and treble', '#1baf7a')}

model = EqModel.load('results/session3/eq_model.json'); A = model.per_step_matrix()
raw = Response.from_csv('results/session4/baseline_pooled_18.csv')
L = np.log2(G)
corr = MIC_CORRECTION_DB * np.clip((L - np.log2(3000)) / (np.log2(7000) - np.log2(3000)), 0, 1)
base = Response(G, raw.db + corr, "baseline (mic-corrected)")
w = default_weights(G)


def finish(steps, target):
    s = np.array(steps, dtype=int).copy(); s[0] = BAND1
    for i, v in BY_EAR.get(target, {}).items():
        s[i] = v
    return s


def predicted(steps):
    p = base.normalized().db + A @ effective_steps(steps, 0.95, 0.93)
    return p - np.mean(p[(G >= 200) & (G <= 2000)])


def werr(db, tgt, weights=w):
    r = db - tgt.normalized().db
    return weighted_rms(r - np.sum(weights * r) / np.sum(weights), weights)


R = {}
for t, (name, blurb, col) in TARGETS.items():
    tgt = load_target(t)
    fit = fit_eq(base, model, tgt, max_boost=4)
    steps = finish(fit.steps_int, t)
    R[t] = dict(name=name, blurb=blurb, col=col, steps=steps, tgt=tgt,
                pred=predicted(steps), err=werr(predicted(steps), tgt),
                err0=werr(base.normalized().db, tgt))
    plot_fit(fit, f'results/final/profile_{t.split("_")[1]}.png', f'{name}: {blurb}')

print(f"microphone correction applied: +{MIC_CORRECTION_DB} dB above 6 kHz")
print(f"band 1 set to +{BAND1} by listening\n")
print(f"{'profile':18} {'settings, bands 1-13':46} {'error':>7}")
for t, r in R.items():
    print(f"{r['name']:18} {' '.join(f'{v:+d}' for v in r['steps']):46} {r['err']:6.2f} dB")
json.dump({R[t]['name']: [int(v) for v in R[t]['steps']] for t in R},
          open('results/final/settings.json', 'w'), indent=1)
with open('results/final/settings.csv', 'w') as fh:
    fh.write("profile," + ",".join(f"band{i+1}_{l}Hz" for i, l in enumerate(LABELS)) + "\n")
    for t, r in R.items():
        fh.write(r['name'].split('  ')[1] + "," + ",".join(str(int(v)) for v in r['steps']) + "\n")


def axes(ax, title, yl="dB"):
    ax.set_xlim(20, 20000); ax.set_xticks([20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v, _: f"{v/1000:g}k" if v >= 1000 else f"{v:g}"))
    ax.grid(True, which="both", color="#e6e5e1", linewidth=0.6)
    ax.set_title(title, loc="left", fontsize=11); ax.set_ylabel(yl)
    for s in ("top", "right"): ax.spines[s].set_visible(False)


fig = plt.figure(figsize=(15, 11)); fig.patch.set_facecolor("#fcfcfb")
gs = fig.add_gridspec(3, 2, height_ratios=[1, 1, 1.15], hspace=0.38, wspace=0.22)
ax = fig.add_subplot(gs[0, 0])
for t, r in R.items(): ax.semilogx(G, r['tgt'].normalized().db, color=r['col'], lw=2, label=r['name'])
ax.axhline(0, color='k', lw=0.5); ax.set_ylim(-7, 9); ax.legend(frameon=False, fontsize=9)
axes(ax, "The three targets")
ax = fig.add_subplot(gs[0, 1])
ax.semilogx(G, base.normalized().db, color='#8a8985', lw=1.4, label="measured, EQ flat")
for t, r in R.items(): ax.semilogx(G, r['pred'], color=r['col'], lw=1.8, label=r['name'])
ax.set_ylim(-30, 18); ax.legend(frameon=False, fontsize=9)
axes(ax, "Predicted response at the driver's seat")
ax = fig.add_subplot(gs[1, :])
for t, r in R.items():
    res = r['pred'] - r['tgt'].normalized().db; res -= np.sum(w * res) / np.sum(w)
    ax.semilogx(G, res, color=r['col'], lw=1.7, label=f"{r['name']}  ({r['err0']:.2f} -> {r['err']:.2f} dB)")
ax.fill_between([20, 20000], -2, 2, color='#e6e5e1', alpha=0.7)
ax.axhline(0, color='k', lw=0.5); ax.set_ylim(-9, 7); ax.legend(frameon=False, fontsize=9)
axes(ax, "Residual vs target (grey band = within 2 dB)")
ax = fig.add_subplot(gs[2, :])
x = np.arange(13); wd = 0.26
for i, (t, r) in enumerate(R.items()):
    b = ax.bar(x + (i - 1) * wd, r['steps'], wd, color=r['col'], label=r['name'])
    for xi, v in zip(x + (i - 1) * wd, r['steps']):
        ax.text(xi, v + (0.45 if v >= 0 else -0.45), f"{v:+d}", ha='center',
                va='bottom' if v >= 0 else 'top', fontsize=7.5, color='#0b0b0b')
ax.set_xticks(x); ax.set_xticklabels([f"{i+1}\n{l:g} Hz" for i, l in enumerate(LABELS)], fontsize=8.5)
ax.set_ylim(-12.5, 8.5); ax.axhline(0, color='k', lw=0.6)
ax.grid(True, axis='y', color='#e6e5e1', lw=0.6); ax.legend(frameon=False, fontsize=9, ncol=3, loc='lower center')
ax.set_title("Head-unit settings.  Band 1 = +6 and Neutral's bands 11-13 settled by ear; "
             "Warm and Bass use the +1.5 dB mic correction inferred from that.",
             loc='left', fontsize=11)
ax.set_ylabel("steps"); ax.set_xlabel("band / label")
for s in ("top", "right"): ax.spines[s].set_visible(False)
fig.suptitle("2021 Mazda 3 — final EQ profiles", x=0.008, ha='left', fontsize=14, weight='bold')
fig.savefig('results/final/profiles.png', dpi=130, bbox_inches='tight')
print("\nwrote results/final/profiles.png, profile_{neutral,warm,bass}.png, settings.json, settings.csv")
