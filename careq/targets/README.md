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

Sources: HouseCurve (https://housecurve.com/docs/tuning/target_curve),
AutoEq (MIT, https://github.com/jaakkopasanen/AutoEq).
