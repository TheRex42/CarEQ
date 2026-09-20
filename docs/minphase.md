# Is the head unit's EQ minimum phase? (2026-09-20)

Prompted by a claim that large EQ moves cause phase shift and that the job
"must be done via DSP, not a simple EQ". The first half is true of any
minimum-phase filter and is not a defect; the second half is a false
dichotomy, because the Mazda's Customize EQ *is* DSP — digital biquads in the
head unit. But the whole argument rests on an assumption nobody here had
measured: that the EQ is minimum phase. The pipeline already keeps complex
transfer functions, so it was testable with recordings that already existed.

Result: **where the measurement has the resolution to decide, the EQ is
indistinguishable from minimum phase.** Two of the thirteen bands can be
decided; the other two tried are reported as undecidable rather than as
numbers.

## Why this matters for the method

`careq` is magnitude-only by construction. Phase is discarded at
`Measurement.power = |H|**2`, pooling averages power, and the fit adds dB
curves (`careq/fit.py`, `predict = A @ e(x)`). That is correct regardless of
phase, because the bands are **cascaded**: transfer functions multiply, so dB
magnitudes add exactly whatever each filter's phase is doing. Phase cannot
corrupt a magnitude prediction for a series chain.

What minimum phase adds is the interpretation. If the EQ is minimum phase,
its phase shift is not a side effect to be traded off — it is the correct
companion of the magnitude change, and correcting a minimum-phase deviation
in the speaker or cabin corrects that deviation's phase at the same time.

## Method

For band *k*, the ratio

    R(f) = H_band(f) / H_baseline(f)

is the EQ filter alone: the cabin, the microphone and the rest of the chain
are common to both recordings and cancel. If the EQ is a minimum-phase
biquad, `arg(R)` is fully determined by `|R|` through the Hilbert transform,
up to a pure delay — the two files are aligned only to the sample their IR
peak landed on.

So: derive the minimum phase implied by the measured `|R|` (real cepstrum),
divide it out, allow one free delay fitted by circular regression with equal
weight per octave, and look at what is left. That residual is the excess
phase. Source: `results/minphase/check_minphase.py`.

Three details decide whether the answer means anything:

- **The sweeps are averaged coherently, not in power.** Every IR in a file is
  windowed around its own peak, so the three sweeps are aligned and their
  phase survives averaging. Coherent averaging loses only 1.15 dB against the
  power average over 100 Hz-10 kHz, which is itself a check on the sync and
  drift correction: they hold phase well enough to compare recordings made
  minutes apart.
- **The measured phase is never unwrapped.** An earlier version unwrapped it
  and dragged wrap errors in from out-of-band noise; that alone produced a
  bogus 578 deg for band 13. The residual is formed as a complex product and
  read as a wrapped angle.
- **Outside the swept band the magnitude is eased to unity** over half an
  octave, rather than clamping a boosted value flat to DC, which would invent
  a shelf the head unit does not have.

### The control is the experiment

An excess-phase number on its own is meaningless: it can be measurement
noise. The control is `baseline2 / baseline` — the same condition recorded
twice, no EQ change — pushed through identical code with identical masks. Its
excess phase is the repeatability floor. A band only says something if it
rises above its own control.

## Results

Recordings: `Recordings/Session_5_cal_mic`, iMM-6, ALC off, volume 30.

| band | centre | measured gain | excess phase | control floor | verdict |
|---|---|---|---|---|---|
| 5 | 250 Hz | +8.5 dB | **0.8 deg rms** | 2.2 deg | below the floor |
| 9 | 2500 Hz | +6.8 dB | **10.7 deg rms** | 11.7 deg | at the floor |

Band 5 is the clean case: group delay **3.24 ms measured against 3.15 ms
predicted from the magnitude alone**, from two independent recordings.

Band 9's excess and its control are both elevated, for a reason already in
the notes: 1.5-4 kHz is the driver crossover region, where the response
varies about +-1 dB between recordings. In `minphase.png` the EQ trace and
the control trace sit on top of each other feature for feature, including a
sharp spike near 650 Hz present in both — which is what shows it is the
measurement and not the filter. Band 9's group delay peak (-0.54 ms measured
against +0.68 ms predicted) should not be read as disagreement: group delay
is a derivative and amplifies exactly that scatter.

## Why bands 1 and 13 are not reported as numbers

Both were tried. Both are dominated by artefacts of the test rather than by
the head unit, and a number would be misleading.

**Band 1 (40 Hz).** The minimum-phase reconstruction needs the magnitude at
all frequencies, but the filter's skirt runs below the sweep's usable range,
and a 500 ms IR window is only 20 cycles at 40 Hz. The residual moves from
31.0 deg to 21.4 deg purely as the assumed behaviour below the sweep's lower
edge is changed (`LO` from 20 to 40 Hz). Sensitive to the assumption means
artefact: bands 5 and 9 move by at most 0.25 deg under the same sweep.

**Band 13 (16 kHz).** The delay is ambiguous. At 16 kHz, delays 62.5 us apart
are indistinguishable, and band 13 is the widest filter (Q about 0.75), still
rising at the sweep's 20 kHz limit, so there is no EQ-free region above it to
pin the delay down. The residual is 89 deg when the search is free (it lands
on 849 us) and 39 deg when the search is restricted to delays peak-aligned
IRs can actually have, +-10 samples (it lands on -18.5 us). Note this is
*not* the extrapolation problem: band 13 moves only 0.1 deg when the
out-of-band extension is changed. Not decidable with this data.

The fix for both is a measurement change, not an analysis change: a longer IR
window and a stimulus reaching lower for band 1, and for band 13 an
independent alignment reference so the delay is not fitted.

## Caveats

- Two of thirteen bands. The others were not recorded at +9 through the
  calibrated mic in a session with two baselines.
- "Indistinguishable from minimum phase at this resolution" is not "proven
  minimum phase". The floor is about 2 deg at 250 Hz and about 12 deg at
  2.5 kHz.
- This says nothing about the **cabin**, which is emphatically not minimum
  phase. Reflection nulls do not invert, which is why the fit works on
  1/3-octave smoothed magnitude and why boosting into a null is a waste of
  headroom.
- The fitted inter-file delay for band 9 is -325 us, about 15 samples. That is
  larger than peak alignment alone should give and is not understood; it is
  consistent across weightings and does not change the verdict, since a pure
  delay is exactly what the test is entitled to remove.

## Reproduce

    .venv/bin/python results/minphase/check_minphase.py

Writes `results/minphase/minphase.png` and the table above.
