# Final EQ profiles — 2021 Mazda 3, non-Bose

Generated 2026-09-14 by `make_profiles.py`. Set with **ALC off**, Bass and
Treble unavailable (Customize EQ replaces them), at the session 3 volume
reference.

| band | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| label | 40 | 63 | 100 | 160 | 250 | 500 | 1k | 1.6k | 2.5k | 4k | 6.3k | 10k | 16k |
| **A Neutral** | +6 | -9 | -9 | +3 | 0 | +4 | +3 | -7 | +1 | +3 | -4 | -4 | -2 |
| **B Warm** | +6 | -9 | -9 | +4 | -3 | +2 | +2 | -9 | -2 | +2 | -6 | -6 | -7 |
| **C Bass-forward** | +6 | -9 | -9 | +2 | -4 | +1 | 0 | -9 | -2 | +2 | -6 | -4 | -5 |

Predicted weighted error against each profile's own target: 2.51, 2.49,
2.60 dB, from about 4.2-4.5 dB with the EQ flat.

## What is fitted and what is not

Two values in every profile were **not** chosen by the optimiser:

- **Band 1 at +6.** The fit caps boosts at +4 for headroom. +6 was chosen by
  listening and was clean on everything except the deepest sub-bass in one
  track. 40-50 Hz is the most distorted part of this system at about 2 %
  before any boost (`docs/distortion.md`), so do not go higher.
- **Neutral's bands 11-13 at -4 -4 -2.** Settled by ear on female vocals,
  listening for sibilance and for cymbals reading as struck metal rather
  than hiss. That is a direct result and stands as measured.

Warm and Bass-forward have not been listened to at the top. Their treble
comes from refitting with a +1.5 dB correction above 6 kHz, which is the
microphone error *inferred from* the neutral by-ear result
(`docs/targets.md`).

## Files

| file | contents |
|---|---|
| `profiles.png` | the summary sheet: targets, predicted response, residuals, settings |
| `profile_neutral.png`, `profile_warm.png`, `profile_bass.png` | one sheet per profile |
| `settings.json`, `settings.csv` | the same numbers, machine readable |
| `make_profiles.py` | regenerates all of the above |

## Caveats worth keeping in view

- The microphone is a cardioid HyperX SoloCast with no calibration. Above
  4 kHz the measurement is the weakest part of this, which is why the
  neutral profile's treble was set by ear instead.
- Bands 2 and 3 are at the rail in all three. The cabin's +14 dB hump at
  83 Hz exceeds every target and cannot be fully corrected; there is no
  Bass tone control to help.
- Below 50 Hz nothing here can help. The doors are 10 dB down by 48 Hz and
  that is physics, not tuning.
- The three differ mostly in bass amount and treble tilt. They agree within
  half a decibel from 250 Hz to 2 kHz, so pick by taste, not by the number.

## Next

A calibrated omnidirectional measurement microphone is the one outstanding
item that would change any of this. When it arrives only the tuning
baseline needs redoing, nine recordings and a refit; the 13-band model is a
ratio measurement and is microphone-independent. See `docs/microphone.md`.
