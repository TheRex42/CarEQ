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

### Is it automatic gain control, or a fixed filter?

A resonance is a fixed linear filter; a gain control is time-varying, and
time-varying gain leaves fingerprints a resonance cannot. Three tests, all
negative:

1. **Noise floor through the 2 s gaps between sweeps.** A gain control
   recovering during silence makes the floor swell. The phone's floor above
   8 kHz is flat to 0.4 dB across both gaps (-69.8 to -70.1 dBFS). The
   broadband floor wanders 4 dB in both directions, but so does the
   SoloCast's: that is passing traffic, not the recorder.
2. **Sweep-to-sweep agreement.** Gain state depends on history, and sweep 1
   is preceded by 1 s of silence against 2 s for sweeps 2 and 3. The phone's
   three sweeps agree within 0.17 dB at every frequency including 10 and
   14 kHz, and are *more* consistent than the SoloCast's (0.48 dB).
3. **Envelope dynamic range.** Compression squashes the loud bass hump and
   lifts the quiet treble. The phone's sweep envelope spans 35.2 dB against
   the SoloCast's 31.9, and the phone does not pull the bass hump down at
   all. The range is wider, not narrower: the opposite of compression.

So the phone's HF excess is a fixed linear filter, whether that is the
capsule's port resonance, the recorder's processing, or both. For
correction purposes it does not matter which, since a fixed linear error is
exactly what a calibration file removes. It matters only for durability: a
capsule resonance is permanent, app processing can change with a settings
or version change, so pin both before calibrating a phone.

### How much of the gap is the phone?

Not all of it. This SoloCast recording is also 3.5 dB below the
18-recording pooled baseline at 10 kHz and 6.4 dB below it at 16 kHz, far
more than the usual single-position scatter. The SoloCast is cardioid, and
a cardioid's high end falls away off-axis, so a headrest clip pointing
somewhere other than at the speakers loses treble that an omnidirectional
phone capsule keeps.

Measured against the pooled car baseline instead of against this one file,
the phone runs about +13 dB hot at 10 to 16 kHz, and this particular
SoloCast placement accounts for the remaining 5 to 8 dB of the headline
gap. Both effects are real. The phone's is much the larger.

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

## Upgrade path when an omni reference arrives

Decided 2026-09-13: future runs use an omnidirectional measurement
microphone. Pattern matters more than the unknown response curve. In a car,
sound arrives from door woofers, dash tweeters, rear speakers and
reflections at many angles; a cardioid weights those differently from an
ear, and differently at 10 kHz than at 1 kHz because its pattern narrows
with frequency. No single calibration curve fixes a directivity error,
because the error depends on the direction of arrival, not only on
frequency. Measurement microphones are omni by design for this reason, and
all three candidates below are omni.

Nothing already measured is invalidated:

- `results/session3/eq_model.json` is built from ratios through one
  microphone and is microphone-independent. It stands as it is.
- Only the tuning baseline needs redoing: nine recordings, about ten
  minutes, then refit against the same targets with `--mic-cal`.
- The settings that should move are bands 11-13. Everything below 4 kHz is
  already agreed between two microphones to within position scatter.

Keep the current settings in the car meanwhile. They were verified by
measurement and the treble bands sit at 0 to -1, so any microphone error up
there has had little influence on them.

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
