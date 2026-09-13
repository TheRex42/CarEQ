# Recording procedure (Phase 0 / 1)

## Once

1. `careq gen --out stimulus` -> copy `careq_sweep_48k_10s_x3.wav` to a USB
   stick (FAT32). Keep `stimulus/stimulus.json`.
2. Phone recorder app: mono WAV, 48 kHz preferred (44.1 kHz is resampled),
   16 or 24 bit, **audio source "unprocessed" or "voice recognition"**, all
   automatic gain control / noise suppression / limiter OFF, fixed gain. Check
   the app cannot change gain between recordings.
   Chosen app: **RecForge II** - Settings: format WAV, 48000 Hz, mono, audio
   source Unprocessed (else Voice recognition), gain/normalize off. Make a
   10 s test recording first and confirm it is WAV, mono, not silent.
   Transfer files by cable or file sync, never through messaging apps (they
   re-encode audio).
3. Head unit: Sound adjustment mode = Advanced, Bass / Treble = 0, Fader and
   Balance centred, listening position "Driver's seat" or "All seats" (pick
   one and keep it), ALC off, Automatic source level adjustment off.
   Bose cars: Centerpoint off, AudioPilot off, stereo mode Standard.
   Equalizer: Customize EQ, all 13 sliders at 0 -> that is the baseline.
4. Volume: loud enough that the sweep is well above cabin noise but the
   recording never clips. Aim for peaks around -6 dBFS in the recorder's
   meter during the sweep (middle to upper third of the meter). Note the
   volume number and never change it during a session.
   **Engine off, ignition in accessory mode**, HVAC fan off, doors closed,
   phone silent. If battery is a worry, run the engine for a minute between
   blocks of recordings, then switch it off again before recording.
5. Phone position for identification: **empty driver's seat**, phone on a
   tripod / clamp holder on the headrest post (or wedged upright against
   the headrest with a towel) at ear height, mic end up, nothing within a
   few cm of the mic. Do not hold it by hand and do not sit in the seat.
   Occupancy does not matter here because every band is a ratio to the
   baseline; what matters is that the phone does not move at all between
   the baseline and the band recordings. If it gets bumped, record a new
   baseline and continue from there.

## Identification session (once per car, ~20 minutes)

Start the recorder, press play on the USB file, wait for the file to end,
stop the recorder. One file = one recording.

```
baseline_1.wav        all bands 0
baseline_2.wav        all bands 0 (again; gives the noise floor and repeatability)
band01_p9.wav         band 1 at +9, all others 0
band02_p9.wav         band 2 at +9, all others 0
...
band13_p9.wav
band04_m9.wav         optional: band 4 at -9 (symmetry check)
band04_p3.wav         optional: band 4 at +3 (linearity check)
baseline_3.wav        optional: all bands 0 again at the end (drift over the session)
```

Write a manifest (paths relative to the manifest file):

```json
{
  "stimulus": "stimulus.json",
  "baseline": ["baseline_1.wav", "baseline_2.wav"],
  "bands": [
    {"band": 1, "steps": 9, "files": ["band01_p9.wav"]},
    {"band": 2, "steps": 9, "files": ["band02_p9.wav"]},
    {"band": 4, "steps": -9, "files": ["band04_m9.wav"]},
    {"band": 4, "steps": 3, "files": ["band04_p3.wav"]}
  ],
  "labels_hz": [40, 63, 100, 160, 250, 400, 630, 1000, 1600, 2500, 4000, 6300, 10000]
}
```

`labels_hz` are whatever the head unit prints under the sliders; they are
labels only. Then:

```
careq identify --manifest session/manifest.json --out eq_model.json \
               --baseline-csv baseline.csv --plot bases.png
```

Look at the diagnostics printed per sweep: `corr-quality` should be in the
thousands, drift the same for every file (same two clocks), SNR at 100 Hz /
1 kHz / 10 kHz well above 20 dB, and no `CLIPPING!`. In the band table every
band should show a single clear peak near its label with a similar dB/step;
`level offset` warnings mean the phone moved or the recorder changed gain.

## Tuning (repeatable)

Multi-position baseline, **occupied seat**: sit in the driver's seat in
normal posture, all bands 0, hold the phone at ear height 10-20 cm from
the head, mic up, and record at 5-7 spots (left ear, right ear, slightly
forward, back, higher, lower). Same volume and recorder gain as the
identification session. `careq fit` power-averages all positions (never
the raw waveforms), so position-specific ripple flattens out and only
features common to all positions get corrected. Record a position twice to
weight it more. Do not strap the phone to your head: the target curves
assume a mic at the listening position, not at the ear.

```
careq fit --measurement pos1.wav --more pos2.wav pos3.wav ... \
          --model eq_model.json --target harman_car --plot fit.png
```

Set the 13 integers, record again at the same positions and run
`careq measure pos*.wav --plot after.png` to confirm the prediction.

## REW cross-check

`careq measure REC.wav --save-ir ir.wav` writes the averaged impulse response
as a WAV; import it into REW (File > Import > Import impulse response) and
compare with the CSV at 1/3-octave smoothing; they should agree within ~1 dB.
Alternatively measure with REW's own sweep played from the same USB stick and
compare its exported response with `careq measure` of a recording made in
the same position.

## Target curve

`harman_car` (default) is HouseCurve's "Car B", a JBL-derived car curve
(+6 dB shelf below 40 Hz, +1 dB at 250 Hz, 0 at 2 kHz, -5 dB at 20 kHz),
used as a stand-in for Harman's in-car preference research, which has no
single published file. It is a placeholder. The owner prefers flat mids with a
slight bass shelf; that is a four-line file, e.g.

```
frequency,raw
20,3
80,3
200,0
20000,0
```

(add a point like `2000,0` / `20000,-3` for a gentle treble tilt), passed as
`careq fit --target mycurve.csv`. Re-running the fit against several targets
needs no new recordings.

## What EQ can and cannot fix

The fit corrects everything in the averaged baseline that a ~1-octave-wide
band can reach: cabin gain, the main bass mode, panel resonances, tilt.
Cabin modes narrower than a band are only partially reduced; nulls from
cancellation are not filled (boosting into them wastes headroom), and the
plot shows a band pinned at +9 when the fit is trying - cap it with
`--max-step` or adjust the weights (`--w-lo`, `--w-hi`, `--fmin`, `--fmax`).
