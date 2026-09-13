# careq - Mazda 3 head-unit EQ tuner (Phase 0: desktop Python)

Goal: tune a 2021 Mazda 3's 13-band graphic EQ (integer steps -9..+9, fixed
frequencies, unknown filter shapes) toward a target curve using an Android
phone mic. Sweeps go to the car on a USB stick; the phone records; this
package does everything else. Bases are MEASURED per band, never assumed.

## Working here

- Python env: `.venv/` (numpy, scipy, soundfile, matplotlib, pytest). Use
  `.venv/bin/python` and `.venv/bin/careq`; system python has none of it.
- Tests: `.venv/bin/python -m pytest` (29 tests, ~1 min). Keep them green.
- Recordings from the car go in `recordings/<session>/` with a
  `manifest.json` (format in `docs/procedure.md`). `*.wav`, `*.npz` and
  `recordings/` are gitignored; results (json/csv/png) may be committed.
- Scratch work goes in the session scratchpad, not the repo.
- Commit with the user's name; the user asks before commits are expected.

## Pipeline (see README.md for detail)

| step | command | in -> out |
|---|---|---|
| stimulus | `careq gen --out stimulus` | `careq_sweep_48k_10s_x3.wav` (10 s exp sweep 20 Hz-20 kHz, -12 dBFS, x3 repeats, 37 s) + `stimulus.json` |
| measure | `careq measure REC.wav --plot m.png --save-ir ir.wav` | recording -> 1/3-oct response CSV, per-sweep diagnostics |
| identify | `careq identify --manifest recordings/S/manifest.json --out eq_model.json --baseline-csv baseline.csv --plot bases.png` | baseline + 13 band recordings -> basis curve and dB/step per band |
| fit | `careq fit --measurement baseline.csv --model eq_model.json --target harman_car --plot fit.png` | -> 13 integers, predicted residual, plot |
| dry run | `careq simulate --out out/sim` | synthetic car recordings (NOT a Mazda; for testing only) |

Key design facts (do not re-derive):
- Drift (phone vs head-unit clock) comes from the spacing of the 3 sweep
  repeats (~1 ppm). Single-sweep recordings get NO drift estimate (IR-based
  estimators are biased 10-40 ppm by the cabin; tried and removed). Drift
  barely affects 1/3-oct magnitude anyway (<0.5 dB at 100 ppm).
- Basis_k = 10log10(smooth(P_k) / smooth(P_baseline)), power-smoothed first;
  this is exactly what the fit adds to the smoothed baseline.
- identify flags a band whose median level differs >0.75 dB from baseline:
  recorder gain changed (AGC) or the phone moved. Such bases are untrusted.
- Fit: bounded weighted LSQ with free level offset, weights 1.0 in
  60 Hz-12 kHz tapering to 0.05 at 30 Hz / 16 kHz, then integer coordinate
  descent. Judge results against the continuous solution / what the bands
  can physically reach, not an absolute % reduction.
- Band labels 40, 63, 100, 160, 250, 400, 630, 1k, 1.6k, 2.5k, 4k, 6.3k,
  10k Hz are a GUESS (in `identify.py`); fix from a photo of the EQ screen.
  Labels only; shapes are measured.
- Default target `harman_car` = HouseCurve "Car B" (JBL-derived), a
  placeholder. The owner prefers flat mids + slight bass shelf; any
  `frequency,raw` CSV works with `--target`.

## Processing a new session: checklist

1. Write the manifest; run `careq identify`. Read the per-sweep lines:
   `corr-quality` in the thousands, 3 sweeps found per file, drift the SAME
   for every file, SNR at 100/1k/10k well above 20 dB, no `CLIPPING!`.
2. Band table: one clear peak per band near its label, similar dB/step
   (expect ~1 dB/step), `fit-err` small. Look at `bases.png`.
3. Notes: `level_offset_warning_bands`, `symmetry_ok`, `linearity_ok`.
4. Identification uses an EMPTY seat, phone on a holder, phone not moved.
   Tuning baseline uses an OCCUPIED seat, hand-held, 5-7 positions, pooled
   with `careq fit --measurement p1.wav --more p2.wav ...`.
5. Real recordings have never been processed yet: expect surprises
   (recorder AGC, level mismatch, sample rate, stereo files, extra silence).
   `load_wav` takes channel 0 of stereo files and resamples 44.1k -> 48k.

## Roadmap

Phase 0 (this): validate on real recordings, cross-check one measurement
against REW (import `--save-ir` WAV). Phase 1: multi-position tuning,
symmetry/linearity, documented procedure. Phase 2: Android app (Kotlin,
Oboe). Phase 3: live pink-noise RTA (`careq gen --pink 60` already writes
the noise file).

## References

AutoEq (MIT; targets + fitting ideas), HouseCurve car curves
(`careq/targets/README.md`), Farina 2000 sweep method. REW is validation
only. Open Sound Meter is the Phase 3 RTA reference.
