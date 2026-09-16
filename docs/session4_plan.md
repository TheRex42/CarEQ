# Session 4 - tuning baseline and first EQ pass

The 13-band model is done (`results/session3/eq_model.json`) and does not
depend on where the mic was. The fit's other input, the baseline, does: it
must be measured where you listen, and averaged over a few spots so that
the fit corrects what is common to all of them and ignores single-spot
cancellations. The passenger-headrest baseline from session 3 shows -8 dB
notches at 160 Hz and 500 Hz that are almost certainly that kind of
single-spot effect; a fit against it wastes bands 4 and 6 at +9 on them.

Head unit: ALC off, session 3's volume number, Bass / Treble 0, fader and
balance centred, all 13 sliders at 0.

## Part 1: baseline (about 5 minutes)

Mic clipped to the **driver's** headrest, driver's seat empty, you in the
passenger seat. Five recordings, all sliders 0, moving the mic between
them by a few cm each time (headrest up / down, seat one notch forward /
back, clip left / right of centre). One recording per spot, recorder
running 3 s past the end.

```
tune_pos1.wav ... tune_pos5.wav
```

Then, back at the computer:

```
careq fit --measurement Recordings/Session4/tune_pos1.wav \
          --more Recordings/Session4/tune_pos2.wav ... tune_pos5.wav \
          --model results/session3/eq_model.json \
          --target TARGET --out results/session4/fit1.json --plot results/session4/fit1.png
```

`TARGET` is `harman_car` (HouseCurve Car B, the JBL-derived default),
`housecurve_car_a` or `housecurve_car_c`, or a `frequency,raw` file such
as `flat_bass_shelf.csv` (+3 dB below 80 Hz, flat mids, -2 dB at 20 kHz).
Re-running against another target needs no new recording. Add
`--max-boost 4` to keep boosts small (they cost head-unit headroom on loud
music; the free level offset means cuts do the same job).

## Part 2: verify and correct (about 5 minutes)

Set the 13 integers from `fit1.json` on the head unit. Record the same five
spots again as `after_pos1.wav ... after_pos5.wav`. Then:

```
careq fit --measurement Recordings/Session4/after_pos1.wav --more ... after_pos5.wav \
          --model results/session3/eq_model.json --target TARGET \
          --current results/session4/fit1.json --out results/session4/fit2.json --plot results/session4/fit2.png
```

The second fit reports how far the first pass landed from its prediction
(that is also the missing ALC-off superposition test), and the corrected
absolute settings. Set those. A third round is optional.

## Then listen

If the result sounds wrong in a way you can name (too much bass, harsh
treble), that is a target-curve problem, not a fit problem: edit the target
file and re-run part 1's fit from the same recordings.
