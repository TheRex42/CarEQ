# Session 5 - calibrated microphone, and pink noise alongside sweeps

For when the Dayton iMM-6C arrives. It is omnidirectional with an individual
calibration file downloadable by serial number, which fixes both problems
with the SoloCast at once: the unknown response curve and, more importantly,
the cardioid pattern that weights arrival directions differently from an ear.

Setup as before: ALC off, session 3 volume reference, engine off, recorder
running 3 s past the end. Download the calibration file first and keep it
with the recordings.

## Part 1: sweep baseline (about 6 minutes)

Nine positions around the driver's headrest, as in session 4, so the result
is directly comparable with `results/session4/baseline_pooled_18.csv`.

## Part 2: pink noise, moving microphone (about 3 minutes)

Play `stimulus/careq_pink_48k_60s.wav`. Start the recorder, wait a second,
then move the microphone **slowly and continuously** through the same volume
the nine sweep positions covered, roughly 20 cm in each direction, for the
full minute. Keep it pointing the same way throughout. Two takes.

## Then

```
careq rta pink1.wav pink2.wav --out rta.csv \
     --mic-cal imm6_cal.txt --compare sweep_baseline.csv --plot rta_vs_sweep.png

careq fit --measurement sweep_baseline.csv --mic-cal imm6_cal.txt \
     --model results/session3/eq_model.json --target mazda_neutral --max-boost 4
```

## Optional, and genuinely optional: measure the SoloCast

An earlier draft of this plan opened with a transfer calibration, swapping
the two microphones into the same clamp to derive the SoloCast's response,
and claimed it would make the existing recordings reinterpretable. That was
overstated and it is not needed.

The band model is a ratio of two recordings through one microphone, so the
microphone cancels and the model is already correct; it does not need
redoing and the SoloCast's curve would not change it. The only recordings
that *do* depend on the microphone are the tuning baselines, and those are
being replaced by this session, so there is nothing to reinterpret.

What one extra 40-second sweep with the SoloCast in the same clamp would
buy is narrower than that:

- **A control.** If the new baseline looks unlike session 4's, a
  back-to-back pair separates "different microphone" from "different day,
  position or volume". Without it those are confounded.
- **A prediction tested.** The by-ear treble result implies the SoloCast
  reads about 1.5 dB low above 6 kHz (`docs/targets.md`). This measures it.

Neither changes a setting. Do it if the clamp is already up and there is
time; skip it otherwise.

## What to look for

1. **Do pink noise and sweeps agree?** They should, within about 1 dB, the
   repeatability of the multi-position average. The synthetic car puts them
   at 0.04 dB (`docs/rta.md`). Disagreement is diagnostic, not noise.
2. **How far off was the SoloCast?** The by-ear treble result predicts it
   reads roughly 1.5 dB low above 6 kHz (`docs/targets.md`). This is the
   direct test of that inference.
3. **Do the fitted treble bands land near the by-ear -4 -4 -2?** If they do,
   two independent methods agree and the profile is settled. If they do not,
   the gap is the difference between preference and accuracy, which is worth
   knowing on its own.
4. **The band model does not need redoing.** It is a ratio through one
   microphone, so the microphone cancels and it is already right. Only the
   baseline changes. The cancellation covers any fixed linear element in the
   chain, microphone, cabin and position alike, and any constant gain. It
   does NOT cover level-dependent behaviour, which is why ALC broke it: a
   limiter is not a fixed filter. Hence the rule that the volume number and
   ALC state must be held, not that level cancels.
