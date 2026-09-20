# Final EQ profiles — 2021 Mazda 3, non-Bose

Regenerated 2026-09-18 by `make_profiles.py`, after listening, with targets
chosen from the research in `docs/targets.md` ("Research round 2"). Fitted
to the calibrated session 6 baseline. Set with **ALC off**; Bass and Treble
are unavailable (Customize EQ replaces them). Measured at Mazda volume 30.

| band | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| label | 40 | 63 | 100 | 160 | 250 | 500 | 1k | 1.6k | 2.5k | 4k | 6.3k | 10k | 16k |
| **A By ear** | +6 | -9 | -9 | +3 | -1 | +6 | -2 | -6 | 0 | +5 | -2 | 0 | +1 |
| **B Harman in-car** | +6 | -8 | -9 | 0 | -5 | +4 | -5 | -8 | -3 | +3 | -4 | 0 | +1 |
| **C Trained listener** | +6 | -9 | -9 | +2 | -1 | +6 | -2 | -8 | -3 | +3 | -5 | 0 | +1 |

| profile | target | error, flat -> fitted (predicted) |
|---|---|---|
| By ear | `mazda_by_ear`: the owner's by-ear preference measured through the calibrated mic; +4 dB shelf, flat mids, -3.25 dB/oct above ~4.2 kHz | 4.08 -> 1.88 dB |
| Harman in-car | `olive_welti_car`: Olive & Welti's in-car target (Toole 2015, Fig. 15); ~+8 dB bass, -5 dB at 20 kHz | 3.96 -> 2.02 dB |
| Trained listener | `olive2013_room_trained`: trained listeners' preferred room curve (Olive et al. 2013; home room) | 4.06 -> 1.90 dB |

All three are predictions. The method was checked on the previous Neutral
profile: 1.81 dB measured against 1.93 predicted.

## What changed and why

The previous set (Neutral / Warm / Bass-forward, commit 32fd53c) was fitted
correctly but to the wrong targets. On a test drive Neutral was too bright
and Warm sounded odd. The owner's by-ear fix, bands 12-13 from +3/+4 to
0/+1, is exactly what every published target with a falling treble asks
for; only our own `mazda_neutral`, whose treble falls just 2 dB by 20 kHz,
asked for +3/+5. Warm's fit made a presence dip (-2 dB at 2.5 kHz).

`By ear`'s fitted settings are within a step or two of the settings the owner
chose by ear (`+6 -8 -7 +1 -2 +4 -2 -7 0 +4 -2 0 +1`); they are the same
preference, the fit just places each band to match the smoothed target.

## How they were made

- **Baseline:** three moving-microphone pink-noise takes, occupied driver's
  seat, Dayton iMM-6 with its calibration file
  (`results/session6/baseline_move_pooled.csv`).
- **Model:** `results/session3/eq_model.json`, gain scale 0.95, cut factor
  0.93, equal weight per octave from 60 Hz to 12 kHz.
- **Boosts capped at +6**, the band 1 level the owner chose by ear. +4 costs
  about 0.1 dB more error; +9 gains 0.05-0.1 dB by driving band 1 to +9 at
  40 Hz, where the doors distort most (`docs/distortion.md`).
- **No overrides.** Every value is what the fit returns.

## Caveats

- Harman in-car's fit cuts bands 5, 7 and 9 harder (lower mids and 2.5 kHz),
  the same structure that made Warm sound odd. It is the research car target,
  so it stays, but listen for it.
- Bands 2 and 3 are at the rail: the +11 dB cabin hump at 80 Hz exceeds every
  target. Below 45 Hz nothing here helps; that is the subwoofer item.
- The model's bass cuts land ~1.5 dB deeper than predicted, and 1.2-3 kHz
  moves 2-3 dB with position and the body in the seat.
- Digitised research targets are read by eye from published plots, ~+-1 dB.

## Files

| file | contents |
|---|---|
| `profiles.png` | summary sheet: targets, predicted response, residuals, settings |
| `profile_by_ear.png`, `profile_harman_in_car.png`, `profile_trained_listener.png` | one fit sheet per profile |
| `settings.json`, `settings.csv` | the same numbers, machine readable |
| `make_profiles.py` | regenerates all of the above |
| `share/`, `make_share_figures.py` | owner-facing figures, including ResoNix fits (`resonix_settings.json`) |

Earlier profile sets are in git history (6de12e6: SoloCast by-ear set;
32fd53c: calibrated Neutral / Warm / Bass-forward).
