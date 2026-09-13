# Session 3 results (2026-09-13, 15:22-15:42, ALC off)

13 files in `Recordings/Session3/`, HyperX SoloCast clipped over the
passenger headrest, same volume number as session 2, ALC off. All files
clean: 3 sweeps each, drift +11.3 to +13.2 ppm, SNR 44-63 dB, no clipping,
sweep-to-sweep repeatability 0.04-0.09 dB. Correlation quality is lower than
before (300-1000) because the level is 6 dB lower; see below.

## ALC was adding 6 dB, and it was the cause of the "superposition failure"

With ALC off the whole session sits 5.8 dB below session 2 and matches
session 2's last file (`baseline_final_level_control.wav`) within 0.1 dB, so
that file was the ALC-off state. ALC on, car parked, adds about 6 dB of gain
before the head unit's DSP. That gain eats the digital headroom the EQ
boosts need: the sweep is at -12 dBFS, ALC lifts it to about -6, and a +9
boost then runs into the unit's output limiter. Two adjacent bands at +9
were being clipped to a plateau. With ALC off:

| | session 2 (ALC on) | session 3 (ALC off) |
|---|---|---|
| bands 9+10 at +9, peak | 9.8 dB | 10.6 / 11.0 dB (two files) |
| sum of the single-band curves | 11.7 dB | 11.2 dB |
| peak / sum | 0.84 | 0.95 / 1.02 |
| LSQ decomposition | 0.85 x b9 + 0.64 x b10 | 0.96 x b9 + 0.81 x b10 and 1.07 x b9 + 0.77 x b10 |

Superposition holds to within about 5 % at the peak. Band 10's coefficient
is still low (0.8) in both files while band 9's is full, which is the same
2.5-4 kHz region that varies between files everywhere else in this data
(see band 9 below), so it is as likely mic placement as head-unit
behaviour. The four-band moderate combo from session 2 (84-92 %) was also
ALC-on and is no longer evidence of anything.

Consequences, all applied in the code:

- `careq fit` gain scale default is now 0.95 (was 0.87). The iterate pass
  remains the way to land exactly.
- Boosts cost headroom on real material exactly as they did on the sweep.
  `careq fit --max-boost N` caps positive steps separately so the fit
  prefers cuts where it has the choice; the free level offset means it
  loses nothing by doing so.
- ALC must stay off for every measurement, and the same volume number must
  be used. Session 3's number, with ALC off, is the reference from here on.

Single-band curves were not much affected by ALC (bands 9 and 10 agree
between the two sessions within 0.2 dB at the peak), so session 2's bands
1, 2, 4, 6, 8, 12, 13 stay in the model.

## Session 1's odd bands were low

| band | session 1 | session 3 |
|---|---|---|
| 3 | +8.2 dB, Q 2.2 | +7.8 dB, Q 2.2 at 102 Hz |
| 5 | +7.5 dB, Q 2.1 | +8.1 dB, Q 2.2 at 242 Hz |
| 7 | +6.5 dB, Q 1.8 | +8.4 dB, Q 2.2 at 996 Hz |
| 11 | +6.4 dB, Q 2.8 at 5.6 kHz | +8.5 dB, Q 1.9 at 6.1 kHz |

Session 1 had one baseline, a moving mic and ALC on. Bands 7 and 11 were
2 dB low and band 11 sat at the wrong frequency. All four session 1 bases
are replaced.

## Band 9 and the 2-4 kHz region

Band 9 measured Q 2.6 in session 2 and Q 1.9 in session 3 with the same
peak height; the difference is 1 dB rms within an octave of the peak. Both
files repeat internally to 0.06 dB, so this is between-file variation, and
every between-file disagreement in all three sessions concentrates in
1.5-4 kHz. That is where a door woofer hands over to a tweeter, and the
interference between two drivers is what changes most with a few
millimetres of mic movement. The model uses the mean of the two sessions for
bands 9 and 10 and treats +-1 dB there as the noise floor of this method.

## Level correction

Session 3's baselines did not droop monotonically: baseline_2 sat 0.8 dB
below the other two and recovered, so time interpolation between baselines
left +0.3 to +1.3 dB broadband offsets on the three bands recorded around
it. `careq identify` now subtracts each run's broadband offset, measured
more than 1.5 octaves from the band's peak (one band cannot move the whole
spectrum; the fit has its own level offset and must not see one in a basis).
The old warning threshold still prints when the offset exceeds 0.75 dB.
The combined model was built the same way. `--no-level-correct` restores
the raw behaviour.

## Combined model (`results/session3/eq_model.json`)

| band | centre | Q | dB/step | source |
|---|---|---|---|---|
| 1 | 37 Hz | 1.6 | 0.85 | s2 |
| 2 | 62 Hz | 2.1 | 0.94 | s2 |
| 3 | 102 Hz | 2.2 | 0.90 | s3 |
| 4 | 160 Hz | 2.6 | 0.92 | s2 |
| 5 | 251 Hz | 2.2 | 0.95 | s3 |
| 6 | 489 Hz | 2.1 | 0.84 | s2 |
| 7 | 987 Hz | 2.2 | 0.94 | s3 |
| 8 | 1.57 kHz | 1.9 | 0.85 | s2 |
| 9 | 2.56 kHz | 2.3 | 0.92 | mean s2, s3 |
| 10 | 3.94 kHz | 2.2 | 0.98 | mean s2, s3 |
| 11 | 6.34 kHz | 1.9 | 0.94 | s3 |
| 12 | 10.1 kHz | 1.5 | 0.97 | s2 |
| 13 | 16.9 kHz | 0.7 | 0.99 | s2 |

Peaking-fit errors 0.22-0.79 dB; band 3 is the worst, its file having been
recorded next to the odd baseline. Cut factor 0.93 from session 2 (bands 4
and 10 at -9). Every centre is within 5 % of its label except band 1 (37 vs
40 Hz, at the edge of the smoothing) and band 13 (a broad top-octave shelf
whose "centre" is not well defined).

The synthetic car's limiter (knee 7 dB, cap 10.5 dB) gives a pair ratio of
0.95, which now matches the ALC-off car rather than being milder than it.

## Still open

- No cut measurement with ALC off, and no separated-band combo with ALC
  off. Both can be folded into the first tuning session (set the fitted
  values, measure, compare with the prediction: that is the combo test).
- Microphone response: see `docs/microphone.md`.
