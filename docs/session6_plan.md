# Session 6 — the calibrated tuning baseline

Written 2026-09-17. Supersedes `docs/session5_plan.md`, most of which has
already been done or overtaken: the band model is confirmed, the
measurement volume is settled, the chain question is answered, and the
SoloCast has been retired.

**The one thing still missing is a tuning baseline taken with a calibrated
microphone.** Everything below serves that. About 12 minutes in the car,
five files, plus an optional verification pass.

## What is already settled, so not re-measured

| question | answer | where |
|---|---|---|
| is the band model right? | yes, and mic-independent: bands 5, 9, 13 agree to 0.41-0.52 dB through a different capsule and converter | `docs/session5_results.md` |
| what volume? | **Mazda 30**. Volume 50 compresses band 1 by 1.9 dB at 35-40 Hz | `docs/level.md` |
| is the dongle distorting? | no, that was the car at volume 50 | `docs/level.md` |
| does the calibration file load, with the right sign? | yes | `docs/session5_results.md` |
| SoloCast comparison | retired; it did its job | |

## Setup

- ALC **off**. Fader and balance centred. **All 13 sliders at 0.**
- **Mazda volume 30.** Set the number; do not set it from an SPL reading.
- Engine off, accessory mode, HVAC off, doors shut, no rain.
- iMM-6, Apple USB-C dongle, USB-C extension, phone. App **digital gain 0**,
  audio source unprocessed.
- Recorder running 3 s past the end of every file.

**Tap test first, every time the chain is reassembled.** Record ten
seconds and tap the capsule. Loud taps mean you are on the iMM-6. Faint
taps mean the app fell back to the phone's own microphone, which is 13 dB
hot above 10 kHz, and nothing after that point is usable.

## Part 1 — pink against sweep, fixed position (3 minutes, 2 files)

Prop the microphone at driver head height with the **driver's seat empty**
and do not touch it between these two.

```
fix_sweep.wav    one sweep file
fix_pink.wav     the pink file
```

Pink noise has been validated only on the synthetic car, where it agrees
with sweeps to 0.04 dB. This is its first real-car test and it gates
Part 2, which relies on it entirely. They should agree within about 1 dB.

Free bonus: `fix_sweep.wav` is also the input for the REW cross-check, the
only external validation never done (`careq measure --save-ir ir.wav`).

## Part 2 — the baseline: moving microphone, occupied seat (5 minutes, 3 files)

Sit in the driver's seat in normal posture. Play the pink file. Hold the
iMM-6 at ear height, 10-20 cm from your head, capsule up, and move it
slowly and continuously through the volume your head occupies for the full
minute. Three takes, deliberately varying the path: one favouring left and
right, one forward and back, one high and low.

```
move1.wav  move2.wav  move3.wav
```

Not strapped to your head: the targets assume a microphone at the listening
position, not at the ear. Hand below and behind the capsule, slow enough
that there is no rustle.

## Then send the files

Five files. I will return, in order:

1. whether pink and sweep agree in the car (the gate)
2. whether the three moving takes agree with each other (convergence)
3. the calibrated baseline and all three voicings refitted against it
4. whether the treble lands near your by-ear **-4 -4 -2** on its own

## Part 3 — verification (optional, 5 minutes, 3 files)

If you can wait in the car while I process, set the returned sliders and
repeat Part 2 exactly, `verify1.wav` to `verify3.wav`. That measures the
error the new settings actually deliver, the way session 4 did. Otherwise
it becomes session 7.

## What the fit will and will not do

- **Band 1 stays at +6** by your listening choice, above the +4 the fit caps
  at. Worth knowing that this costs more at high listening volume: at
  volume 50 the doors already run 7.5 % distortion at 40 Hz before any boost.
- **The treble overrides get retested, not assumed.** Neutral's -4 -4 -2 was
  set by ear to compensate for an uncalibrated microphone. The calibrated
  fit either reproduces it, which settles the neutral profile, or does not,
  which tells us the gap is preference rather than accuracy.
- **The bass hump stays.** Bands 2 and 3 at -9 is the ceiling on this head
  unit and the microphone changes nothing about that.
