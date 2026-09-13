# Recording procedure (Phase 0 / 1)

## Once

1. `careq gen --out stimulus` -> copy `careq_sweep_48k_10s_x3.wav` to a USB
   stick (FAT32). Keep `stimulus/stimulus.json`.
2. Phone recorder app: mono WAV, 48 kHz preferred (44.1 kHz is resampled),
   16 or 24 bit, **audio source "unprocessed" or "voice recognition"**, all
   automatic gain control / noise suppression / limiter OFF, fixed gain. Check
   the app cannot change gain between recordings. Examples: RecForge II
   (source: Unprocessed), Easy Voice Recorder Pro (source: Unprocessed),
   Audio Recorder by Sony. Any recorder works if its gain is fixed.
3. Head unit: Sound adjustment mode = Advanced, Bass / Treble = 0, Fader and
   Balance centred, listening position "Driver's seat" or "All seats" (pick
   one and keep it), ALC off, Automatic source level adjustment off.
   Bose cars: Centerpoint off, AudioPilot off, stereo mode Standard.
   Equalizer: Customize EQ, all 13 sliders at 0 -> that is the baseline.
4. Volume: loud enough that the sweep is well above cabin noise but the
   recording never clips. Aim for peaks around -6 dBFS in the recorder's
   meter during the sweep. Note the volume number and never change it
   during a session. Engine off, doors closed, HVAC off, phone silent.
5. Phone position: at the driver's head position, mic pointing up or toward
   the windshield, held by a stand or a rolled towel on the headrest. Do not
   hold it by hand. The phone must not move between the baseline and the
   band recordings of one identification session.

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

Multi-position baseline: all bands 0, record at 5-7 positions around the
driver's head (+-15 cm left/right/forward/back/up/down). Pool them:

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
