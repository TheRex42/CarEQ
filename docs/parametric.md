# What the fixed 13-band EQ costs (2026-09-14)

The head unit gives 13 bands at fixed centres, fixed shapes, integer steps.
A parametric EQ would give free centre, Q and gain. How much is that worth?

Same baseline (`results/session4/baseline_pooled_18.csv`), same target
(`mazda_neutral`), same weighting and free level offset. Only the filter set
changes. Reproduce with `results/parametric/compare_parametric.py`.

| configuration | weighted RMS |
|---|---|
| no EQ | 4.43 dB |
| 13 fixed bands, integer, boosts capped at +4 (what is loaded) | 2.52 dB |
| 13 fixed bands, integer, boosts to +9 | 2.37 dB |
| 13 fixed bands, continuous gains | 2.36 dB |
| 5 parametric, free centre/Q/gain | 2.70 dB |
| 8 parametric | 2.05 dB |
| 13 parametric, Q capped at 3 | 1.48 dB |
| 13 parametric, Q capped at 10 | 1.78 dB |
| 20 parametric | 0.64 dB |

## Reading it

**Integer steps cost nothing.** 2.37 against 2.36 for continuous gains. The
coordinate descent recovers essentially all of the rounding loss.

**The boost cap costs 0.15 dB**, which buys headroom and, per
`docs/distortion.md`, keeps band 1 out of the region where the speakers are
already at 2 % THD. Cheap.

**Fixed shapes cost about 0.9 dB.** Thirteen free filters reach 1.48 dB
against 2.37 for thirteen fixed ones. Note that the Q<=10 run scored *worse*
than the Q<=3 run (1.78 vs 1.48): with only two restarts the wider search
lands in a poorer local minimum, and several of its filters degenerate to
Q 0.3 at the gain rail, being used as makeshift shelves. Take 1.48 dB as the
fair figure for 13 free filters.

**The loss is in the placement, not the bandwidth.** Capping parametric Q at
3 is close to the graphic EQ's measured Q of about 2, yet it still gains
0.9 dB purely from being able to choose where the filters sit. Fixed centres
are the real constraint; fixed Q is almost free.

**About 8 well-placed filters equal 13 fixed ones** (2.05 against 2.37).

## Where the difference lives

| region | 13 fixed | 13 parametric | gain |
|---|---|---|---|
| 30-60 Hz | 3.65 | 2.47 | +1.18 |
| 60-120 Hz | 2.52 | 1.04 | +1.49 |
| 120-250 Hz | 2.76 | 3.40 | -0.64 |
| 250-500 Hz | 2.17 | 1.20 | +0.97 |
| 500 Hz-1 kHz | 0.92 | 0.70 | +0.22 |
| 1-2 kHz | 1.91 | 0.51 | +1.39 |
| 2-4 kHz | 1.83 | 0.20 | +1.63 |
| 4-8 kHz | 1.02 | 0.48 | +0.54 |
| 8-16 kHz | 1.04 | 0.88 | +0.16 |

The biggest wins are 1-4 kHz, which is the feature sitting in the gap
between bands 8 and 9 where the graphic EQ has no centre, and 60-120 Hz,
where the hump wants a wider and deeper filter than a Q 2 band at -9 can
provide.

## The caveat that matters

Some of the parametric advantage is not real. The 13-filter solution places
filters at Q 10 and Q 5.9 around 365 and 420 Hz, correcting features
narrower than the measurement's own reliability: position-to-position
scatter is 2.2 dB over 500 Hz-2 kHz, and a Q 10 notch is far narrower than
anything that survives moving your head. The 20-filter result at 0.64 dB is
almost certainly fitting ripple that changes between seats.

So the honest figure for what a parametric EQ would buy in the car is
somewhere below the 0.9 dB the arithmetic shows, concentrated in one real
feature near 2 kHz and in the bass hump. It is not nothing, and it is also
not the difference between good and bad.
