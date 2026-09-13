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

## Cross-check against a Pixel 11 (2026-09-13)

Two recordings of the same sweep in the car, one per microphone, as a free
test of whether the SoloCast's unknown treble is a real problem. Both are
genuinely in the car: each shows the +11 to +13.5 dB cabin hump at 80 Hz,
the 160 Hz dip, and a 25 ms decay. Plot and data in `results/mic/`.

| | phone minus SoloCast |
|---|---|
| 40-120 Hz | 2.1 dB rms |
| 120 Hz-2.5 kHz | 2.5-3.2 dB rms |
| 4-8 kHz | +4.6 dB mean |
| 8-12.5 kHz | +15.3 dB mean |
| 12.5-16 kHz | +20.3 dB mean |

Below 2.5 kHz the two agree to within a few dB, and that residue is
narrow-band ripple of the shape position differences produce, not a smooth
offset. Neither microphone has a gross midrange error.

Above 2.5 kHz they diverge enormously, peaking at +21 dB near 12.5 kHz.
**The phone is the one that is wrong**, on three independent grounds:

1. A car cabin cannot rise 12 dB at 10-16 kHz. Seats, carpet and headliner
   absorb strongly up there and tweeters roll off; the phone's curve is
   acoustically impossible, the SoloCast's gentle decline is not.
2. The phone's *noise floor* rises over the same range, from -104 dBFS at
   8 kHz to -96 at 16 kHz, while the SoloCast's falls to -114. A capsule
   resonance boosts the ambient noise and the sweep equally, which is what
   is seen. A recording-chain low-pass on the SoloCast would not explain the
   phone's rising noise.
3. This SoloCast recording tracks the 18-recording pooled car baseline to
   within 3 to 6 dB above 6 kHz, ordinary single-position variation, while
   the phone departs from it by 12 to 13 dB.

The shape is a broad hump centred near 12.5 kHz: the classic acoustic
resonance of a tiny MEMS capsule in a ported phone body, probably with
recorder-side processing on top, since +21 dB is large for the capsule
alone.

**What this does and does not establish.** It eliminates the phone as a
reference and shows the SoloCast is the better of the two by a wide margin.
It does *not* calibrate the SoloCast: two unknowns, one now known to be
badly behaved, still leaves the other unmeasured. The SoloCast's in-car
curve is smooth and physically plausible, so the treble bands are unlikely
to be wildly wrong, but a few dB of unknown remains above 4 kHz.

It also settles a Phase 2 question in advance: an Android app using the
phone's internal microphone **cannot** work without a calibration file. A
20 dB error in the top octave would drive the fit to cut bands 11-13 to the
rail.

## Decision

No mic calibration is applied for now (unchanged by the Pixel cross-check
above, which ruled the phone out as a reference rather than vouching for the
SoloCast). Between 50 Hz and 4 kHz the one
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
