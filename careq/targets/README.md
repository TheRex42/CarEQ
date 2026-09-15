# Target curves

All files: optional `#` comment lines, then `frequency,raw` (Hz, dB). Level is
arbitrary; `careq fit` normalises target and measurement to equal mean level
over 200 Hz-2 kHz. Any file in this format (or HouseCurve `.txt`, or a REW
export) can be passed to `careq fit --target FILE`.

| name | use |
|---|---|
| `harman_car` (default) | Harman-style in-car stand-in = HouseCurve Car B |
| `housecurve_car_a/b/c` | HouseCurve's three automobile curves (JBL / JBL variant / Crutchfield) |
| `housecurve_harman_room` | Toole/Harman-inspired home in-room slope, +2 to -8 dB |
| `bk_1974` | Classic B&K room curve |
| `autoeq_harman_in_room_2013`, `autoeq_harman_over_ear_2018` | AutoEq copies, ear-reference curves - reference only |
| `mazda_neutral` | The owner's 2021 Mazda 3 voicing A: flat mids, +3 dB bass shelf, -2 dB at 20 kHz (validated in the car 2026-09-13) |
| `mazda_warm` | voicing B: +5 dB bass to 100 Hz, Harman-style slope to -5 dB at 20 kHz |
| `mazda_bass` | voicing C: +7 dB below 60 Hz, flat mids and treble |

Sources: HouseCurve (https://housecurve.com/docs/tuning/target_curve),
AutoEq (MIT, https://github.com/jaakkopasanen/AutoEq).

## How much authority these car curves carry (checked 2026-09-14)

Less than the names suggest. HouseCurve's page introduces them only as
"some additional curves ... for automobiles. These curves have
significantly more bass which is common for automobile listening", with no
attribution. The curve files carry a single header line each, Car B's
reading "Variant of JBL curve". That is the entire published derivation.

Harman's listener-preference research, the body of work usually meant by
"the Harman curve", is on headphones and on loudspeakers in rooms. Their
automotive publications are largely measurement methodology, for example
Olive and Welti, "Validation of a Binaural Car Scanning Measurement System
for Subjective Evaluation of Automotive Audio Systems", AES 36th
International Conference on Automotive Audio, 2009. There is no in-car
target curve with the statistical backing the headphone targets have.

So none of `harman_car`, `housecurve_car_a/b/c` is a standard in the sense
that the Harman headphone target is. They are reasonable starting points
that agree on the broad shape, a bass lift of roughly 6 dB, flat mids and a
gentle treble roll-off, and they disagree on the details because nobody has
settled them.

The `mazda_*` curves are explicitly preferences, not derivations: see
`docs/targets.md`.
