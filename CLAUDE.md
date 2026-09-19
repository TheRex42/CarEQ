# careq - Mazda 3 head-unit EQ tuner (desktop Python)

Goal: tune one 2021 Mazda 3's 13-band graphic EQ (integer steps -9..+9,
fixed frequencies, unknown filter shapes) toward a target curve by
measuring it. Sweeps go to the car on a USB stick, a USB microphone plugged
into an Android phone records, this package does everything else. Bases are
MEASURED per band, never assumed. (There is no laptop in this setup; earlier
drafts wrongly assumed one.)

**This is a DIY tuning tool for a specific car, not a general app.** The
original plan had an Android app as phase 2; see the roadmap for why that
was reconsidered. The signal processing generalises for free, the head-unit
quirks, microphone calibration and user technique do not.

## Working here

- Python env: `.venv/` (numpy, scipy, soundfile, matplotlib, pytest). Use
  `.venv/bin/python` and `.venv/bin/careq`; system python has none of it.
- Tests: `.venv/bin/python -m pytest` (34 tests, ~1 min). Keep them green.
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
| rta | `careq rta REC.wav --compare sweep.csv --out rta.csv` | continuous pink-noise recording (mic may MOVE during the take) -> same 1/3-oct CSV; magnitude only, see docs/rta.md |
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
  descent. Weights sit on a log-uniform grid, i.e. equal weight per octave;
  every fit ALSO reports the same error weighted by auditory bandwidth
  (`erb_density(f) = f/(f+228.8)`), which is always lower because the big
  errors are in the bass. `--erb-weight` optimises on it instead; on this
  car that moves 8 bands by one step and is inside the method's scatter.
  Effective steps = 0.95 * steps (cuts x0.93 more). With ALC ON
  the head unit adds ~6 dB and its limiter clips big boosts (session 2's
  "superposition failure" was that); with ALC OFF adjacent bands add to
  within ~5 %. `--max-boost` caps boosts separately (headroom). One pass is
  still approximate (2-4 kHz varies +-1 dB between recordings: driver
  crossover region); always measure with the sliders set and refit with
  `--current`. Judge results against the continuous solution / what the
  bands can physically reach, not an absolute % reduction.
- Band labels 40, 63, 100, 160, 250, 500, 1k, 1.6k, 2.5k, 4k, 6.3k, 10k,
  16k Hz are MEASURED centres (sessions 1-2). Labels only; shapes measured.
- The car COMPRESSES above ~volume 40: +9 on band 1 delivers 1.9 dB less at
  35-40 Hz at volume 50 than at 30, tapering to nothing by 80 Hz, with THD at
  40 Hz going 1.8 % -> 7.5 %. Woofer excursion, not the chain. `simulate.py`'s
  `woofer_saturation` models it and a test asserts the two-level
  `careq measure --compare` check catches it (`docs/level.md`).
- The band model is mic-INDEPENDENT, now measured not just argued: bands 5, 9,
  13 re-identified through a different capsule, converter and polar pattern
  agree to 0.41-0.52 dB rms (`docs/session5_results.md`).
- Real-car facts (docs/session3_results.md): Q ~2, 0.85-1.0 dB/step, cuts
  mirror boosts at 93 %, level wanders ~1 dB between files during a session
  (interleave baselines; identify subtracts each run's far-field offset),
  road noise is irrelevant above 31 Hz. ALC must be OFF and the volume
  number fixed at Mazda volume 30 (settled 2026-09-17: volume 50 compresses
  band 1 by 1.9 dB at 35-40 Hz and trebles distortion; volume 30 reproduces
  the volume-25 model within 0.3 dB). THE VOLUME NUMBER IS THE REFERENCE; no
  trustworthy SPL figure exists (the only meter available runs on the phone's
  built-in mic, which is +13 dB hot up top). Do NOT pick a volume from a pink
  SPL reading: pink spreads energy across the band while a sweep puts it all
  at one frequency, so the same reading is ~20 dB more demand on the woofer
  during a sweep. Volume 50 is ~20 dB above 25 and tripled distortion to
  7.5 % at 40 Hz (`docs/level.md`). Combined model: `results/session3/eq_model.json`.
  `simulate.py`'s `HeadUnitEq.mazda_like` carries these numbers plus a soft
  gain limiter matching the ALC-off pair result.
- Mic, from session 5 on: Dayton iMM-6 (serial 99-64551) through an Apple
  USB-C dongle into the phone. Calibration `Calibration/99-64551.txt`, sign
  checked; ALWAYS pass `--mic-cal Calibration/99-64551.txt` to `rta` and
  `measure` for a baseline, and to `fit` ONLY when fitting a WAV directly:
  `fit --mic-cal` also applies to a CSV, and rta/measure CSVs are already
  calibrated (double subtraction). Identification needs no mic cal (ratio). The
  SoloCast used for sessions 1-4 is retired; its baselines are superseded.
- Default target `harman_car` = HouseCurve "Car B" (JBL-derived), a
  placeholder. The owner's measured by-ear preference is `mazda_by_ear` (+4 dB
  shelf, flat mids, -3.25 dB/oct above ~4.2 kHz); use it. Research targets
  `olive_welti_car`, `clark_car`, `binelli_farina_car`, `olive2013_room_*` are
  digitised from Toole 2015 (~+-1 dB). `mazda_neutral/warm/bass` are
  superseded (Neutral's treble was too flat); see `docs/targets.md`.

## Processing a new session: checklist

1. Write the manifest; run `careq identify`. Read the per-sweep lines:
   `corr-quality` in the thousands, 3 sweeps found per file, drift the SAME
   for every file, SNR at 100/1k/10k well above 20 dB, no `CLIPPING!`.
2. Band table: one clear peak per band near its label, similar dB/step
   (expect ~1 dB/step), `fit-err` small. Look at `bases.png`.
3. Notes: `level_offset_warning_bands`, `symmetry_ok`, `linearity_ok`.
4. Identification: mic clipped to the headrest of the seat NOT being sat
   in, not moved between baseline and band runs. Only 4 bands are actually
   needed (1, 5, 9, 13 plus a baseline lands within 1 step of the full
   13-band model; see docs/method.md) once a full model for the head unit
   exists. Tuning baseline (from session 6): hand-held moving-mic PINK
   noise from the occupied driver's seat, three takes, `careq rta move*.wav
   --mic-cal ...`. Sessions 1-4 used 9 clamped sweep positions instead; that
   works but needs the mic still, which the iMM-6 makes awkward.
5. ALC OFF, fixed volume number, Bass/Treble unavailable (Customize EQ
   replaces them). Let the recorder run 3 s past the end. `load_wav` takes
   channel 0 and resamples 44.1k -> 48k.
6. Docs: `docs/method.md` (what every stage does + how the target was
   reached), `docs/session{2,3,4,5}_results.md`, `docs/session6_results.md`
   (latest), `docs/level.md` (volume, compression), `docs/microphone.md`,
   `docs/distortion.md`, `docs/targets.md`, `docs/rta.md`,
   `docs/weighting.md`, `docs/parametric.md`, `docs/listening.md`. Older plan
   files and `session2_results` / `session5_results` carry OVERTURNED banners
   where they were wrong; read the banner. Committable results live in
   `results/<session>/`.

## Roadmap

**Done (2026-09-13/14).** All 13 bands identified and cross-checked over
three sessions. Multi-position tuning baseline, fit, and a measured
verification in the car: predicted 2.64 dB weighted error, measured 2.73,
from 4.54 flat, with pass-1 settings `+4 -9 -9 +3 0 +4 +3 -6 +1 +4 -1 -1 0`.
Three voicings bundled and listened to (band 1 and Neutral's bands 11-13
were then set by ear; those overrides were dropped 2026-09-18). Harmonic
distortion measured. Written up in
`docs/method.md`.

**Done (2026-09-17).** iMM-6 in hand and checked. Band model re-confirmed
through it. Measurement volume settled at 30 (50 compresses).

**Done (2026-09-18), session 6.** Pink agrees with sweep in the car (0.31 dB
rms). Calibrated moving-mic baseline, all three voicings refitted with NO
by-ear overrides (the old mic read 4-6 dB hot above 6 kHz, so the by-ear
treble cuts were wrong-way), boosts capped at +4. Neutral
`+4 -9 -9 +1 -2 +4 -2 -7 0 +4 -2 +3 +4` verified: predicted 1.93, measured
1.81 dB from 4.30 flat; pass 2 would gain 0.16 dB, so stopped. Write-up
`docs/session6_results.md`.

**Done (2026-09-18), targets revised after listening.** Neutral was too
bright: its own target (treble -2 dB at 20 kHz) was the fault, not the
method. Every published target with a falling treble reproduces the owner's
by-ear treble. Research in `docs/targets.md` ("Research round 2"; Toole JAES
2015 Figs 14-15: Olive 2013 preferred room curves, three in-car targets).
Final profiles in `results/final/`, boosts capped at +6: **By ear**
(`mazda_by_ear`) `+6 -9 -9 +3 -1 +6 -2 -6 0 +5 -2 0 +1`, **Harman in-car**
(`olive_welti_car`), **Trained listener** (`olive2013_room_trained`). All
predicted, not yet measured.

**Scope, reconsidered.** The signal processing was never the hard part; it
worked on the first real recording and never gave a wrong answer. All three
wrong conclusions along the way came from a head-unit setting nobody knew
was on (ALC, silently adding 6 dB), an unmeasured microphone, and
measurement discipline. A general app must solve those three for arbitrary
cars, phones and users, while the maths ports for free. So this stays a
tool for one car, used by someone willing to follow a procedure.

If it were ever generalised, the split is: identification is a ratio
through one microphone, hence microphone-independent and shareable per
head-unit model; the baseline is one cabin, one seat, one listener, and
never shareable. Unlike headphones, the unshareable half does most of the
work. The one feature that would make it robust is an automatic
level-linearity check (play the sweep at two levels, compare normalised
responses) to catch ALC-class settings, which fail silently.

### Next, in rough order

1. **Verify By ear** in the car: set it, three moving pink takes (recorder
   started 3 s early), `careq rta ... --mic-cal`, then
   `careq fit --current ... --target mazda_by_ear --max-boost 6`.
2. **REW cross-check.** Still the only external validation never done.
   `careq measure --save-ir ir.wav` writes the averaged impulse response
   for import; magnitudes should agree within ~1 dB at 1/3 octave.
   `fix_sweep.wav` from session 6 is the input.
3. **Subwoofer** for the low bass, which no EQ can reach: 25-45 Hz is
   ~11 dB under target and the doors are 10 dB down by 48 Hz. Cross at
   50-60 Hz, NOT the usual 80, which would feed the +13.8 dB hump at 83 Hz.
   Non-Bose gen4 has no preouts: tap speaker level under the passenger
   seat. Retune afterwards; set level, crossover and phase by measurement.
   The taps are POST-EQ, so bands 1-3 will drive the sub too: re-identify
   bands 1-3 with sweeps and take a new moving-mic baseline after install.
   Simulated (2026-09-18, ideal sub at 60 Hz): the lower-mid scoop that
   bass-heavy targets force (bands 5, 7) disappears and error falls to
   ~1.45 dB; ResoNix's 1.6-2.5 kHz cuts do not (its own dip + the car's
   1.6-2 kHz bump). See `docs/targets.md`.
4. **Door sealing** as a separate, measurable experiment. The 160 Hz dip
   is a source property (0.77 dB spread across 18 positions vs 1.73
   median), but the cause is NOT established: an unsealed door's acoustic
   short circuit and a deliberate notch in Mazda's own tuning fit the data
   equally well, and sealing only helps the first. Reliable benefits are
   rattle and road noise. Risk: it may raise the 80-125 Hz hump, where
   bands 2-3 are already pinned at -9. Measure 9 before, 9 after.

### Known dead ends (do not retry)

- Bass/Treble tone controls: disabled by Customize EQ.
- A second fit pass ON THE SOLOCAST BASELINE: predicted gain 0.26 dB, mostly
  by cutting treble the uncalibrated mic could not vouch for. With the
  calibrated iMM-6 that objection lapses; iterating is legitimate again.
- Measuring at volume 50, or choosing a volume from a pink SPL reading.
- The SoloCast as a reference, or re-identifying the band model for a new mic.
- The phone's internal mic as a reference: +13 dB hot at 10-16 kHz.
- IR-based clock-drift estimators: biased 10-40 ppm by the cabin.

## References

AutoEq (MIT; targets + fitting ideas), HouseCurve car curves
(`careq/targets/README.md`), Farina 2000 sweep method. REW is validation
only (item 2 above).
