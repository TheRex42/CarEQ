# CarEq - tune a car head unit's graphic EQ with a calibrated microphone

Phase 0 (desktop Python). Measures the car + head-unit EQ with exponential
sine sweeps played from a USB stick and recorded, identifies the
shape and dB/step of every EQ band by system identification, and fits integer
band settings toward a target curve.

```
.venv/bin/careq gen --out stimulus              # sweep WAV for the USB stick + stimulus.json
.venv/bin/careq measure REC.wav --plot m.png    # one recording -> smoothed response CSV
.venv/bin/careq identify --manifest session/manifest.json --out eq_model.json --baseline-csv baseline.csv
.venv/bin/careq fit --measurement baseline.csv --model eq_model.json --target harman_car --plot fit.png
.venv/bin/careq simulate --out out/sim          # fake recordings of a known car for a dry run
.venv/bin/careq targets                         # bundled target curves
```

See `docs/method.md` for what every stage does and how the Mazda 3 target
was arrived at, and `docs/procedure.md` for the in-car recording procedure.

## Layout

| file | contents |
|---|---|
| `careq/signals.py` | Farina exponential sweep, inverse filter, stimulus assembly (silence + N repeats), pink noise, WAV export |
| `careq/measure.py` | sync by cross-correlation, clock-drift estimate from repeat spacing, deconvolution, IR windowing, fractional-octave smoothing, multi-position pooling, mic-cal |
| `careq/identify.py` | baseline + per-band measurements -> `eq_model.json` (basis curve per band, symmetry / linearity / level-offset checks, peaking-filter description) |
| `careq/fit.py` | target loading, weighted bounded least squares, integer rounding + coordinate descent, plot |
| `careq/simulate.py` | synthetic cabin / EQ / mic / recorder used by the tests and `careq simulate` |
| `careq/biquad.py` | RBJ biquads |
| `careq/targets/` | target curves (see its README) |
| `tests/` | synthetic end-to-end, sync robustness, rounding |

## How it works

**Stimulus.** 10 s exponential sweep 20 Hz-20 kHz at -12 dBFS, 48 kHz, 1 s
of silence before, 2 s after, repeated 3 times in one file (37 s). Repeats are
averaged, and their spacing gives the phone/head-unit clock offset to about
1 ppm without any assumption about the cabin.

**Measurement.** The recording is cross-correlated with the sweep to find
each onset (no clock sync needed), resampled to remove drift, deconvolved with
the inverse filter, and the linear impulse response is windowed (20 ms before
the peak, 500 ms after with a raised-cosine tail). Harmonic distortion lands
before the linear IR (Farina) and falls outside the window. The FFT of the
window is power-averaged over repeats and positions and smoothed to 1/3
octave on a log grid. A noise-only window of the same length gives a per-band
SNR estimate.

**Identification.** For band k at +9: `basis_k = 10 log10(P_k / P_baseline)`
with both spectra 1/3-octave smoothed first. The mic must not move between
baseline and band runs. Each run's broadband level difference to the
baseline (measured more than 1.5 octaves from the band's peak) is
subtracted, since one band cannot move the whole spectrum; above 0.75 dB it
is also flagged (`--no-level-correct` keeps it). Optional runs at -9 / +3 produce symmetry and
linearity checks. The per-step curve is `basis_k / 9`; a peaking-filter fit
of each basis is reported for sanity but not used.

**Fit.** Target and baseline are normalised to equal mean level over
200 Hz-2 kHz. Weighted least squares with a free level offset and bounds +-9
(`scipy.optimize.lsq_linear`), weights 1.0 over 60 Hz-12 kHz tapering to
0.05 at 30 Hz / 16 kHz, then rounding and +-1 integer coordinate descent.
Each band's effect is `gain_scale * per_step * steps`, with cuts further
scaled by `cut_factor`: with ALC off the Mazda delivers about 95 % of the
single-band gain when adjacent bands are set together and cuts 7 %
shallower than it boosts. `--max-boost` caps positive steps separately,
because boosts spend the head unit's digital headroom (with ALC on, which
adds ~6 dB, two bands at +9 hit its limiter). Output: 13 integers,
predicted residual, before / predicted / target plot.

**Iterate.** The linear model is good to about 5 % with ALC off and the
2-4 kHz region varies +-1 dB between recordings, so one pass is approximate. Set the
sliders, measure again, and run `careq fit --current fit.json` (or
`--current "0 0 +3 ..."`) on the new recording: the fit then returns the
corrected absolute settings and the change from the current ones.

## Status

- 30 tests pass (`.venv/bin/python -m pytest`, ~1 min). On the synthetic
  car (measured-like: Q~2 bands, 0.93 cut factor, soft gain limiter),
  identified bases match the true filters within 0.5 dB, the cut factor
  within 0.03, drift to <2 ppm; the first fit pass predicts the re-simulated
  result within 1 dB rms, the second within 0.3 dB and the third within
  0.1 dB (each pass refits from the measured result with `--current`).
- Real recordings: three identification sessions on a 2021 Mazda 3
  (2026-09-13) gave all 13 bands; the combined model is
  `results/session3/eq_model.json` (see `docs/session3_results.md`; the
  mic is discussed in `docs/microphone.md`). Not yet validated against REW;
  no tuning pass yet.
- Band labels: 40, 63, 100, 160, 250, 500, 1k, 1.6k, 2.5k, 4k, 6.3k, 10k,
  16k Hz, from the measured centres. Labels only; every shape is measured.

## Reuse and attribution

- Targets from HouseCurve (https://housecurve.com/docs/tuning/target_curve)
  and AutoEq (MIT, Jaakko Pasanen, https://github.com/jaakkopasanen/AutoEq).
  AutoEq's fixed-band optimiser fits ideal peaking filters with SLSQP; since
  our bands are measured curves the problem is linear, so a bounded linear
  least squares is used instead. AutoEq's target normalisation and
  smoothing ideas are borrowed.
- Sweep / inverse filter after Farina (2000), "Simultaneous measurement of
  impulse response and distortion with a swept-sine technique".
