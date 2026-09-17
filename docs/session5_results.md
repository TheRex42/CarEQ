# Session 5, Part 1b — the four-band confirmation (2026-09-17)

Seven files in `Recordings/Session_5_cal_mic/`, recorded with the Dayton
iMM-6 through an Apple USB-C dongle into the phone. Calibration file
`Calibration/99-64551.txt`. Model written to
`results/session5/model_imm6_4band.json`, plots in `results/session5/`.

**Verdict: it passes.** The band model measured through a completely
different microphone, converter and polar pattern, four days later, agrees
with the model built from the SoloCast.

## The chain is better than the old one

| | SoloCast sessions | iMM-6 + dongle |
|---|---|---|
| correlation quality | 250 - 4400 | **4900 - 9900** |
| SNR at 100 Hz / 1 kHz / 10 kHz | 45 - 65 dB | **55 - 72 dB** |
| SNR at 20 Hz | 12 - 16 dB | **32 dB** |
| drift | +9.9 to +13.2 ppm | +11.8 to +12.2 ppm |
| clipping | none | none |
| peaks | -12 dBFS | -7 to -9 dBFS |

Nothing here suggests the dongle is degrading anything. The low-frequency
signal-to-noise is 16 to 20 dB better than any previous session, which is
the opposite of what a high-pass in the chain would do. The direct test,
the same-spot SoloCast sweep, is still outstanding.

## The calibration file

256 points, 20 Hz to 20 kHz, spanning -1.3 to +4.1 dB. Flat within about a
decibel to 6 kHz, then a +3.3 dB presence rise across 8 to 12.5 kHz,
falling back by 16 kHz. A textbook small-electret shape, and the sign
convention is right: careq subtracts it, so the corrected measurement comes
out lower where the capsule reads hot.

## Bands, two microphones

Peaking-filter descriptions fitted over 40 Hz to 16 kHz:

| band | centre SoloCast | iMM-6 | Q SoloCast | iMM-6 | basis rms difference |
|---|---|---|---|---|---|
| 1 | 36 Hz | 38 Hz | 1.97 | 1.87 | 0.69 dB |
| 5 | 251 Hz | 249 Hz | 2.15 | 2.19 | 0.43 dB |
| 9 | 2558 Hz | 2491 Hz | 2.27 | 2.24 | 0.41 dB |
| 13 | 15.3 kHz | 15.2 kHz | 1.09 | 1.08 | 0.52 dB |

Centres within 5 %, Q within 0.1, whole basis curves within 0.41 to 0.69 dB
rms over 40 Hz to 16 kHz. For scale, two nine-position baselines of the same
car on the same day differ by 1.0 dB rms, and one slider step is about
0.9 dB. The disagreement is smaller than the method's own repeatability.

Peak heights run 0.3 dB lower on the new microphone for the middle two bands
and about 1 dB lower for bands 1 and 13. The extremes disagreeing more is
expected: they sit where SNR is worst and at the edge of the analysis range.

**This is the first empirical confirmation that the microphone cancels out
of a basis.** The claim was always sound theory, and a great deal rests on
it: that the model survived the microphone change, that identification would
be the shareable half if this were ever generalised, and that
re-identification is not on the roadmap. It is now tested rather than
assumed, and `results/session3/eq_model.json` stands unchanged.

## A bug this found in our own code

The first run reported band 1 at 26 Hz with Q 0.65 and 0.61 dB per step,
against 37 Hz and Q 1.62 in the model, which looked like a real
disagreement. It was not. `fit_peaking` was being handed the whole
20 Hz-20 kHz grid, including 20 to 40 Hz where SNR is 32 to 47 dB and the
basis ratio is mostly noise. That dragged the fitted centre and Q a long
way for the outermost bands.

Restricted to the check range, band 1 becomes 38 Hz at Q 1.87, and band 13
moves from an unstable 16.9 kHz to 15.2 kHz. `identify` now fits over
`check_range` only. The description is diagnostic and never fed the fit, so
no previous result changes, but it is the table read at the start of every
session and it was misleading at both ends.

## Procedure notes

Recorded as baseline, band 1, band 5, band 9, baseline 2, band 13, which
leaves band 13 six minutes after the last baseline. `identify` subtracts
each run's far-field offset so this is handled, but a third baseline at the
end would have been better. Two baselines instead of three is the only
departure from the plan.

## Still outstanding

Everything except 1b. Part 1's diagnostics, the linearity pair, the static
pink take and the same-spot SoloCast sweep, and Part 2's moving-microphone
baseline. The baseline is what the fit actually needs; this run only
confirmed that the model feeding it is sound.

A direct SoloCast comparison is not possible from these files: session 2's
baselines were at a different position on a different day, so the two differ
by 2.8 to 6.3 dB rms depending on region, which is position and not
microphone. That is exactly why the plan puts both microphones in the same
spot in the same minute.
