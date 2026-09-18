# Session 6 results: the calibrated baseline

Recorded 2026-09-18, processed the same day. iMM-6 (99-64551) with its
calibration file, Mazda volume 30, ALC off, all sliders at 0. Files in
`Recordings/Session 6/`; results in `results/session6/`.

The three moving-microphone pink takes are named `sweep1-3.wav` ("sweeping"
the microphone through the head space). They are pink noise, not sine
sweeps. `fix_sweep2.wav` is an unplanned second sweep at the fixed spot,
used as a repeatability check.

## 1. The gate: pink agrees with sweep in the car

Fixed spot, driver's seat empty, mic untouched between files.

| comparison, 40 Hz-16 kHz, level removed | rms | max |
|---|---|---|
| sweep vs repeat sweep | 0.29 dB | 1.41 dB at 914 Hz |
| pink vs sweep | 0.31 dB | 1.08 dB at 1 kHz |
| three sweeps inside one file | 0.21 dB | 0.83 dB at 5.3 kHz |

Pink matches the sweep as well as the sweep matches itself, so Part 2 is
valid. Below 30 Hz pink reads high only because its SNR there is 7 dB or
less (fit weight 5 %). Plot: `results/session6/gate_pink_vs_sweep.png`.

Source data: 3 sweeps found per file, drift +9.9 / +11.2 ppm (session 5:
+12), corr-quality 1363-1635, SNR ~50 dB at 100 / 1k / 10k, no clipping,
peaks -27 dBFS, pink level steady within 1 dB for the whole take.

**Mic calibration:** applied by `measure`, `rta` and `fit`. Response with
minus without equals the calibration curve to 0.0002 dB.

**Bug found and fixed in `rta`.** The pink stimulus stops at 20 kHz; the
recorder's noise does not. Dividing that noise by an empty stimulus bin gave
+40 dB, and the 1/3-octave windows centred above 17.8 kHz averaged it in as a
+60 dB shelf, which moved band 13 from +7 to +2 in a trial fit.
`measure_noise_signal` now drops bins the stimulus does not excite; test
`test_pink_noise_rta_ignores_bins_the_stimulus_does_not_excite`.

## 2. The three moving takes converge

| comparison | rms | max |
|---|---|---|
| take vs take | 0.55-0.79 dB | 2.2 dB at 1.8 kHz |
| take vs pool | 0.32-0.46 dB | 1.3 dB |
| pool minus one take vs full pool | 0.17-0.24 dB | 0.78 dB |

Dropping any take moves the baseline by a quarter of the method's ~1 dB
resolution; a fourth take would not change the fit. Takes 1 and 2 began
after the noise was already playing, so `rta`'s SNR line is meaningless for
them (it reads the first 0.5 s as the floor). Borrowing the floor from this
session's other files, all three have the same SNR: 18 dB at 40 Hz, 24 at
50, 30-35 above 100. The noise biases the response 0.06 dB at 40 Hz and
nothing above. Start the recorder 3 s early next time.

Baseline: `results/session6/baseline_move_pooled.csv` (already calibrated).

The occupied-seat moving baseline differs from the empty-seat fixed spot by
2.6 dB rms, most at 1.26 kHz (-6.4 dB) and 100-125 Hz (+2.6 to +4.5 dB). That
is position and the body in the seat, not error, and is why the tuning
baseline is taken in the occupied seat.

## 3. Refit, matching the targets

On 2026-09-18 the owner dropped the by-ear overrides (band 1 at +6, Neutral
treble at -4 -4 -2, the inferred +1.5 dB mic correction): with a calibrated
instrument the goal is to match the targets. Model `results/session3/eq_model.json`,
gain scale 0.95, cut factor 0.93, default weights.

| profile | settings, bands 1-13 | error flat -> fitted |
|---|---|---|
| **Neutral** | +4 -9 -9 +1 -2 +4 -2 -7 0 +4 -2 +3 +4 | 4.30 -> 1.93 dB |
| **Warm** | +4 -9 -9 +2 -4 +4 -4 -8 -3 +3 -5 0 +1 | 3.67 -> 1.86 dB |
| **Bass-forward** | +4 -8 -9 +1 -5 +4 -5 -8 -2 +3 -3 +1 +4 | 3.99 -> 1.94 dB |

These use `--max-boost 4`. Uncapped fits (`*_mb9`) reach 1.77-1.80 dB, only
0.08-0.14 dB better, by putting band 1 at +8/+9 and band 6 at +5 to +9; band 1
at 40 Hz is where the doors already distort most and where volume 50
compresses. The cap costs nothing measurable. All six are in
`results/session6/settings.csv`, with plots and JSON alongside.

**The treble reverses.** Above 8 kHz the calibrated baseline is 5-8 dB lower
relative to 1 kHz than the session 4 SoloCast baseline, and agrees with the
session 5 iMM-6 files within ~2 dB. So every fit now boosts bands 12-13 where
the old ones cut. The by-ear -4 -4 -2 compensated in the wrong direction for
a microphone that read hot, i.e. it was preference or bias, not accuracy.

**Hazard:** `careq fit --mic-cal` applies the calibration to a CSV input too.
The `rta` CSV is already calibrated, so do NOT pass `--mic-cal` to `fit` with
it; that would subtract the curve twice. Pass it to `fit` only when fitting
a WAV directly.

## 4. Verification: Neutral set, measured

Two moving pink takes with Neutral `+4 -9 -9 +1 -2 +4 -2 -7 0 +4 -2 +3 +4`
set (`Recordings/Session 6/verify/`: `20260918_183743-0.wav`, `pink_2.wav`;
the third was not recorded). The first file opens with a click and has ~1 s
of non-pink sound after the noise ends; the second stops at 49 s. Trimmed to
the sustained noise by hand; default `rta` trimming gives the same response
within 0.06 dB rms. Takes agree 0.54 dB rms (baseline takes: 0.55-0.79).
Pooled, calibrated: `results/session6/verify_pooled.csv`.

| weighted error vs `mazda_neutral` | dB |
|---|---|
| EQ flat | 4.30 |
| predicted | 1.93 |
| **measured** | **1.81** |

The EQ change matched the model to 1.13 dB weighted rms (session 4: 1.05).
Two patterns: the bass cuts at 50-100 Hz land 1.1-1.7 dB deeper than
predicted, the same bias session 4 saw at 63/100 Hz, and it happens to help
here; 1.25 kHz and 2.5-3.15 kHz land 2-3 dB higher than predicted, the
region that moves most with position and body (up to 6 dB between the fixed
spot and the occupied seat) and the known driver-crossover region.

Pass 2 (`fit --current`, `results/session6/fit_neutral_pass2.json`) proposes
`+4 -9 -9 +1 -4 +4 -3 -8 -3 +3 -2 +2 +3` for a predicted 1.81 -> 1.65 dB,
0.16 dB, driven mostly by band 9 (-3) chasing the 2.5-3 kHz region. That is
below the ~0.5 dB threshold set above and inside the method's ~1 dB
resolution, from two takes. **Pass 1 is the result.**

## Next

Neutral is tuned. Warm and Bass-forward are fitted but not verified. `results/final/`
still holds the pre-calibration profiles. Remaining roadmap items: REW
cross-check (`fix_sweep.wav`), subwoofer, door sealing.
