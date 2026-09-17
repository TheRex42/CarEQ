# Session 5 — calibrated microphone, simplified

Dayton iMM-6 (TRRS) through an Apple USB-C dongle into the phone, with a
USB-C extension on the long run. **7 files and about 13 minutes in the
car**, or 14 files and 25 minutes with the optional four-band
confirmation, plus 10 minutes of checks at the desk beforehand.

This is a deliberate simplification of an earlier 14-file draft, and it is
also a return to what `docs/procedure.md` specified from the beginning:
a hand-held tuning baseline taken from the occupied driver's seat. Session 4
only deviated from that because the SoloCast came with a stand and clamping
it was easy. The iMM-6 is awkward to clamp and easy to hold, which points
back at the original design.

## What the session actually has to produce

Only two things.

1. **A tuning baseline** at the driver's listening position, calibrated.
2. **Confidence the chain is sane**: the right microphone is selected, the
   volume is in the linear region, and the dongle is not shaping the signal.

The 13-band model is **not** one of them. It is a ratio of two recordings
through one microphone, so the microphone cancels and
`results/session3/eq_model.json` is already correct. Nothing about the new
microphone, the dongle, or the seat being occupied changes it.

## Where the simplification comes from

The nine clamped sweep positions existed to average over space. A pink-noise
run with the microphone moving does that better and continuously, and wants
the microphone hand-held. So the clamp is only needed where the microphone
must hold still, which is the diagnostics, and those all happen at a single
position.

---

# At the desk first (10 minutes)

**1. Test the whole chain, assembled exactly as it will be used, USB-C
extension included.** The extension is the component most likely to
misbehave, since USB-C extension cables are out of specification.

Record ten seconds and **tap the iMM-6 capsule**. Loud, obvious taps mean
you are on the external microphone. Faint ones mean the app fell back to the
phone's built-in microphone, which is 21 dB hot at 12.5 kHz
(`docs/microphone.md`) and would waste the session silently. Check the
input selector and set the audio source to unprocessed or voice recognition,
never the default.

**2. Download the calibration file** by serial number, keep it as
`imm6_cal.txt`, and check careq reads it and that the sign is right:

```
.venv/bin/python -c "
import sys, numpy as np; sys.path.insert(0,'.')
from careq.measure import Response
c = Response.from_csv('imm6_cal.txt')
print(len(c.freq), 'points,', c.freq.min(), '-', c.freq.max(), 'Hz')
for f in (30, 100, 1000, 5000, 10000, 16000):
    print(f, round(float(np.interp(f, c.freq, c.db)), 2), 'dB')"
```

A smooth curve within a few dB, typically rising a little up top. The file
states the **microphone's own response** and careq subtracts it, so a mic
that reads hot at 10 kHz is positive there and the corrected measurement
comes out lower. If applying it makes the car look brighter, it is inverted.

---

# In the car

ALC **off**, fader and balance centred, all 13 sliders at 0. Bass and Treble
are unavailable while Customize EQ is selected. Engine off, accessory mode,
HVAC off, doors shut. Recorder: mono WAV, fixed gain, no processing, running
3 s past the end of every file.

## Part 0 — volume reference (3 minutes)

Play `stimulus/careq_pink_48k_60s.wav`. With an SPL meter or phone app at
the driver's head position, set the head unit to read **75 dB, C weighted,
slow**. Note the Mazda number. Sessions 1-4 used 25.

The sweep file runs 5.0 dB hotter than the pink file at the same setting, so
expect about 80 dB during sweeps (`docs/level.md`). Check the recorder peaks
near -12 dBFS on a sweep and never clips.

## Part 1 — the fixed-position block (5 minutes, 4 files)

**One position, four recordings, do not touch the microphone between them.**
This is the only part that needs the microphone held still, so prop it,
wedge it against the headrest with a towel, or use any small stand. Put it
roughly where a driver's ear would be.

```
fix_sweep_ref.wav       sweep at the reference volume
fix_sweep_loud.wav      sweep about 6 dB louder, then return the volume
fix_pink_ref.wav        pink noise at the reference volume
fix_solocast.wav        SoloCast swapped into the identical spot, one sweep
```

Four files, four questions, each answered by a pair:

| pair | question |
|---|---|
| `fix_sweep_ref` vs `fix_sweep_loud` | is the volume in the linear region, or is the limiter active? |
| `fix_sweep_ref` vs `fix_pink_ref` | do sweeps and pink noise agree in this car? |
| `fix_sweep_ref` vs `fix_solocast` | is the dongle shaping anything below 4 kHz? |
| all of them | the microphone never moved, so every difference is real |

## Part 1b — four-band confirmation (12 minutes, 7 files). Optional.

**Microphone stays exactly where Part 1 left it.** If it has moved, this is
worthless; re-seat it and start Part 1 again.

Four bands and three baselines, interleaved so the level drift of about
1 dB per session can be removed:

```
id_base1.wav      all sliders 0
id_b01_p9.wav     band 1 (40 Hz) at +9, everything else 0
id_b05_p9.wav     band 5 (250 Hz) at +9
id_base2.wav      all sliders 0
id_b09_p9.wav     band 9 (2.5 kHz) at +9
id_b13_p9.wav     band 13 (16 kHz) at +9
id_base3.wav      all sliders 0
```

**Why four and not thirteen.** Measured after the fact from the finished
model, bands 1, 5, 9 and 13 plus a baseline reproduce the full 13-band
model within one step and 0.02 dB of delivered error (`docs/method.md`).
That was computed retrospectively and has never been tested by actually
recording only four.

**Why bother at all.** The band model is a ratio of two recordings through
one microphone, so the microphone cancels and the model should be unchanged
by any of this. That claim carries a great deal of weight in this project:
it is why the model survives a new microphone, why identification would be
the shareable half if this were ever generalised, and why re-identification
is not on the roadmap. It is sound theory that has never been checked
against a genuinely different microphone. These five recordings check it.

**Skip it** if Part 1's diagnostics came back clean and you would rather
have the time. It confirms something, it does not enable anything.

## Part 2 — the baseline: moving microphone, occupied seat (5 minutes, 3 files)

Sit in the driver's seat in normal posture. Play the pink file. Hold the
iMM-6 at ear height, **10-20 cm from your head**, capsule up, and move it
slowly and continuously through the volume your head occupies for the full
minute. Three takes, and deliberately vary the path between them: one
favouring left and right, one forward and back, one high and low.

```
move1.wav  move2.wav  move3.wav
```

Do not strap it to your head. The target curves assume a microphone at the
listening position, not at the ear. Keep your hand below and behind the
capsule, not beside it, and move slowly enough that you hear no rustle.

---

# Processing

Recordings in `Recordings/Session5/`.

```
# the linearity gate: shape must not change with level
.venv/bin/careq measure Recordings/Session5/fix_sweep_loud.wav \
    --stimulus stimulus/stimulus.json --out out/loud.csv
.venv/bin/careq measure Recordings/Session5/fix_sweep_ref.wav \
    --stimulus stimulus/stimulus.json --out out/ref.csv \
    --compare out/loud.csv --plot out/linearity.png

# sweeps vs pink, same spot, same minute
.venv/bin/careq rta Recordings/Session5/fix_pink_ref.wav \
    --out out/fix_pink.csv --compare out/ref.csv --plot out/pink_vs_sweep.png

# is the dongle flat? below 4 kHz the two mics are known to agree
.venv/bin/careq measure Recordings/Session5/fix_solocast.wav \
    --stimulus stimulus/stimulus.json --out out/solocast.csv
.venv/bin/careq measure Recordings/Session5/fix_sweep_ref.wav \
    --stimulus stimulus/stimulus.json --mic-cal imm6_cal.txt \
    --out out/imm6.csv --compare out/solocast.csv --plot out/chains.png

# optional: does the band model come out the same through a different mic?
.venv/bin/cat > Recordings/Session5/manifest.json <<'JSON'
{
  "stimulus": "../../stimulus/stimulus.json",
  "baseline": ["id_base1.wav", "id_base2.wav", "id_base3.wav"],
  "bands": [
    {"band": 1,  "steps": 9, "files": ["id_b01_p9.wav"]},
    {"band": 5,  "steps": 9, "files": ["id_b05_p9.wav"]},
    {"band": 9,  "steps": 9, "files": ["id_b09_p9.wav"]},
    {"band": 13, "steps": 9, "files": ["id_b13_p9.wav"]}
  ],
  "labels_hz": [40, 63, 100, 160, 250, 500, 1000, 1600, 2500, 4000, 6300, 10000, 16000]
}
JSON
.venv/bin/careq identify --manifest Recordings/Session5/manifest.json \
    --out out/model_imm6.json --plot out/bases_imm6.png
# then compare the four measured bases against results/session3/eq_model.json:
# centres within a few %, Q within ~0.3, dB/step within ~0.05

# THE BASELINE
mkdir -p results/session5
.venv/bin/careq rta Recordings/Session5/move*.wav --mic-cal imm6_cal.txt \
    --out results/session5/baseline.csv --plot results/session5/baseline.png

# refit
for T in mazda_neutral mazda_warm mazda_bass; do
  .venv/bin/careq fit --measurement results/session5/baseline.csv \
      --model results/session3/eq_model.json --target $T --max-boost 4 \
      --out results/session5/fit_$T.json --plot results/session5/fit_$T.png
done
```

# What to look for, in order

1. **Linearity.** The two volumes, level removed, should agree within about
   1 dB. Bass flattening at the louder setting means the limiter is active:
   drop the reference volume 3 or 4 steps and redo Parts 0 and 1.
2. **Pink against sweep, same spot.** Should agree closely, since both see
   the same static position. The synthetic car puts them at 0.04 dB. This is
   the first real-car test of the pink path and it gates everything in
   Part 2.
3. **Dongle.** The iMM-6 chain and the SoloCast should track below 4 kHz
   once the calibration is applied. A roll-off under 100 Hz that the
   SoloCast does not show is a dongle high-pass. Second tell: cabin noise in
   the pre-sweep silence should rise 6-12 dB per octave below 100 Hz, and a
   flat or falling floor means something is cutting it.
4. **The three moving takes against each other.** They should agree within
   about 1 dB. That is the only available check that the spatial average has
   converged, which is why there are three and why the paths differ.
5. **The treble bands.** Does the calibrated fit land near the by-ear
   **-4 -4 -2**? Agreement settles the neutral profile.
6. **If Part 1b was done: do the four bases match the existing model?**
   Centres within a few per cent, Q within about 0.3, dB per step within
   about 0.05. Agreement is the first empirical confirmation that the
   microphone really does cancel out of a basis, which the whole
   architecture rests on. Disagreement would be far more interesting and
   would mean the ratio is not cancelling something it should, so check the
   level-offset warnings and whether the microphone moved before believing
   it.

# Order and timing

| part | files kept | minutes | needed? |
|---|---|---|---|
| desk checks (not in the car) | 0 | 10 | yes |
| 0 — volume reference | 0 | 3 | yes |
| 1 — fixed-position diagnostics | 4 | 5 | yes |
| 1b — four-band confirmation | 7 | 12 | optional |
| 2 — moving-mic baseline | 3 | 5 | yes |
| **in the car, without 1b** | **7** | **13** | |
| **in the car, with 1b** | **14** | **25** | |

Parts 1 and 1b share the same microphone position, so do them together and
do not touch the microphone until Part 2. Part 2 is hand-held, so it can
only come last.

# What this gives up, honestly

No nine-position clamped sweep baseline, so the new baseline is **not**
directly comparable with session 4's. It differs by microphone, by method,
and by the seat now being occupied, and those cannot be separated after the
fact. Expect the bass especially to move, since a body in the seat absorbs.

That is an acceptable trade because the goal is the right answer, not an
attributable difference. The one comparison worth preserving is preserved:
Part 1 puts both microphones in the same spot in the same minute, so the
chain can still be checked in isolation.

Session 4's baseline stays on disk as a rough reference. If the new one
looks wildly unlike it below 4 kHz, something went wrong rather than
something changed.
