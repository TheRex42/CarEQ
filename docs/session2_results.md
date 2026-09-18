# Session 2 results (2026-09-13, 14:00-14:45)

21 files in `Recordings/Session2/`, USB condenser clipped over the passenger
headrest, 44.1 kHz mono 16-bit, peaks -12 dBFS, no clipping, drift +9.9 to
+11.2 ppm in every file, SNR 45-69 dB. Outputs in `results/session2/`
(`eq_model.json` is the combined 13-band model; odd bands 3, 5, 7, 11 come
from session 1 and carry its single-baseline noise above 5 kHz).

## All 13 bands, measured at +9

| band | centre | Q | peak dB | dB/step | source |
|---|---|---|---|---|---|
| 1 | 41 Hz | 1.7 | 7.6 | 0.84 | s2 |
| 2 | 60 Hz | 2.0 | 8.3 | 0.92 | s2 |
| 3 | 102 Hz | 2.2 | 8.2 | 0.91 | s1 |
| 4 | 169 Hz | 2.5 | 8.6 | 0.95 | s2 |
| 5 | 253 Hz | 2.1 | 7.6 | 0.84 | s1 |
| 6 | 506 Hz | 2.0 | 8.0 | 0.88 | s2 |
| 7 | 968 Hz | 1.8 | 6.7 | 0.75 | s1 |
| 8 | 1.60 kHz | 1.8 | 7.7 | 0.85 | s2 |
| 9 | 2.51 kHz | 2.6 | 8.3 | 0.92 | s2 |
| 10 | 4.04 kHz | 2.1 | 9.1 | 1.01 | s2 |
| 11 | 5.62 kHz | 2.8 | 7.6 | 0.84 | s1 |
| 12 | 10.2 kHz | 1.5 | 8.7 | 0.96 | s2 |
| 13 | 15.7 kHz | 0.8 | 8.3 | 0.92 | s2 |

Band labels are therefore 40, 63, 100, 160, 250, 500, 1k, 1.6k, 2.5k, 4k,
6.3k, 10k, 16k, not the 1/3-octave ladder that was guessed. Band 13 is a
broad top-octave filter (Q 0.75) rather than a peak. Q is about 2 and dB per
step 0.85-1.0 everywhere; band 7's 0.75 is a session 1 number and probably
low.

Peaking-filter fit errors dropped from 0.6-1.2 dB (session 1) to 0.35-0.55 dB
(session 2). The far-field junk in each basis (more than 2.5 octaves from
its peak) is 0.15-0.7 dB rms, against 0.6-1.4 in session 1.

## Repeatability

- **Band 1** agrees with session 1 within 0.5 dB rms near the peak. Session
  1's band 1 was fine at 40 Hz; only its midrange was disturbed.
- **Band 9** does not: session 2 gives +8.3 dB, Q 2.6, against session 1's
  +7.1 dB, Q 1.8, and the session 1 file was the one whose sweeps disagreed
  with each other. Session 2's three sweeps agree within 0.03 dB. Trust
  session 2.

## Baseline drift

Six baselines over 37 minutes, plus one at the end at a different level.
Sweep-to-sweep repeatability inside every file is 0.03-0.09 dB. Between
files the 200 Hz-1 kHz region loses 1.2 dB over 37 minutes, roughly
linearly (-2 dB/hour; session 1 showed -2.5 dB/hour), while 5-16 kHz stays
within 0.2 dB. It is a midrange loss, not a gain change. Cause still
unknown; voice-coil heating from repeated sweeps would look like this.
Bases above were computed against a baseline interpolated in time between
the neighbouring baselines, which brings each band's broadband offset from
-0.6 dB down to 0.0 to +0.5 dB.

The final file `baseline_final_level_control.wav` sits 5.8 dB below
Baseline_6 with a flat shape (0.66 dB rms). If that was a volume step, it
says the volume control changes nothing but level over that range, which is
what tuning at one volume needs.

## Cut vs boost (bands 4 and 10 at -9, one file)

| band | boost +9 | cut -9 | cut / boost |
|---|---|---|---|
| 4 | +8.6 dB, Q 2.5 | -8.1 dB, Q 2.3 | 0.93 |
| 10 | +9.1 dB, Q 2.2 | -8.4 dB, Q 2.0 | 0.93 |

Cuts are the mirror of boosts to within 7 %, same centre, same width.
Session 1's band 9 asymmetry came from its unreliable +9 file. The fit now
applies a 0.93 factor to negative steps. Note that 1/3-octave power
smoothing itself shrinks a cut more than a boost (a synthetic unit with a
true factor of 0.98 measures as 0.93 through this pipeline), so the
underlying filters are probably almost exactly symmetric; 0.93 is still the
right number for the fit, which works on the smoothed curves.

## Superposition: the assumption that fails

> **OVERTURNED by session 3.** This conclusion was wrong. ALC was on and
> adding about 6 dB, so +9 boosts ran into the head unit's limiter. With ALC
> off, adjacent bands add to within about 5 %, and the fit's gain scale is
> 0.95, not 0.87. See `docs/session3_results.md`. The text below records
> what was believed at the time.

**Adjacent bands 9 and 10 both at +9.** Measured peak 9.8 dB where the sum
of the two single-band curves predicts 11.7 dB. Least squares recovers the
combination as 0.85 x basis 9 + 0.64 x basis 10, and a two-peak fit of the
measured curve finds band 9 widened to Q 1.1 (from 2.6) and band 10 cut to
5.3 dB (from 9.2). The measured response also spills 2.9 dB more than
predicted into the 1.5-2 kHz octave below the pair. Two adjacent maxed
bands do not add; the head unit delivers a wide 9-10 dB plateau spanning
both centres.

**Four non-adjacent bands at 6, 4, 7, 5.** Measured within 0.5-1.0 dB rms
of the prediction near each peak, but consistently short: least squares
recovers 5.5, 3.4, 5.9, 4.3, that is 84-92 % of what was set.

Both point the same way. Gains under-deliver in combination, mildly for
separated bands (about 12 %), strongly for adjacent ones at the same sign.
This is the signature of a graphic EQ whose filter gains are solved jointly
so the response at each centre lands near the slider value, rather than
independent filters that stack. It is a deliberate design and it is not
what `careq fit` assumes.

Consequences for tuning:

- `careq fit` will overpredict the effect of any settings where neighbours
  push the same way, by up to 2 dB in the worst case, and by about 10 %
  elsewhere. The direction is consistent, so the predicted residual is
  optimistic.
- The robust fix is iteration: fit, set the sliders, measure again, fit the
  new residual with the same bases, apply the increment. The second pass
  lands on the target regardless of the interaction. Building the interaction
  into the model would need every adjacent pair measured at several settings,
  which is 30+ files for a gain that the iteration gets for free.
- A cheaper single-pass improvement is to scale the per-step gains by 0.87
  in the fit so the typical multi-band case is right on average.

## The RecForge file

`20260913_140208.wav`, recorded between Baseline_1 and Baseline_2, is a
complete three-sweep baseline that matches Baseline_1 within 0.3 dB from
20 Hz to 16 kHz. Two different microphones do not agree like that, so it is
the same USB mic, not the phone's internal mic. If it was meant as the
phone-versus-USB comparison, that recording has not happened yet.
`20260913_140031.wav` is a single 10 s sweep, presumably a level test.

## Next

Done the same evening: band labels fixed in `identify.py`; `simulate.py`
carries the measured centres, Q, 0.93 cut factor and a soft gain limiter (a
milder interaction than the real one, enough for the tests to exercise the
second pass); `careq fit` has `--gain-scale` (0.87), `--cut-factor` (from the
model's symmetry run, else 0.93) and `--current` for the iterate pass.

Still to do: session 3 (`docs/session3_plan.md`), mic calibration, then the
occupied-seat multi-position tuning baseline at the same volume number.
