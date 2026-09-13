# Session 3 - ALC check and odd-band redo

Sessions 1 and 2 were recorded with the head unit's ALC (automatic level
control) on. ALC is a speed-dependent volume adjustment and should be inert
with the car stationary, and nothing in the data shows level-dependent gain
(three sweeps per file identical to 0.03 dB, +5 = 5/9 of +9 within 0.2 dB,
a 5.8 dB volume step with a flat 0.66 dB rms shape). But "should be" is
not "is", so this session checks it directly while completing the model.

Set-up exactly as session 2 (mic clipped to the passenger headrest, same
volume number, recorder running 3 s past the end), with **ALC off**.

| # | file | setting | purpose |
|---|---|---|---|
| 1 | `baseline_1.wav` | all 0 | |
| 2 | `band10_p9.wav` | band 10 = +9 | ALC check: must match session 2 within 0.5 dB |
| 3 | `band09_band10_p9.wav` | bands 9 and 10 = +9 | ALC check: the plateau must still be there |
| 4 | `band03_p9.wav` | band 3 = +9 | replaces session 1 |
| 5 | `band05_p9.wav` | band 5 = +9 | replaces session 1 |
| 6 | `baseline_2.wav` | all 0 | |
| 7 | `band07_p9.wav` | band 7 = +9 | replaces session 1 |
| 8 | `band11_p9.wav` | band 11 = +9 | replaces session 1 |
| 9 | `baseline_3.wav` | all 0 | |

About 20 minutes. If #2 and #3 reproduce session 2, ALC changed nothing and
the session 2 model stands with bands 3, 5, 7, 11 refreshed. If they do not,
stop and say so; the full set gets re-recorded with ALC off.

Then, if the mic is still up and there is time, the tuning baseline can
follow in the same session: see `docs/procedure.md` "Tuning".
