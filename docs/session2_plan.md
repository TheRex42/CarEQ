# Identification session 2 - recording plan

Fixes the three problems found in session 1 (2026-09-13) and adds the two
checks that session could not make. See `docs/procedure.md` for the setup;
only the differences are listed here.

## Changes to the setup

1. **Clip the mic over the PASSENGER seat headrest**, not the driver's. Sit
   in the driver's seat to change the sliders and stay in the car for the
   whole session. In session 1 the mic was clipped to the seat being sat in,
   and it shifted: a narrow notch near 7 kHz moved by up to 3 dB between
   files, and one file (band 1) picked up a 4 dB notch at 2 kHz. Occupancy
   does not matter for identification because every band is a ratio to
   baseline. The mic not moving is the only thing that matters.
2. **Check the mic for a low-cut / high-pass switch and turn it OFF.** See
   "Microphone" below; session 1 shows about 9 dB/octave of rolloff below
   80 Hz somewhere in the capture chain.
3. **Same volume number and same input gain as session 1.** Do not change
   either. Levels peaked at -12 dBFS with 45-65 dB SNR, which is ideal.
4. **Let the recorder run about 3 s after the sound stops.** Several session 1
   files ended within 0.1 s of the last sweep and one truncated it.
5. Ambient road noise does not need a quieter spot. See "Noise" below.

## Files, in order

Baselines are interleaved so the session-long level droop (-2.5 dB/hour,
very linear in session 1) can be regressed out per file.

| # | file | head unit setting |
|---|---|---|
| 1 | `baseline_1.wav` | all bands 0 |
| 2 | `baseline_2.wav` | all bands 0 (back to back with #1) |
| 3 | `band02_p9.wav` | band 2 = +9 |
| 4 | `band04_p9.wav` | band 4 = +9 |
| 5 | `band06_p9.wav` | band 6 = +9 |
| 6 | `baseline_3.wav` | all bands 0 |
| 7 | `band08_p9.wav` | band 8 = +9 |
| 8 | `band10_p9.wav` | band 10 = +9 |
| 9 | `band12_p9.wav` | band 12 = +9 |
| 10 | `baseline_4.wav` | all bands 0 |
| 11 | `band13_p9.wav` | band 13 = +9 |
| 12 | `band09_p9.wav` | band 9 = +9 (repeat; session 1 was unstable here) |
| 13 | `band01_p9.wav` | band 1 = +9 (redo; session 1 file was disturbed) |
| 14 | `baseline_5.wav` | all bands 0 |
| 15 | `band04_m9.wav` | band 4 = -9 (cut/boost asymmetry) |
| 16 | `band10_m9.wav` | band 10 = -9 (cut/boost asymmetry) |
| 17 | `combo_A.wav` | band 9 = +9 **and** band 10 = +9 together |
| 18 | `baseline_6.wav` | all bands 0 |
| 19 | `combo_B.wav` | band 2 = +6, band 6 = +4, band 10 = +7, band 13 = +5 |
| 20 | `baseline_7.wav` | all bands 0 (final) |

About 45 minutes at session 1's pace. If it has to be cut short, drop in this
order: #13 (band 1 redo), #16 (second cut), #2, #19 (combo B).

Optional, gives the phone a calibration for Phase 2: record one extra
baseline with the phone's own mic held where the USB mic sits, as
`baseline_phone.wav`. Dividing it by a USB-mic baseline gives the phone's
response relative to the USB mic, which is what the Android app will need.

Optional, settles why the level droops: after #20, run the engine for two
minutes, switch it off, and record one more baseline as `baseline_8.wav`. If
the level jumps back up, the droop is battery voltage sag.

## Why the last four files

Bands 4, 9, 10, 13 are all measured at +9 in this same session, so the checks
below compare like with like and do not depend on session 1.

- **#15, #16 (cuts).** Band 9 in session 1 cut 9.1 dB at -9 but boosted only
  7.4 dB at +9, and the cut was narrower. `careq fit` currently assumes a cut
  is a boost with the sign flipped, so it under-predicts cuts by about 20 %.
  Two more cut measurements say whether one asymmetry factor covers all bands
  or each band needs its own cut basis.
- **#17, #18 (superposition).** The fit assumes band gains add. That has never
  been checked on real hardware; the synthetic car satisfies it by
  construction. Bands 9 and 10 are adjacent, so their skirts overlap and any
  interaction shows up. The test is whether the measured combo curve equals
  the sum of the two individual curves.
- **#19 (combo B).** Four bands at four different non-maximum settings, spread
  across the spectrum. Tests superposition and per-step linearity together
  under conditions resembling a real tuning result.

## Microphone

Session 1 was recorded with a desktop USB condenser clipped over the headrest,
not a phone. That is a better mic and it changes nothing about identification,
because every band is a ratio of two measurements through the same mic, so the
mic response cancels exactly. It does change tuning: `careq fit` compares the
baseline against a target curve, and there the mic's own response is folded in
and is **not** removed. Whatever the mic does to the bass, the fit will try to
undo in the car.

Two things are needed before the fit output can be trusted.

1. **The mic's make and model**, so its published response can be saved as a
   two-column `frequency,dB` file and passed as `careq fit --mic-cal FILE`.
   The flag already exists and also accepts REW and UMIK-1 calibration files.
2. **Any low-cut switch on the mic or in the recording software turned off.**

Evidence that something is rolling off the low end: road noise in a car rises
steeply toward low frequency, normally 6-12 dB/octave below 100 Hz. In the
session 1 silences it is dead flat from 20 Hz to 80 Hz. That implies roughly
9 dB/octave of rolloff in the capture chain, or about 17 dB at 20 Hz. The
measured baseline falls 50 dB from 70 Hz to 20 Hz; perhaps a third of that is
the mic and the rest is real speaker rolloff. Until this is pinned down, treat
anything below 40 Hz in a fit result as unreliable.

The recordings also carry no encoder metadata, unlike the one RecForge II file
in the folder, so note which software captured them and confirm its input gain
and any processing are fixed and off.

## Noise

Measured from the silence before each sweep in session 1, the cabin noise
floor is road noise below 100 Hz falling steeply above it. Ambient level
varied by 13 dB between files as traffic came and went, with no visible effect
on any result, because a 10 s sweep buys roughly 40 dB of processing gain.

| frequency | SNR achieved |
|---|---|
| 20-25 Hz | 6-19 dB, unusable |
| 31.5 Hz | 28-36 dB |
| 40 Hz | 37-53 dB |
| 50 Hz and above | 43-77 dB |

The lowest EQ band sits at 41 Hz and `careq fit` already tapers its weighting
to 0.05 below 30 Hz, so nothing that can be controlled falls in the noisy
region. A quieter spot is not worth the trouble. If the 20-31.5 Hz octave ever
needs to be trusted, raising `careq gen --repeats` from 3 to 6 buys 3 dB more
cheaply than moving the car.
