# Final EQ profiles — 2021 Mazda 3, non-Bose

Generated 2026-09-18 by `make_profiles.py` from the calibrated session 6
baseline (`docs/session6_results.md`). Set with **ALC off**; Bass and Treble
are unavailable (Customize EQ replaces them). Measured at Mazda volume 30.

| band | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| label | 40 | 63 | 100 | 160 | 250 | 500 | 1k | 1.6k | 2.5k | 4k | 6.3k | 10k | 16k |
| **A Neutral** | +4 | -9 | -9 | +1 | -2 | +4 | -2 | -7 | 0 | +4 | -2 | +3 | +4 |
| **B Warm** | +4 | -9 | -9 | +2 | -4 | +4 | -4 | -8 | -3 | +3 | -5 | 0 | +1 |
| **C Bass-forward** | +4 | -8 | -9 | +1 | -5 | +4 | -5 | -8 | -2 | +3 | -3 | +1 | +4 |

| weighted error vs own target | EQ flat | predicted | measured |
|---|---|---|---|
| Neutral | 4.30 dB | 1.93 dB | **1.81 dB** |
| Warm | 3.67 dB | 1.86 dB | not yet |
| Bass-forward | 3.99 dB | 1.94 dB | not yet |

Neutral was verified in the car the same evening with two moving-microphone
takes. A second fit pass from the measured result would gain 0.16 dB, inside
the method's ~1 dB resolution, so these are final.

## How they were made

- **Baseline:** three moving-microphone pink-noise takes from the occupied
  driver's seat, Dayton iMM-6 with its calibration file, pooled
  (`results/session6/baseline_move_pooled.csv`). Dropping any one take
  moves it by at most 0.24 dB rms.
- **Model:** `results/session3/eq_model.json`, gain scale 0.95, cut factor
  0.93, equal weight per octave from 60 Hz to 12 kHz.
- **Boosts capped at +4.** Uncapped fits are 0.08-0.14 dB better and put
  band 1 at +8/+9, where the doors already distort most (`docs/distortion.md`).
- **No by-ear overrides.** Earlier profiles set band 1 to +6 and Neutral's
  treble to -4 -4 -2 by ear. The calibrated microphone showed the old
  SoloCast read 4-6 dB hot above 6 kHz, in two independent comparisons, so
  those treble cuts compensated in the wrong direction. Every value here
  is what the fit returns.

## Caveats

- Bands 2 and 3 are at the rail. The +11 dB cabin hump at 80 Hz exceeds
  every target; there is no Bass tone control to help.
- Below 45 Hz nothing here can help: the doors fall away and the error
  there is physics. That is the subwoofer item on the roadmap.
- The model's bass cuts land ~1.5 dB deeper than predicted (sessions 4 and
  6 both), and 1.2-3 kHz moves 2-3 dB with position and the body in the seat.
- The three share band 1 and bands 2, 3, 6 and 8 within a step. They
  differ in the lower mids (bands 5 and 7, which set how full the bass
  sounds against the voice), band 9, and the treble tilt. Pick by taste.

## Files

| file | contents |
|---|---|
| `profiles.png` | summary sheet: targets, predicted response, residuals, settings |
| `profile_neutral.png`, `profile_warm.png`, `profile_bass.png` | one fit sheet per profile |
| `settings.json`, `settings.csv` | the same numbers, machine readable |
| `make_profiles.py` | regenerates all of the above |

The previous, pre-calibration profiles are in git history (commit 6de12e6).
