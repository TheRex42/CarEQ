  # How careq works, and how the Mazda 3 target was arrived at

Written 2026-09-13 after Phase 0 completed: four recording sessions in a
2021 Mazda 3, all 13 EQ bands identified, a tuning fit computed and then
verified by measuring the car again with the fitted settings in place.

This document has two halves. Part 1 is what the code does at each step and
why each choice was made. Part 2 is the chain of measurements that produced
the final settings, including the things that went wrong and what they cost.

---

# Part 1: the pipeline

Five commands, each consuming the previous one's output:

```
careq gen       -> stimulus WAV for the USB stick + stimulus.json
careq measure   -> recording(s)            -> smoothed response CSV
careq identify  -> baseline + band runs    -> eq_model.json
careq fit       -> baseline + model + target -> 13 integers
careq simulate  -> synthetic recordings of a known car (tests only)
```

## 1. Stimulus (`careq/signals.py`)

**What it writes.** A 10 s exponential sine sweep from 20 Hz to 20 kHz at
-12 dBFS, 48 kHz mono, preceded by 1 s of silence and followed by 2 s, the
whole 13 s block repeated 3 times: 37 s total. Plus `stimulus.json`, which
records every parameter, because the inverse filter used later must be
derived from exactly the sweep that was played.

**Why an exponential sweep.** In an exponential (log) sweep the instantaneous
frequency rises geometrically, so each octave gets equal time. Two properties
matter here:

- *Deconvolution is exact.* Convolving the recording with a time-reversed,
  amplitude-corrected copy of the sweep (the "inverse filter") collapses it
  to the system's impulse response. `inverse_filter` is normalised so that
  `fftconvolve(sweep, inv)` peaks at exactly 1.0, which pins where the
  impulse response lands: index `len(sweep) - 1` plus the acoustic delay.
- *Distortion separates itself in time.* This is the Farina (2000) trick.
  Harmonic distortion produced by the amplifier and speakers appears in the
  deconvolved result as separate impulses, arriving **before** the linear
  one, at `duration * ln(k) / ln(f2/f1)` seconds for the k-th harmonic. With
  a 10 s sweep over three decades that is 1.0 s before for the 2nd harmonic.
  The analysis window starts 20 ms before the linear peak, so every
  distortion product falls outside it and is discarded. The measurement is of
  the *linear* response only, which is what an EQ can correct.

**Why -12 dBFS.** Headroom. The sweep must not clip in the head unit, the
amplifier, or the recorder. 12 dB proved to be enough even when the car's
automatic level control was quietly adding 6 dB (see Part 2).

**Why three repeats.** Two reasons, one obvious and one not:

- Averaging three sweeps in the power domain lowers the noise floor.
- The spacing between the repeats measures the clock difference between the
  phone/recorder and the head unit's DAC. Consumer clocks differ by tens of
  parts per million; over a 10 s sweep that smears the high end. Since the
  playback spacing is known exactly (`n_sweep + n_post` samples), comparing
  it with the recorded spacing gives the drift directly.

## 2. Measurement (`careq/measure.py`)

One recording in, one smoothed magnitude response out. Six stages:

**a. Load and rate-match.** `load_wav` takes channel 0 of a multi-channel
file and resamples (polyphase, exact rational ratio) to the stimulus rate.
Every recording in this project arrived at 44.1 kHz and was resampled to 48.

**b. Find the sweeps.** Cross-correlate the whole recording with the unit
sweep; peaks mark onsets. This needs no clock sync, no timestamp, and no
knowledge of when the recorder was started: press record, press play, stop.
The peak-to-median ratio of the correlation is reported as `corr-quality`,
a rough measure of how cleanly the sweep stands out. Real recordings scored
250 to 4400; the synthetic car scores about 8000.

**c. Estimate drift.** `estimate_drift_from_repeats` deconvolves a short
window around each onset, cross-correlates the resulting impulse responses
against the first one with parabolic interpolation for sub-sample precision,
and least-squares fits position against sweep index. The slope is the
stretch factor. This is accurate to about 1 ppm and assumes nothing about
the cabin.

> **A dead end worth recording.** Two other drift estimators were built and
> discarded: impulse-peak sharpness maximisation and per-band arrival time.
> Both are biased by 10 to 40 ppm in a reverberant cabin, because cabin
> reflections move the apparent peak. A single-sweep recording therefore
> gets *no* drift estimate rather than a wrong one. This costs little:
> even 100 ppm changes a 1/3-octave magnitude by under 0.5 dB.

Every real recording in this project measured +10 to +13 ppm, consistently,
which is the true offset between the phone's crystal and the car's.

**d. Deconvolve and window.** Each sweep segment is resampled by the drift
ratio, convolved with the inverse filter, and the linear impulse response
located. `window_ir` then cuts it: a half-Hann rise over the 20 ms before
the peak, flat through 350 ms, and a raised-cosine fall over the last 150 ms
of a 500 ms window.

*Why window at all.* The window is a compromise between frequency resolution
and how much of the room is included. Too short and low frequencies are
lost; too long and late reflections plus noise dominate. 500 ms comfortably
contains a car cabin's decay, which is on the order of 50 to 100 ms.

**e. Spectrum and noise.** FFT of the windowed impulse response gives the
complex transfer function. A second window of identical shape, taken 900 ms
after the peak where the impulse response has decayed, gives a noise-only
spectrum of the same length; the ratio is the per-frequency SNR. This is how
the project established that road noise was irrelevant (Part 2).

**f. Smooth.** `frac_octave_average` averages **power** over a 1/3-octave
window centred on each of 480 log-spaced frequencies from 20 Hz to 20 kHz.

*Why power, not dB.* Averaging in the power domain is what energy does
physically, and it does not let a deep null dominate the mean. Where the
FFT resolution is too coarse for the window to contain two bins (below about
100 Hz) the code interpolates instead of averaging.

*Why 1/3 octave.* It matches the bandwidth of the EQ bands being fitted and
is roughly the ear's resolution for steady tonal balance. Finer smoothing
shows interference ripple that moves when the listener's head moves, which
no EQ should chase.

**Multi-position pooling.** `Measurement.combine` pools sweeps from several
recordings, and `average_power` averages responses. Always in the power
domain, never on raw waveforms: two recordings of the same sweep at
different positions have different phase, and averaging the waveforms would
create comb filtering that neither position exhibits.

## 3. Identification (`careq/identify.py`)

The head unit's 13 sliders have fixed, undocumented centre frequencies and
filter shapes. Rather than assume them, measure them.

**The basis.** Record a baseline with all sliders at 0, then one recording
per band with that band at +9. For band k:

```
basis_k(f) = 10 log10( smooth(P_k(f)) / smooth(P_baseline(f)) )
```

Both spectra are smoothed *first*, then divided. The cabin, the speakers,
the microphone and the recorder all appear in both and cancel exactly. What
remains is the filter, and nothing else. Smoothing before dividing (rather
than after) matters because it makes the basis exactly the quantity the fit
later adds to the smoothed baseline, so prediction and model stay consistent.

The per-step curve is `basis_k / 9`, and the assumption that gain scales
linearly with step count was checked by measuring one band at +5: it matched
5/9 of the +9 curve within 0.2 dB.

**Level correction.** One band cannot change the whole spectrum. So any
broadband difference between a band recording and the baseline is something
else: the volume knob, recorder gain, or the car's slow level drift.
`far_field_offset_db` measures the median difference more than 1.5 octaves
from the band's peak and subtracts it, and warns above 0.75 dB. Without this
the fit would believe each band lifts everything.

**Cut factor.** A run at -9 yields `notes["cut_factor"]`, the least-squares
ratio of the measured cut to the negated boost near the peak. Measured 0.93
on this car for two different bands.

> Note: 1/3-octave *power* smoothing itself shrinks a cut slightly more than
> it shrinks the equivalent boost. A synthetic filter with a true factor of
> 0.98 measures as 0.93 through this pipeline. The underlying filters are
> therefore close to symmetric; 0.93 is still the right number for the fit,
> which works entirely on smoothed curves.

**Diagnostics.** A peaking-filter fit of each basis reports centre frequency,
Q and dB/step. It is descriptive only, never used by the fit, which works
with the measured curves. It is how the band table in Part 2 was produced.

## 4. Fitting (`careq/fit.py`)

Find 13 integers minimising the weighted error between the EQ'd response and
a target.

**The model.**

```
error(f) = measured(f) + sum_k per_step_k(f) * (e(x_k) - e(cur_k)) + c - target(f)
e(x) = gain_scale * (cut_factor if x < 0 else 1) * x
```

- `measured` is the pooled multi-position baseline.
- `cur` are the settings that were in the head unit when `measured` was
  recorded; all zero for a flat baseline, non-zero when iterating.
- `c` is a free level offset, solved analytically at every step. Its
  presence means the fit never wastes bands on overall loudness, and makes
  a solution of all cuts equivalent to one of all boosts.
- `gain_scale` is 0.95: with ALC off, two adjacent bands at +9 deliver about
  95% of the sum of their individual curves.

**Normalisation.** Target and measurement are each shifted to zero mean over
200 Hz to 2 kHz before fitting, so the comparison is of *shape*. Absolute
level is arbitrary anyway.

**Weighting.** 1.0 from 60 Hz to 12 kHz, tapering log-linearly to 0.05 at
30 Hz and 16 kHz. Below 30 Hz the microphone and the cabin's pressure
response dominate and the speakers cannot deliver output; above 16 kHz the
microphone is unknown. Neither is worth spending sliders on.

Those weights are applied on a grid that is uniform in log frequency, so
every octave counts equally. That is the natural axis for the thing being
adjusted, since the EQ bands are themselves log spaced, but it is not how
the ear divides the spectrum. Auditory filter bandwidth is roughly constant
below about 500 Hz and proportional to frequency above it, so the bass
holds far fewer resolvable bands than equal-per-octave implies: the
midpoint of 20 Hz to 20 kHz is 632 Hz on a log axis and about 2 kHz on an
ERB axis, and 20 to 632 Hz is half of a log chart but 28 % of auditory
bandwidth.

`erb_density(f) = f / (f + 228.8)` is the derivative of the ERB number with
respect to log frequency, and multiplying the weights by it restores the
ear's proportions. Every fit reports both numbers, whichever it optimised
(`--erb-weight` switches which one is optimised). The ERB figure is always
the lower of the two here, because the largest errors are in the bass,
which it de-emphasises. It measures frequency *resolution* rather than
importance, so it is offered alongside the log-uniform number, not as a
replacement.

**Solve.** Bounded weighted least squares (`scipy.optimize.lsq_linear`) over
the 13 gains plus the offset. Because `e(x)` bends at zero (cuts are scaled
by `cut_factor`), the solve is repeated with column scales updated from the
current signs until they stop changing, typically two iterations.

**Round.** Rounding the continuous solution to integers can cost more than
it should, because errors in neighbouring bands compound. So rounding is
followed by coordinate descent: try each band at +-1, keep any move that
lowers the weighted RMS, repeat until no move helps. A test asserts the
integer result is never worse than naive rounding and within 0.5 dB of the
continuous solution across 30 random models.

**Boost cap.** `--max-boost` limits positive steps separately from cuts.
Boosts consume digital headroom in the head unit; cuts do not, and the free
level offset means the fit loses almost nothing by preferring them. Capping
boosts at +4 cost 0.15 dB of predicted accuracy and kept 5 dB of headroom.

**Iterating.** Set the fitted values, measure again, and refit with
`--current` pointing at those settings. The second pass corrects whatever
the linear model got wrong. On the synthetic car the prediction error falls
0.54 -> 0.24 -> 0.06 dB over three passes.

## 5. The synthetic car (`careq/simulate.py`)

Every stage is tested against a fake car with known ground truth: 13 peaking
filters at the measured centres and Qs, a cabin impulse response (direct
sound, discrete reflections, a weak high-passed diffuse tail, broadband
colouration), a microphone tilt, clock drift applied by windowed-sinc
resampling, and pink noise at a chosen SNR.

Two details worth noting. The head-unit model applies a **soft limiter** to
the summed gain curve (knee 7 dB, cap 10.5 dB) and realises the result as a
minimum-phase FIR, so that adjacent bands at large boosts interact the way
the real unit does while each setting remains a proper linear filter. And
the tests judge the fit against an **oracle** that knows the true filters
exactly, asserting the pipeline recovers more than 80% of what the oracle
can remove, rather than an absolute percentage. The achievable fraction
depends on the cabin, not on the code; an early version wasted effort tuning
the fake cabin to hit an arbitrary absolute number.

30 tests, about a minute.

---

# Part 2: how the target was arrived at

## Session 1 (12:16-12:38): six bands, and four lessons

Odd bands at +9, one baseline at the start, phone-style handling. Every file
was clean by the diagnostics: 3 sweeps found, drift identical, SNR 45 to
65 dB, no clipping. The band shapes came out plausible. But:

1. **The band labels were wrong.** Bands 1, 3 and 5 landed on their printed
   labels (41, 102, 253 Hz) but band 7 measured 968 Hz against a printed
   630, band 9 measured 2.5 kHz against 1.6 k, band 11 measured 5.6 kHz
   against 4 k. The slider layout is not the 1/3-octave ladder that had been
   assumed. This is exactly what the "measure, don't assume" design was for.
2. **One baseline is not enough.** Over 22 minutes the level drifted about
   2.5 dB/hour in the midrange, and a narrow feature near 7 kHz moved by up
   to 3 dB non-monotonically. The first was drift; the second was the
   microphone shifting each time the car was entered to change a slider.
3. **Road noise was a non-issue,** settled by measurement rather than
   argument. Measuring the pre-sweep silence in every file gave a cabin
   noise floor; the achieved SNR was 37 to 53 dB at 40 Hz and above 43 dB
   everywhere above 50 Hz, while ambient level varied 13 dB between files as
   traffic passed with no visible effect. A 10 s sweep buys about 40 dB of
   processing gain. Only 20 to 31 Hz was noise-limited, and nothing there is
   controllable anyway.
4. **A false conclusion, later overturned.** Band 9's -9 run appeared to cut
   9.1 dB where +9 boosted 7.4. "Cuts are deeper than boosts" was recorded
   as a finding. It was an artefact of an unreliable file.

## Session 2 (14:00-14:45): all 13 bands, and a wrong diagnosis

Even bands, interleaved baselines, microphone moved to the passenger
headrest. This gave the full band table and two experiments.

The cut test (bands 4 and 10 at -9) showed cuts mirror boosts at 0.93 with
the same centre and width, correcting session 1.

The superposition test did not go as expected. Bands 9 and 10 both at +9
produced a 9.8 dB plateau where the sum of their individual curves predicted
11.7. Least squares decomposed it as 0.85 x band 9 + 0.64 x band 10, with
band 9 apparently widened from Q 2.6 to Q 1.1. Four separated bands at
moderate settings delivered 84 to 92% of nominal. The conclusion drawn was
that the head unit solves its band gains jointly, like a designed graphic EQ
rather than independent filters, and the fit's gain scale was set to 0.87.

That conclusion was wrong.

## Session 3 (15:22-15:42): ALC, and the real explanation

The user found that the car's Automatic Level Control had been on. It should
be inert in a parked car, since it responds to road speed, and nothing in
the data suggested level-dependent gain. Rather than assume, a nine-file
session with ALC off repeated two session 2 measurements and replaced the
four session 1 bands.

ALC was adding 5.8 dB. Every session 3 file sat that much below session 2,
and matched session 2's final "level control" file within 0.1 dB. With the
sweep at -12 dBFS, ALC lifted it to about -6, and a +9 boost on top of that
ran into the head unit's output limiter. The "jointly-solved graphic EQ" was
a clipped measurement.

With ALC off:

| bands 9 and 10 at +9 | ALC on | ALC off |
|---|---|---|
| measured peak | 9.8 dB | 10.6 and 11.0 dB |
| sum of singles | 11.7 dB | 11.2 dB |
| ratio | 0.84 | 0.95 and 1.02 |

Superposition holds. The gain scale went to 0.95, `--max-boost` was added
(the headroom lesson survives: boosts cost the same on real music), and ALC
off at a fixed volume became the reference condition.

Session 1's odd bands were also 0.5 to 2 dB low with band 11 at the wrong
frequency, so they were replaced. The combined 13-band model
(`results/session3/eq_model.json`) takes bands 1, 2, 4, 6, 8, 12, 13 from
session 2, bands 3, 5, 7, 11 from session 3, and averages the two sessions
for bands 9 and 10:

| band | centre | Q | dB/step |
|---|---|---|---|
| 1 | 37 Hz | 1.6 | 0.85 |
| 2 | 62 Hz | 2.1 | 0.94 |
| 3 | 102 Hz | 2.2 | 0.90 |
| 4 | 160 Hz | 2.6 | 0.92 |
| 5 | 251 Hz | 2.2 | 0.95 |
| 6 | 489 Hz | 2.1 | 0.84 |
| 7 | 987 Hz | 2.2 | 0.94 |
| 8 | 1.57 kHz | 1.9 | 0.85 |
| 9 | 2.56 kHz | 2.3 | 0.92 |
| 10 | 3.94 kHz | 2.2 | 0.98 |
| 11 | 6.34 kHz | 1.9 | 0.94 |
| 12 | 10.1 kHz | 1.5 | 0.97 |
| 13 | 16.9 kHz | 0.7 | 0.99 |

So the labels are 40, 63, 100, 160, 250, 500, 1k, 1.6k, 2.5k, 4k, 6.3k, 10k,
16k Hz, and the sliders are ordinary peaking filters of Q about 2 delivering
about 0.9 dB per step, with band 13 a broad top-octave shelf.

## Session 4 (16:49-17:01): the baseline that the fit actually uses

Identification is mic-independent because every basis is a ratio. The
*baseline* is not: it is the car as heard at one place, and it decides what
the fit tries to correct. Nine recordings around the driver's headrest,
forward to aft, empty driver's seat, pooled in the power domain.

Averaging mattered. A single passenger-seat spot showed a -8.2 dB notch at
500 Hz; the nine-position average showed -0.5 dB. That notch was an
interference null that moves with the microphone, and a fit against the
single spot spent bands 4 and 6 at +9 chasing it. What survived averaging
was real: a +14 dB cabin hump at 60 to 120 Hz, a -5 dB dip at 160 Hz, and a
+4 dB bump at 1.6 kHz specific to the driver's position.

## Choosing the target

Four candidates were fitted against the same recordings: HouseCurve's Car A,
Car B (JBL-derived, the bundled default) and Car C, plus a custom
flat-mids-with-bass-shelf curve matching the user's stated preference.

All four agree within 0.5 dB from 250 Hz to 2 kHz. The entire choice is bass
amount below 160 Hz and treble tilt above 4 kHz. Three facts decided it:

- Bands 2 and 3 pin at -9 for every target. The hump exceeds all of them.
- The treble bands are where the targets disagree most, and also where the
  HyperX SoloCast's response is unknown: no full-band third-party
  measurement of it exists. Car A's -6/-6/-7 there
  would be a large correction stacked on an unmeasured microphone.
- The user's own preference was flat mids with a slight bass shelf.

Chosen: flat mids, +3 dB shelf below 80 Hz, gentle -2 dB tilt to 20 kHz,
with boosts capped at +4. Predicted weighted error 4.54 -> 2.64 dB, settings

```
+4 -9 -9 +3 0 +4 +3 -6 +1 +4 -1 -1 0
```

## Verification: the number that matters

Settings entered, same positions recorded again.

| | weighted RMS vs target |
|---|---|
| baseline, EQ flat | 4.54 dB |
| predicted after fit | 2.64 dB |
| **measured after fit** | **2.73 dB** |

The change the EQ made matched the model's prediction within 1.05 dB RMS.
An accidental second flat-EQ session, recorded 25 minutes after the first,
provides the scale: two pooled nine-position baselines of the same car in
the same state differ by 1.0 dB RMS. The model is therefore as accurate as
the measurement is repeatable, and further iteration cannot improve itS.

The bass came out better than predicted: cuts at 63 and 100 Hz landed 1.5 to
2 dB deeper than the model said, leaving 1.1 dB RMS in the 60 to 120 Hz
region against 2.5 predicted.

A second fit pass was computed and rejected. It predicted a 0.26 dB gain, of
which 0.15 came from cutting bands 11 to 13 by 3 to 5 steps, chasing treble
that the microphone cannot vouch for and that moved 1.4 dB between the two
flat baselines on its own. The remaining 0.11 dB is inside the method's
one-step scatter.

## What remains, and why

Measured in the car with the pass-1 settings, the two weightings put the
result at 2.73 dB equal-per-octave and 1.79 dB by auditory bandwidth before
EQ, 2.47 and 1.56 after. The three bundled voicings land at 2.52 to 2.66
log-uniform and 1.87 to 1.98 ERB-weighted.

| region | factory | after EQ |
|---|---|---|
| 60-120 Hz | 8.9 dB | 1.1 dB |
| 120-250 Hz | 4.0 | 2.4 |
| 250 Hz-1 kHz | 3.1 | 1.5 |
| 1-4 kHz | 2.3 | 1.6 |
| 4-16 kHz | 1.7 | 1.4 |

Above 250 Hz the factory tuning was already within about 3 dB of every car
target and the EQ improved it by roughly a decibel: a competent OEM voicing,
with the caveat that the region above 4 kHz is measured through an
uncalibrated microphone. Below 250 Hz it was not tuned at all in any
meaningful sense; the +14 dB hump is the cabin, and removing 8 dB of it was
the single largest improvement of the exercise.

The residual splits roughly one third filter-shape cost (fixed Q about 2 at
two-thirds-octave spacing cannot reach the 2 kHz feature sitting between
bands 8 and 9) and two thirds things no equaliser fixes: an interference
null at 160 Hz that cannot be filled by adding power, and the speakers'
physical roll-off below 50 Hz. A parametric EQ with the same +-9 dB range
would leave most of it.

Three voicings were then bundled (`mazda_neutral`, `mazda_warm`,
`mazda_bass`) differing only along the two axes the data says matter, for
listening tests that measurement cannot settle.

## Identification could be a third of the work

Measured after the fact, from the finished model. The 13 bands turned out
to be regular: Q clusters around 2.1 (only band 13 at 0.74 is an outlier)
and dB/step spans 0.84 to 0.99. So most of the bases are predictable from a
few of them.

Refitting with a model where only some bands were measured and the rest
were interpolated (known centre, interpolated Q and dB/step), then judging
the resulting settings against the *full* measured model:

| measured | recordings | settings vs full | delivered |
|---|---|---|---|
| all 13 | 15 | reference | 2.52 dB |
| bands 1, 5, 9, 13 | 5 | max 1 step | 2.54 dB |
| bands 1, 4, 7, 10, 13 | 6 | max 1 step | 2.54 dB |
| bands 1, 7, 13 | 4 | max 2 steps | 2.56 dB |

Four band recordings plus a baseline land within one step of the full
model, which is inside the method's own scatter. The 45-minute
identification session could be about ten minutes.

The catch is that this is only knowable *because* all 13 were measured. The
first car of a given head-unit model needs the full set; after that a
four-recording run confirms the shared model fits that particular car.

This also sets the architecture for anything more general. Identification
is a ratio of two recordings through the same microphone, so it is
microphone-independent and therefore shareable between users and phones:
measure a head-unit model once, everyone with that car reuses it. The
baseline is the opposite, being specific to one cabin, one seat and one
listener, and can never be shared. The expensive half is the transferable
one.

## Open items

- **Microphone calibration.** A single baseline recorded with a calibrated
  measurement microphone alongside the SoloCast would produce a permanent
  correction file and make the treble decisions real.
- **REW cross-check.** `careq measure --save-ir` writes the averaged impulse
  response as a WAV for import into REW, to confirm the magnitude response
  against an independent implementation. Not yet done.
- ~~The Bass tone control~~ is not available: selecting Customize EQ
  replaces Bass and Treble on this head unit, so the 13 sliders are the
  only gain there is. The residual bass hump is permanent.
- **An unexplained level jump:** the verification recordings were 18.6 dB
  louder in absolute terms than both flat sets, while the EQ accounts for
  under 1 dB of that. Either the volume or the recorder gain changed. The
  fit normalises level so the result stands, but one file clipped and was
  dropped.
