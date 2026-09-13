# careq - Mazda 3 head-unit EQ tuner (Phase 0: desktop Python)

Goal: tune a 2021 Mazda 3's 13-band graphic EQ (integer steps -9..+9, fixed
frequencies, unknown filter shapes) toward a target curve using an Android
phone mic. Sweeps go to the car on a USB stick; the phone records; this
package does everything else. Bases are MEASURED per band, never assumed.

## Working here

- Python env: `.venv/` (numpy, scipy, soundfile, matplotlib, pytest). Use
  `.venv/bin/python` and `.venv/bin/careq`; system python has none of it.
- Tests: `.venv/bin/python -m pytest` (30 tests, ~1 min). Keep them green.
- Recordings from the car go in `recordings/<session>/` with a
  `manifest.json` (format in `docs/procedure.md`). `*.wav`, `*.npz` and
  `recordings/` are gitignored; results (json/csv/png) may be committed.
- Scratch work goes in the session scratchpad, not the repo.
- Commit with the user's name; the user asks before commits are expected.

## Pipeline (see docs/method.md for the full write-up, README.md for a summary)

| step | command | in -> out |
|---|---|---|
| stimulus | `careq gen --out stimulus` | `careq_sweep_48k_10s_x3.wav` (10 s exp sweep 20 Hz-20 kHz, -12 dBFS, x3 repeats, 37 s) + `stimulus.json` |
| measure | `careq measure REC.wav --plot m.png --save-ir ir.wav` | recording -> 1/3-oct response CSV, per-sweep diagnostics |
| identify | `careq identify --manifest recordings/S/manifest.json --out eq_model.json --baseline-csv baseline.csv --plot bases.png` | baseline + 13 band recordings -> basis curve and dB/step per band |
| fit | `careq fit --measurement baseline.csv --model eq_model.json --target harman_car --plot fit.png` | -> 13 integers, predicted residual, plot |
| iterate | `careq fit --measurement after.wav --current fit.json --model ... --target ...` | measurement made WITH the sliders set -> corrected absolute settings + change |
| dry run | `careq simulate --out out/sim` | synthetic car recordings (NOT a Mazda; for testing only) |

Key design facts (do not re-derive):
- Drift (phone vs head-unit clock) comes from the spacing of the 3 sweep
  repeats (~1 ppm). Single-sweep recordings get NO drift estimate (IR-based
  estimators are biased 10-40 ppm by the cabin; tried and removed). Drift
  barely affects 1/3-oct magnitude anyway (<0.5 dB at 100 ppm).
- Basis_k = 10log10(smooth(P_k) / smooth(P_baseline)), power-smoothed first;
  this is exactly what the fit adds to the smoothed baseline.
- identify subtracts each run's broadband offset vs baseline (measured >1.5
  oct from the peak) and flags it above 0.75 dB (volume / gain / mic moved).
- Fit: bounded weighted LSQ with free level offset, weights 1.0 in
  60 Hz-12 kHz tapering to 0.05 at 30 Hz / 16 kHz, then integer coordinate
  descent. Effective steps = 0.95 * steps (cuts x0.93 more). With ALC ON
  the head unit adds ~6 dB and its limiter clips big boosts (session 2's
  "superposition failure" was that); with ALC OFF adjacent bands add to
  within ~5 %. `--max-boost` caps boosts separately (headroom). One pass is
  still approximate (2-4 kHz varies +-1 dB between recordings: driver
  crossover region); always measure with the sliders set and refit with
  `--current`. Judge results against the continuous solution / what the
  bands can physically reach, not an absolute % reduction.
- Band labels 40, 63, 100, 160, 250, 500, 1k, 1.6k, 2.5k, 4k, 6.3k, 10k,
  16k Hz are MEASURED centres (sessions 1-2). Labels only; shapes measured.
- Real-car facts (docs/session3_results.md): Q ~2, 0.85-1.0 dB/step, cuts
  mirror boosts at 93 %, level wanders ~1 dB between files during a session
  (interleave baselines; identify subtracts each run's far-field offset),
  road noise is irrelevant above 31 Hz. ALC must be OFF and the volume
  number fixed (session 3's). Combined model: `results/session3/eq_model.json`.
  `simulate.py`'s `HeadUnitEq.mazda_like` carries these numbers plus a soft
  gain limiter matching the ALC-off pair result.
- Mic: HyperX SoloCast. No full-band measurement exists (docs/microphone.md);
  no `--mic-cal` applied, so treat fit results above 4 kHz with suspicion.
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
5. Recordings are a HyperX SoloCast clipped to the headrest of the seat NOT
   being sat in. Let the recorder run 3 s past the end. `load_wav` takes
   channel 0 and resamples 44.1k -> 48k.
6. Session docs: `docs/session2_plan.md`, `docs/session2_results.md`,
   `docs/session3_plan.md`, `docs/session3_results.md`, `docs/microphone.md`.
   Results that may be committed live in `results/<session>/`.

## Roadmap

Phase 0 (this): validated on real recordings 2026-09-13 (identification
done); still to do: REW cross-check, mic calibration, first tuning pass
with iterate. Phase 1: multi-position tuning, documented procedure. Phase 2: Android app (Kotlin,
Oboe). Phase 3: live pink-noise RTA (`careq gen --pink 60` already writes
the noise file).

## References

AutoEq (MIT; targets + fitting ideas), HouseCurve car curves
(`careq/targets/README.md`), Farina 2000 sweep method. REW is validation
only. Open Sound Meter is the Phase 3 RTA reference.
