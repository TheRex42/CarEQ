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

# A problem found in these files: distortion is 2-3x higher

Checked because 75 dB on the pink file is a new reference and might be
louder than the volume 25 used for sessions 2-4. Harmonic distortion,
corrected for the cabin response at the harmonic frequencies:

| fundamental | sessions 2 and 4, SoloCast | session 5, iMM-6 |
|---|---|---|
| 40 Hz | 2.2 - 2.7 % | 7.5 % |
| 63 Hz | 1.1 - 1.3 % | 2.5 % |
| 100 Hz | 0.9 - 1.0 % | 3.0 % |
| 250 Hz | 0.3 - 0.4 % | 2.8 % |
| 400 Hz | 0.2 - 0.3 % | 1.1 % |

## It does not look like the speakers

Two things point away from the car.

**The second harmonic is flat with frequency.** In session 5 it sits at
-30 to -34 dB from 40 Hz to 250 Hz, barely varying. Woofer distortion is
excursion-limited, so it climbs steeply toward low frequency; the SoloCast
sessions show exactly that, with H2 wandering between -40 and -53 dB and no
plateau. A roughly constant second harmonic across three octaves is the
signature of a fixed nonlinearity somewhere in the signal path.

**The harmonic balance flipped.** Session 4 is third-harmonic dominant
below 63 Hz, by 12 to 13 dB, which is what a driver at its excursion limit
does. Session 5 is second-harmonic dominant nearly everywhere, by 8 to
20 dB. That is a different mechanism, not more of the same one.

## Most likely: input gain too high on the dongle

The session 5 files peak at -7.6 to -9.1 dBFS against -12 for every
SoloCast session. Nothing clips digitally, but preamp distortion happens
*before* the converter, so digital headroom says nothing about it. The
SoloCast contained its own preamp and converter; the Apple dongle's is a
cheap headset input being asked for a lot of gain.

Supporting this, within session 5 the two identical baselines differ by
1.5 dB in recorded level and by 30 to 40 % in distortion, which is steeper
than a simple nonlinearity and closer to something approaching its limit.

## What it did and did not affect

**Part 1b is unharmed.** A basis is a ratio of two recordings through the
same chain, so a fixed nonlinearity largely divides out, and the four bands
agreed with the SoloCast model to 0.41-0.69 dB rms. That result stands.

**A tuning baseline would be harmed.** The baseline is not a ratio. Second
harmonic at -32 dB adds energy at twice every frequency, which would tilt
the measured response and be fitted as if it were the car.

## The fix, and the test

Drop the recording app's input gain so peaks land around **-18 to -24 dBFS**
while leaving the car at 75 dB. There is 55 to 72 dB of signal-to-noise in
these recordings, so giving away 12 to 15 dB costs nothing that matters.

Then the decisive two-file test, same position, same car volume:

```
gain_high.wav    one sweep at the current recorder gain
gain_low.wav     one sweep about 12 dB lower on the recorder
```

Acoustic level identical, electrical level different. If the distortion
falls, it is the chain and the fix is confirmed. If it does not, it is the
car at 75 dB and the reference volume should come down instead.

If the app has no input gain control, lower the car volume instead and
accept a quieter reference; the comparison is then confounded but a large
drop still points at the chain.
