# Session 5 — calibrated microphone, volume reference, pink noise

For when the Dayton iMM-6 arrives. About 20 minutes in the car, 14 files.
Everything learned so far is folded in, so this supersedes earlier drafts.

The microphone is omnidirectional with an individual calibration file, which
fixes both problems with the SoloCast at once: the unknown response and,
more importantly, the cardioid pattern that weights arrival directions
differently from an ear.

---

# Before going out (at the desk, 10 minutes)

**1. Download the calibration file** by serial number from Dayton's site.
Keep it with the recordings as `imm6_cal.txt`.

**2. Check careq can read it and that the sign is right.** This is the one
thing that silently doubles the error instead of removing it.

```
.venv/bin/python -c "
import sys; sys.path.insert(0,'.')
from careq.measure import Response
c = Response.from_csv('imm6_cal.txt')
print(len(c.freq), 'points,', c.freq.min(), '-', c.freq.max(), 'Hz')
for f in (30, 100, 1000, 5000, 10000, 16000):
    import numpy as np; print(f, round(float(np.interp(f, c.freq, c.db)), 2), 'dB')"
```

Expect a smooth curve within a few dB, typically rising a little in the top
octaves. The convention is that the file states the **microphone's own
response** and careq subtracts it, so a mic that reads hot at 10 kHz has a
positive value there and the corrected measurement comes out lower. If
applying it makes the car look *brighter*, the sign is inverted.

**3. Know which variant you have.** The iMM-6 is 3.5 mm TRRS and needs a
headset input; the iMM-6C is USB-C. A laptop headset jack is a different
recording chain from the SoloCast's USB path and may have its own high-pass
or automatic gain. Part 0 below tests for that.

---

# In the car

Head unit: **ALC off**, fader and balance centred, all 13 sliders at 0.
Bass and Treble are unavailable while Customize EQ is selected. Engine off,
accessory mode, HVAC off, doors shut. Recorder: mono WAV, fixed gain, no
processing, running 3 s past the end of every file.

Microphone clipped to the **driver's** headrest, driver's seat empty, you in
the passenger seat, aimed consistently and not rotated between files.

## Part 0 — set the volume reference (5 minutes, 1 file)

Play `stimulus/careq_pink_48k_60s.wav`. With an SPL meter or phone app at
the driver's head position, set the head unit so it reads **75 dB, C
weighted, slow**. Write down the Mazda volume number. Sessions 1-4 used 25;
if the new number is close to that, everything stays directly comparable.

Record one pink file at this setting while you are there:

```
pink_ref.wav
```

Check the recorder peaks near -12 dBFS during a sweep and never clip. The
sweep file runs 5.0 dB hotter than the pink file at the same volume, so
expect roughly 80 dB during sweeps (`docs/level.md`).

## Part 1 — level-linearity check (3 minutes, 2 files)

The gate. Everything after this assumes the system is linear at the chosen
volume, and two sessions were once misread because it was not.

Microphone clamped, not moved between these two.

```
lin_ref.wav      sweep at the reference volume   (this is also baseline position 1)
lin_loud.wav     sweep about 6 dB louder (roughly 6 volume steps up)
```

Then return the volume to the reference and leave it there.

## Part 2 — sweep baseline (6 minutes, 8 more files)

Eight further positions around the driver's headrest, spread about 20 cm in
each direction, same spread as session 4 so the result is comparable with
`results/session4/baseline_pooled_18.csv`. With `lin_ref.wav` that is nine.

```
base2.wav ... base9.wav
```

## Part 3 — pink noise, moving microphone (3 minutes, 2 files)

Play the pink file. Start the recorder, wait a second, then move the
microphone **slowly and continuously** through the same volume the nine
sweep positions covered, for the full minute. Keep it pointing the same way.
Two takes.

```
pink1.wav  pink2.wav
```

## Part 4 — optional, 1 file

Swap the SoloCast into the identical clamp position and record one sweep.

```
solocast_same_spot.wav
```

It changes no setting. It buys two things: a control that separates "new
microphone" from "different day, position or volume" if the new baseline
looks unlike session 4's, and a test of the prediction that the SoloCast
reads about 1.5 dB low above 6 kHz (`docs/targets.md`). Do it if the clamp
is up and there is time.

---

# Processing

Put everything in `Recordings/Session5/`.

```
# 1. the gate: shape must not change with level
.venv/bin/careq measure Recordings/Session5/lin_loud.wav \
    --stimulus stimulus/stimulus.json --out out/lin_loud.csv
.venv/bin/careq measure Recordings/Session5/lin_ref.wav \
    --stimulus stimulus/stimulus.json --out out/lin_ref.csv \
    --compare out/lin_loud.csv --plot out/linearity.png

# 2. pooled sweep baseline, calibrated
.venv/bin/careq measure Recordings/Session5/lin_ref.wav Recordings/Session5/base*.wav \
    --stimulus stimulus/stimulus.json --mic-cal imm6_cal.txt \
    --out results/session5/baseline_sweep.csv --plot results/session5/baseline_sweep.png

# 3. moving-mic pink noise, calibrated, against the sweeps
.venv/bin/careq rta Recordings/Session5/pink1.wav Recordings/Session5/pink2.wav \
    --mic-cal imm6_cal.txt --out results/session5/baseline_pink.csv \
    --compare results/session5/baseline_sweep.csv --plot results/session5/pink_vs_sweep.png

# 4. refit the three voicings
for T in mazda_neutral mazda_warm mazda_bass; do
  .venv/bin/careq fit --measurement results/session5/baseline_sweep.csv \
      --model results/session3/eq_model.json --target $T --max-boost 4 \
      --out results/session5/fit_$T.json --plot results/session5/fit_$T.png
done
```

---

# What to look for, in order

1. **Linearity gate.** `lin_ref` against `lin_loud`, level removed from
   both, should agree within about 1 dB. A shape difference, especially the
   bass flattening at the louder setting, means the limiter is active;
   drop the reference volume 3 or 4 steps and redo Parts 0 and 1.
2. **Pink against sweeps.** Should agree within about 1 dB, the
   repeatability of a multi-position average. The synthetic car puts them
   at 0.04 dB, because a car decays in 25 ms against a 500 ms analysis
   window. Disagreement is diagnostic, not noise: suspect level-dependent
   behaviour or a microphone that moved during a sweep.
3. **The treble bands.** Does the calibrated fit land near the by-ear
   **-4 -4 -2**? If so, two independent methods agree and the neutral
   profile is settled. If not, the gap is preference versus accuracy, which
   is worth knowing on its own.
4. **Everything below 4 kHz** should look much like session 4. Two
   microphones already agreed there within position scatter, so a large
   change would mean something else moved.

# What does NOT need redoing

The 13-band model. It is a ratio of two recordings through one microphone,
so the microphone cancels and `results/session3/eq_model.json` is already
correct. The cancellation covers any fixed linear element, microphone,
cabin and position alike, and any constant gain. It does not cover
level-dependent behaviour, which is why ALC broke it and why Part 1 exists.
