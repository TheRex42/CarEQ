# Session 4 results (2026-09-13, 16:49-17:01): tuning baseline, fit pass 1

Nine recordings in `Recordings/Session_4/` (two short stray files
dropped), mic clipped around the driver's headrest at nine spots forward to
aft, driver's seat empty, ALC off, session 3 volume. Every file: 3 sweeps,
drift +12.3 to +13.8 ppm, SNR 43-62 dB, sweep-to-sweep 0.06-0.11 dB.
Positions differ from each other by 2-2.6 dB rms in shape, as a spread of
head positions should. Pooled (27 sweeps, power-averaged) baseline:
`results/session4/baseline_pooled.csv`.

## What averaging changed

| | passenger headrest, one spot (s3) | driver, 9 spots averaged |
|---|---|---|
| 500 Hz | -8.2 dB | -0.5 dB |
| 160 Hz | -4.8 dB | -1.8 dB |
| 80-100 Hz cabin hump | +13 dB | +14 dB |
| 4 kHz | -6.2 dB | -4.7 dB |

(all relative to the 200 Hz-2 kHz mean). The 500 Hz notch was a
single-spot cancellation and is gone; the bass hump is real everywhere.

## Fit pass 1

Model `results/session3/eq_model.json`, gain scale 0.95, cut factor 0.93.

| target | boost cap | settings, bands 1-13 | weighted rms before -> after |
|---|---|---|---|
| flat mids + 3 dB bass shelf | 4 | **+4 -9 -9 +3 0 +4 +3 -6 +1 +4 -1 -1 0** | 4.54 -> 2.64 dB |
| flat mids + 3 dB bass shelf | 9 | +9 -9 -9 +4 +1 +5 +4 -4 +2 +5 0 -1 +1 | 4.54 -> 2.49 dB |
| Car B (default) | 4 | +4 -9 -9 +4 -1 +3 +2 -7 0 +2 -4 -4 -4 | 4.58 -> 2.86 dB |
| Car B (default) | 9 | +9 -9 -9 +5 0 +4 +3 -5 +1 +3 -3 -3 -3 | 4.58 -> 2.66 dB |

Recommended: the first row (`results/session4/fit1_flat_bass_shelf_mb4.json`).
The boost cap costs 0.15 dB rms and keeps 5 dB of headroom in the head
unit; the uncapped fits spend +9 on band 1 chasing the region below 40 Hz
where the mic response is unknown and the fit weight is already low.

## All four targets compared (`results/session4/target_comparison.png`)

| target | cap | settings, bands 1-13 | before -> after |
|---|---|---|---|
| Car A (JBL) | 4 | +4 -8 -9 -2 -4 -1 -1 -9 -1 +2 -6 -6 -7 | 4.44 -> 3.01 |
| Car A (JBL) | 9 | +9 -8 -9 0 -3 +1 0 -7 0 +3 -5 -5 -6 | 4.44 -> 2.77 |
| Car B (JBL, default) | 4 | +4 -9 -9 +4 -1 +3 +2 -7 0 +2 -4 -4 -4 | 4.58 -> 2.86 |
| Car B (JBL, default) | 9 | +9 -9 -9 +5 0 +4 +3 -5 +1 +3 -3 -3 -3 | 4.58 -> 2.66 |
| Car C (Crutchfield) | 4 | +4 -9 -9 +4 -4 0 0 -8 -1 +3 -3 -2 -3 | 3.97 -> 2.49 |
| Car C (Crutchfield) | 9 | +9 -9 -9 +5 -3 +1 +1 -6 0 +4 -2 -1 -2 | 3.97 -> 2.33 |
| flat mids + 3 dB shelf | 4 | +4 -9 -9 +3 0 +4 +3 -6 +1 +4 -1 -1 0 | 4.54 -> 2.64 |
| flat mids + 3 dB shelf | 9 | +9 -9 -9 +4 +1 +5 +4 -4 +2 +5 0 -1 +1 | 4.54 -> 2.49 |

How the targets differ from Car B (dB): Car A asks for 4 dB more below
63 Hz and 1.5 dB less at 160 Hz; Car C asks for 2-3 dB more at 100 Hz and
2-4 dB more above 4 kHz; the flat shelf asks for 1-2 dB less bass and 2-3 dB
more treble. All four agree from 250 Hz to 2 kHz within 0.5 dB, so bands
5-8 barely change between them: the whole decision is bass amount below
160 Hz and treble tilt above 4 kHz.

Bands 2 and 3 pin at -9 for every target: the cabin hump is beyond any of
them. Band 8 (1.6 kHz) cuts 4-9 steps for every target: the driver-position
average has a +4 dB bump at 1.6 kHz that the passenger spot did not. The
treble bands (11-13) are where the targets disagree most, and they are also
where the mic response is unknown, so the flat-shelf choice (0 to -1 there)
is the safe one; Car A's -6/-6/-7 is a large cut on top of an unmeasured mic.

## Where the remaining 2.6 dB lives

| region | before | after | note |
|---|---|---|---|
| 30-60 Hz | 5.9 | 3.8 | sub-bass roll-off; nothing to boost into, low weight |
| 60-120 Hz | 8.9 | 2.5 | the cabin hump, still +2.3 dB after two bands at -9 |
| 120-250 Hz | 4.0 | 2.9 | the 160 Hz dip, common to all positions |
| 250 Hz-1 kHz | 3.1 | 1.7 | |
| 1-2 kHz | 2.1 | 1.9 | the driver-crossover region; band 8 at -6 |
| 2-8 kHz | 2.5 | 1.3 | |
| 8-16 kHz | 0.9 | 1.1 | target tilt vs unknown mic treble; left alone |

Everything above 250 Hz ends within about +-2 dB of the target. The bass
hump is the one thing the 13 bands cannot finish: bands 2 and 3 are pinned
at -9 and still leave +6 dB at 80 Hz against a +3 dB target.

**There is no way to get the rest.** On this head unit, selecting Customize
EQ replaces the Bass and Treble tone controls, so the 13 sliders are the
only gain available (confirmed by the owner 2026-09-14; an earlier version
of this document recommended a Bass tone control experiment, which is not
possible). Bands 2 and 3 at -9 is the hard ceiling, and a residual +5 to
+6 dB bump at 80 Hz is what this car does. The target's own +3 dB shelf
means it is not far off what was wanted anyway.

## Pass 2

Set the recommended integers, record the same nine spots (or any five of
them) as before, then:

```
careq fit --measurement Recordings/Session_4b/p1.wav --more p2.wav ... \
          --stimulus stimulus/stimulus.json --model results/session3/eq_model.json \
          --target results/session4/flat_bass_shelf.csv --max-boost 4 \
          --current results/session4/fit1_flat_bass_shelf_mb4.json \
          --out results/session4/fit2.json --plot results/session4/fit2.png
```

The summary's "before" line is then the error of the pass-1 settings as
actually measured, which is the first real test of the whole chain.

# Pass 1 measured (17:24-17:51)

Two more folders. `Recordings/Session4a/` (9 files) was recorded with the
sliders still at 0 by mistake, which makes it a repeat of the flat baseline
and a free repeatability check. `Recordings/Session_4_target_shelf/`
(6 files) has the pass-1 settings +4 -9 -9 +3 0 +4 +3 -6 +1 +4 -1 -1 0 in.
Plots: `results/session4b/pass1_validation.png`, `fit2_flat_bass_shelf_mb4.png`.

## Repeatability of the multi-position baseline

The two flat sets, 25 minutes apart, differ by 1.0 dB rms over 40 Hz-16 kHz
after pooling (each single spot differs from its pool by 1.2-2.4 dB). A fit
on the repeat gives +4 -9 -9 +3 -1 +4 +3 -8 0 +3 -3 -2 -2, the same shape as
pass 1 with 1-2 steps of scatter in the treble. That is the resolution of
the method: about 1 dB, about one step.

## Prediction vs measurement

| | weighted rms vs target |
|---|---|
| baseline, EQ flat | 4.54 dB |
| predicted after pass 1 | 2.64 dB |
| **measured after pass 1** | **2.73 dB** |

The change the EQ actually made matches the model's prediction within
1.05 dB rms (against the repeat baseline; 1.5 dB against the original one),
which is the baseline's own repeatability. The cuts at 63 and 100 Hz came
out 1.5-2 dB deeper than predicted (-9.9 / -10.7 measured against -8.2 /
-8.4), so the bass hump ended better than predicted: 1.1 dB rms in
60-120 Hz against 2.5 predicted. Everything from 50 Hz to 16 kHz is inside
+-2 dB of the target except the 160 Hz dip and the 2 kHz bump between bands
8 and 9, both of which no slider reaches.

| region | before | predicted | measured |
|---|---|---|---|
| 30-60 Hz | 5.9 | 3.8 | 4.6 |
| 60-120 Hz | 8.9 | 2.5 | 1.1 |
| 120-250 Hz | 4.0 | 2.9 | 2.4 |
| 250-500 Hz | 3.4 | 2.3 | 2.1 |
| 500 Hz-1 kHz | 2.9 | 1.3 | 0.8 |
| 1-2 kHz | 2.1 | 1.9 | 1.7 |
| 2-4 kHz | 2.5 | 1.6 | 1.6 |
| 4-8 kHz | 2.4 | 1.0 | 1.0 |
| 8-16 kHz | 0.9 | 1.1 | 1.8 |

## Level jump, one clipped file

The EQ-on recordings are 18.6 dB louder in absolute terms than both flat
sets (200 Hz-2 kHz level -12.7 dBFS against -31.3 / -31.7), while the EQ
itself changes that band by +0.7 dB. Either the head-unit volume or the
recorder gain was different. The fit normalises level so the result above
is unaffected, but the last file (`20260913_174957.wav`) clipped (449
samples at full scale) and was dropped; the first is 2 samples short of
clipping and was kept. Whatever changed needs to go back before the next
recording: if it was the volume knob, the head unit's limiter is now 18 dB
closer on real music.

## Pass 2

| variant | settings | predicted |
|---|---|---|
| free | +4 -9 -9 +2 -2 +4 +1 -9 -2 +3 -4 -2 -5 | 2.73 -> 2.47 |
| bands 11-13 frozen | +4 -8 -9 +3 0 +4 +2 -8 -1 +3 -1 -1 0 | 2.73 -> 2.62 |
| bands 8, 11-13 frozen | +4 -8 -9 +4 0 +4 +2 -6 -1 +3 -1 -1 0 | 2.73 -> 2.64 |

The free pass 2 buys 0.26 dB, and 0.15 of that comes from cutting bands 11-13
by 3-5 steps to chase a treble region that (a) the mic has never been
calibrated in and (b) moved by 1.4 dB between the two flat baselines. The
other 0.1 dB is band 8 to the rail. Neither is worth a slider. **Pass 1 is
the result**; the frozen variant's +1 on band 2 and -1 / -2 on bands 7-9 are
within the method's one-step scatter.

## What is left, in order of size

1. Below 50 Hz and the 160 Hz dip: speaker limit and cancellation, no EQ.
2. The 2 kHz bump between bands 8 and 9: crossover region, no slider
   centre there, and it varies with head position anyway.
3. Treble tilt: needs a mic calibration before it is worth touching.
4. The last 5-6 dB of bass hump: nothing. Customize EQ disables the Bass
   tone control, so the sliders are all there is and bands 2-3 are at the
   rail.

# Three voicings to try by ear

Bundled as `mazda_neutral`, `mazda_warm`, `mazda_bass` in `careq/targets/`.
Fitted against both flat baseline sets pooled (18 recordings, 54 sweeps,
`results/session4/baseline_pooled_18.csv`), boosts capped at 4. Fit JSONs,
per-target plots and `comparison.png` in `results/session4/three/`.

| | target | settings, bands 1-13 | before -> after |
|---|---|---|---|
| A | neutral: flat mids, +3 dB bass shelf, -2 dB at 20 kHz | +4 -9 -9 +3 -1 +4 +3 -7 0 +4 -2 -2 -1 | 4.43 -> 2.52 |
| B | warm: +5 dB bass to 100 Hz, slope to -5 dB at 20 kHz | +4 -9 -9 +4 -3 +2 +1 -9 -2 +2 -5 -5 -5 | 4.21 -> 2.53 |
| C | bass-forward: +7 dB below 60 Hz, flat mids and treble | +4 -9 -9 +2 -4 +1 0 -9 -2 +2 -4 -4 -2 | 4.15 -> 2.66 |

Predicted in-car response relative to the 200 Hz-2 kHz mean (dB):

| | 40 | 63 | 80 | 100 | 160 | 250 | 500 | 1k | 2k | 4k | 8k | 12.5k | 16k |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | -1.7 | +3.4 | +6.4 | +4.2 | -1.7 | +1.4 | +2.2 | -1.2 | +2.6 | -0.9 | +0.1 | -0.5 | -2.3 |
| B | +0.5 | +5.4 | +8.3 | +6.2 | +0.6 | +1.6 | +1.7 | -2.2 | +3.1 | -2.4 | -1.6 | -2.4 | -4.1 |
| C | +1.4 | +6.2 | +9.1 | +6.7 | -0.4 | +1.3 | +1.8 | -2.1 | +3.5 | -1.2 | +0.5 | +0.6 | -0.7 |

What the measurements say about the three:

- Bands 2 and 3 sit at -9 for all of them. The 80 Hz hump is +14 dB
  before EQ, and even the +7 dB target is 7 dB below it. Bass amount is
  therefore set by bands 1, 4 and 5 and by how much the mids come down.
- Band 8 (1.6 kHz) is cut hard everywhere: the driver-seat average has a
  +4 dB bump there.
- A is the validated one (measured 2.73 dB on the earlier 9-file baseline).
  A differs from B and C mostly in treble tilt, which is the region the
  mic has not been calibrated in. Listening is the only test that settles
  treble, which is what these three are for.
- B and C need 43-47 steps of cut against A's 31; with the free level
  offset that is only a louder volume setting, not a quality difference.

# The 160 Hz dip is a source property (2026-09-14)

Checked across all 18 flat recordings, because it matters for whether door
treatment could help. Standard deviation of the 1/3-octave level between
positions:

| frequency | spread between 18 positions |
|---|---|
| 80 Hz | 2.29 dB |
| 100 Hz | 1.85 dB |
| 160 Hz | 0.77 dB |
| 200 Hz | 0.80 dB |
| 250 Hz | 0.71 dB |
| 500 Hz | 1.93 dB |
| 1.25 kHz | 3.37 dB |

Median across 40 Hz-16 kHz is 1.73 dB. The 160 to 315 Hz region is the most
position-independent part of the whole spectrum, at less than half the
typical spread, so the 11 dB drop from 125 Hz to 160 Hz is in what the
speakers radiate, not in where the microphone sat. It was previously
described here as a floor-bounce cancellation; that was wrong.

A broad source-side loss in this region is what an unsealed door does: the
inner skin's access holes let the woofer's back wave meet its front wave.
That makes it the one part of the response that door sealing could
plausibly change, and it is measurable before and after with nine
recordings each.

The 80 to 100 Hz hump, by contrast, varies by over 2 dB between positions,
so it is partly modal rather than pure cabin gain.
