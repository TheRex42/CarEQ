# Session 5 - calibrated microphone, and pink noise alongside sweeps

For when the Dayton iMM-6C arrives. It is omnidirectional with an individual
calibration file downloadable by serial number, which fixes both problems
with the SoloCast at once: the unknown response curve and, more importantly,
the cardioid pattern that weights arrival directions differently from an ear.

Setup as before: ALC off, session 3 volume reference, engine off, recorder
running 3 s past the end. Download the calibration file first and keep it
with the recordings.

## Part 1: transfer calibration (about 6 minutes)

Two sweeps, **swapping microphones sequentially into the same clamp in the
same position**. Never side by side: a few centimetres in a modal field
exceeds the curve being measured.

```
cal_imm6.wav        iMM-6C in the clamp
cal_solocast.wav    SoloCast in the identical spot
```

Dividing one by the other gives the SoloCast's own response for good, which
makes every recording already taken reinterpretable rather than obsolete.

## Part 2: sweep baseline (about 6 minutes)

Nine positions around the driver's headrest, as in session 4, so the result
is directly comparable with `results/session4/baseline_pooled_18.csv`.

## Part 3: pink noise, moving microphone (about 3 minutes)

Play `stimulus/careq_pink_48k_60s.wav`. Start the recorder, wait a second,
then move the microphone **slowly and continuously** through the same volume
the nine sweep positions covered, roughly 20 cm in each direction, for the
full minute. Keep it pointing the same way throughout. Two takes.

## Then

```
careq measure cal_imm6.wav --stimulus stimulus/stimulus.json --out imm6.csv
careq measure cal_solocast.wav --stimulus stimulus/stimulus.json --out solocast.csv
# solocast.csv minus imm6.csv (plus the iMM-6C's own cal file) = the SoloCast's response

careq rta pink1.wav pink2.wav --out rta.csv \
     --mic-cal imm6_cal.txt --compare sweep_baseline.csv --plot rta_vs_sweep.png

careq fit --measurement sweep_baseline.csv --mic-cal imm6_cal.txt \
     --model results/session3/eq_model.json --target mazda_neutral --max-boost 4
```

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
   microphone and is microphone-independent. Only the baseline changes.
