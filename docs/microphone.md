# Microphone: HyperX SoloCast

All identification and tuning recordings so far were made with a HyperX
SoloCast (14 mm electret condenser capsule, cardioid, USB, 48 kHz / 16 bit,
sensitivity -6 dBFS at 1 V/Pa, manufacturer frequency response "20 Hz-20 kHz"
with no tolerance stated), clipped over a headrest and recorded at 44.1 kHz.

## What the mic response affects

Nothing in identification: every band basis is the ratio of two recordings
through the same mic, so the mic cancels exactly. The combined model is
mic-independent.

The tuning fit is different: it compares the measured baseline with a target
curve, and the mic response sits inside that measurement as if it were the
car. Whatever the SoloCast does to the bass or the treble, the fit will try
to undo in the speakers. `careq fit --mic-cal FILE` subtracts a
`frequency,dB` calibration curve before fitting.

## Published measurements (searched 2026-09-13)

There is no full-band third-party measurement of this microphone.

- **SoundGuys** (review, 2021) is the only outlet that measured it. Their
  chart covers the "voice band", about 50 Hz to 4 kHz, on their standard
  rig, and shows the mic flat within about +-2 dB over that range: a +3 dB
  bump around 65-75 Hz, -1.5 dB around 130-150 Hz, within +-1 dB from 200 Hz
  to 2 kHz, +2 dB at 2.3 kHz and 3.5 kHz, back to 0 at 4 kHz. Nothing below
  50 Hz or above 4 kHz.
- **HyperX / Kingston** publish only "20 Hz-20 kHz", no chart, no tolerance.
- **PC Perspective, Podcastage, PC Gamer, Tom's Guide, TechRadar,
  MMORPG, ThinkComputers** review it by ear; no measurements.
- **Audio Science Review, RTINGS, Julian Krause**: no SoloCast measurement
  found.

## Decision

No mic calibration is applied for now. Between 50 Hz and 4 kHz the one
measurement that exists says the mic is flat to +-2 dB, which is at the
level of the method's own between-file noise. Below 50 Hz and above 4 kHz
there is no data at all, and a calibration invented from a watermarked
1659-pixel screenshot would add error rather than remove it.

What this means for the fit:

- Above 4 kHz the fit is working blind on the mic's own treble character.
  Small-capsule electrets typically rise a few dB somewhere in 5-12 kHz. If
  the fitted settings cut bands 11-13 by several steps, distrust that and
  cap those bands with `--max-step` or leave them at 0.
- Below 50 Hz the fit already weights the error down to 0.05 by 30 Hz.
  Session 1's flat road-noise floor between 20 and 80 Hz hinted at a
  high-pass in the chain; the SoundGuys chart shows none down to 50 Hz, so
  if it exists it is below 50 Hz and mostly outside the fit's weight.

## How to get a real calibration

Any of these beats searching further:

1. Borrow or buy a calibrated measurement mic (miniDSP UMIK-1, about 100
   USD, ships with a per-unit calibration file `careq measure --mic-cal`
   reads directly). One baseline recorded with both mics in the same spot
   gives the SoloCast's relative response with `careq measure` on each and a
   subtraction; that becomes the SoloCast's calibration file for good.
2. The same trick with a phone whose model AutoEq or a mic-cal database
   lists, which is worse but free.
3. Check the SoloCast against itself at two distances from a speaker for
   proximity effect only, which is not the issue at 40 cm from a door
   speaker.
