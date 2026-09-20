# Where our targets came from, and what that is worth

Asked directly on 2026-09-14: why did we vary from the JBL or Crutchfield
car curves, is there a research standard for in-car listener preference, and
were we just moving the target to make the error smaller? Answering
honestly, in that order.

## Is there a research standard for cars?

> **CORRECTED 2026-09-18.** There are three experimentally determined in-car
> targets, collected by Toole (JAES 2015, Fig. 15): Olive & Welti (Harman),
> Clark, and Binelli & Farina. None has the statistical backing of the Harman
> headphone target, but "no in-car target exists" was wrong. See
> "Research round 2" at the end.

No, not in the sense the question implies.

Harman's listener-preference work, the thing usually meant by "the Harman
curve", is on headphones and on loudspeakers in rooms. It is genuinely
substantial: hundreds of listeners across several countries, a predictive
statistical model, many peer-reviewed AES papers. Its automotive
publications are mostly measurement methodology rather than a preferred
curve, for example Olive and Welti's binaural car scanning validation paper
at the AES automotive conference in 2009.

The car curves in circulation are informal. HouseCurve's page introduces
them with no attribution at all, and the Car B file's entire provenance is
a one-line header reading "Variant of JBL curve". Our own
`careq/targets/README.md` reports those labels faithfully, but a label is
not a derivation.

What the various curves do agree on is a broad shape: a bass lift of
roughly 6 dB, flat mids, and a gentle treble roll-off. They disagree on
amounts because nobody has settled them.

## Did we move the target to reduce the error?

No, and the numbers rule it out. All four candidates were fitted against
the same recordings:

| target | weighted RMS after fit |
|---|---|
| Car C (Crutchfield-derived) | **2.49 dB** |
| flat mids + 3 dB shelf (chosen) | 2.64 dB |
| Car B (JBL-derived, the default) | 2.86 dB |
| Car A | 3.01 dB |

Car C scored best and was not chosen. Had error minimisation been the
criterion, the answer would have been Car C. Note also that a target being
easier to reach says something about the target, not about the car: Car C
happens to resemble this cabin's own response more closely.

## So why the flat shelf?

Because the project's notes recorded, before any measurement existed, that
the owner prefers flat mids with a slight bass shelf. The target was built
from that stated preference and nothing else.

That is a legitimate basis. It is also a preference rather than a finding,
and earlier drafts of these documents did not label it clearly enough.
`mazda_neutral`, `mazda_warm` and `mazda_bass` are three points in a
preference space, offered for listening, not derived from anything.

## One place our targets look conservative

Ours ask for 3 to 7 dB of bass lift. The informal consensus, and the car
curves above, sit nearer 6 to 10. Three independent things now point the
same way:

1. The owner's listening report of "kick, not deep rumble".
2. The auditory-bandwidth weighting, which de-emphasises the bass and
   consequently leaves more of the cabin hump in (`docs/weighting.md`).
3. Common practice, weakly, given the caveat below.

The caveat is real: target curves do not transfer between measurement
protocols. A steady-state room measurement accumulates low-frequency
reverberant energy that our 500 ms window excludes, so a curve written for
one reads differently under the other. A number taken off someone else's
screen cannot be applied directly to ours.

## The treble, settled by ear

> **OVERTURNED 2026-09-18 (session 6).** The calibrated iMM-6 showed the
> SoloCast read 4-6 dB HOT above 6 kHz, not 1.5 dB low as inferred below, so
> the by-ear cuts compensated in the wrong direction. The owner dropped the
> by-ear overrides; the final profiles are pure fits (`results/final/`).
> Kept for the record.

On 2026-09-14 the owner tuned bands 11 to 13 by ear on female vocals,
listening for sibilance and cymbals, and landed on **-4 -4 -2** where the
`mazda_neutral` fit had given -2 -2 -1.

That is a measurement in its own right. Refitting with a hypothetical
microphone correction applied:

| assumed SoloCast error above 6 kHz | fitted bands 11, 12, 13 |
|---|---|
| none | -2 -2 -1 |
| reads 1 dB low | -3 -3 -2 |
| reads 2 dB low | -4 -3 -3 |
| reads 3 dB low | -5 -4 -4 |
| by ear | **-4 -4 -2** |

The by-ear result sits between the 1 dB and 2 dB rows, so the ear puts the
microphone's treble error at roughly 1.5 dB low above 6 kHz. That is the
same direction and the low end of the magnitude predicted for a cardioid
used off-axis, and it is the first independent check
on it.

It cannot separate microphone error from preference, since wanting less
treble than the target looks identical to the microphone under-reading it.
Either way the correction is the same size and small, which further reduces
what a calibrated microphone would have bought for this car.

## Research round 2 (2026-09-18): where targets come from, and what the ears chose

Prompted by the owner's first drive on the calibrated Neutral: treble too
bright, bass a little thin. Settled by ear on
`+6 -8 -7 +1 -2 +4 -2 -7 0 +4 -2 0 +1` (bands 12-13 down 3 steps, bands 1-3
up 1-2). Warm "sounded odd".

### The primary source: Toole 2015

F. E. Toole, "The Measurement and Calibration of Sound Reproducing Systems",
JAES 63(7/8), 2015 (free copy: linkwitzlab.com/Toole-Room calibration.pdf).
Two figures matter, both digitised by eye into `careq/targets/` (~+-1 dB):

- **Fig. 14**: preferred steady-state room curves from Olive, Welti &
  McMullin (AES 135th Conv. 2013, paper 8994). Listeners adjusted bass and
  treble on a loudspeaker EQ'd flat in a treated room. Untrained listeners (4)
  chose "more of everything", about +10 dB bass and treble above flat;
  trained listeners (7) chose about +3.5 dB bass and treble falling to
  about -5 dB by 10-16 kHz. Toole: "a single target curve is not likely to
  satisfy all listeners", hence his case for accessible bass and treble
  controls. Files `olive2013_room_{untrained,all,trained}`.
- **Fig. 15**: three in-car targets, Olive & Welti (Harman; AES 36th Int.
  Conf. 2009), Clark (AES 110th Conv. 2001, paper 5407), Binelli & Farina
  (AES 125th Conv. 2008, paper 7575), plus the average of five premium
  factory systems. All lift the bass about 8 dB below 50-100 Hz "to compete
  with the substantial road, aerodynamic, and mechanical noise"; all are
  flat through the mids; treble ends -4 to -10 dB at 20 kHz, while the
  factory average stays flat. Files `olive_welti_car`, `clark_car`,
  `binelli_farina_car`.

### DMS's REW bounds

The source was not found. Read off his screenshot, the two curves have the
same treble, only -1.1 to -1.5 dB by 20 kHz, and differ only in the bass: a
~+10 dB low shelf turning over near 80 Hz (lower) versus a ~2.5 dB/octave
rise below 300 Hz (upper). That is a range of acceptable bass over a nearly
flat top, closer to Olive's untrained listeners and the factory average than
to any of the three car targets. Files `dms_lower_bound`, `dms_upper_bound`
(provenance unknown; reference only).

### The curve the ears chose

The by-ear settings applied to the measured Neutral response
(`results/session6/verify_pooled.csv` plus the model's change) give, 1-octave
smoothed, relative to 200 Hz-2 kHz:

| | 40-80 Hz | 4-8 kHz | 10-16 kHz |
|---|---|---|---|
| by ear | +3.9 | -1.3 | -4.7 |
| Olive 2013 trained | +3.5 | -4.0 | -5.1 |
| Olive 2013 all | +5.4 | -2.1 | -2.7 |
| Olive & Welti car | +7.4 | -1.5 | -3.1 |
| `harman_car` (HouseCurve B) | +4.5 | -2.8 | -4.6 |
| DMS lower bound | +7.6 | -1.7 | -1.9 |
| `mazda_neutral` | +3.0 | -0.9 | -1.6 |
| Olive 2013 untrained | +9.0 | +0.7 | +1.6 |

Reduced to what Olive's listeners actually adjusted (a bass shelf and a
treble tilt), it is **+4 dB low shelf (half-gain near 160 Hz), flat mids,
-3.25 dB/octave above ~4.2 kHz** (1.15 dB rms from the by-ear curve). Saved
as `careq/targets/mazda_by_ear.csv`. Fitting the EQ to it returns bands
11-13 at -2 0 +1 (max boost 6), the by-ear treble exactly.

**Every published target with a falling treble reproduces the by-ear
treble.** `harman_car`, `olive_welti_car` and `olive2013_room_trained` all
fit bands 12-13 to 0 / +1. Only `mazda_neutral` asks for +3 / +5, because
its treble falls just 2 dB by 20 kHz. The brightness was the target, not
the measurement: `mazda_neutral` was built from a stated preference with
the SoloCast, which read 4-6 dB hot up top, so a nearly flat target looked
right then.

**Warm sounded odd** most likely because its fit makes a presence dip:
predicted Warm minus by-ear is -2.1 dB at 2.5 kHz and -1.4 at 6.3 kHz, with
+1.2 at 160 Hz and 16 kHz. With boosts capped, the fit reaches Warm's bass
target partly by cutting the mids (bands 5, 7, 9) instead.

**Bass:** the by-ear bass (+3.9 at 40-80 Hz) is below the car targets (+7 to
+9) but bands 2-3 at -8 / -7 hold 63-125 Hz about 1.5 dB above what any
target fit leaves; that was chosen while driving, which is what the car
targets' extra bass is for.

### What this means for the method

Olive's targets are averages of method-of-adjustment results. The owner's
by-ear settings are one listener's method-of-adjustment result, measured
through a calibrated microphone, so for this car and this listener
`mazda_by_ear` is the better-grounded target. The published curves bound it:
bass between trained-listener and car-target levels, treble on the
trained-listener / Harman-car slope.

### ResoNix (added 2026-09-18)

ResoNix Sound Solutions (Nick Apicella) publishes REW house curves for car
audio in a public Google Drive folder: "ResoNix Target Curve 2026" (May 2026,
current), and in an "Old House Curves" subfolder "Accurate" (Aug 2023) and
"Laid Back" (Jun 2025). Bundled as `resonix_2026`, `resonix_accurate_2023`,
`resonix_laid_back_2025`. Their README: pink noise, REW RTA, spatial average
around the head from the driver's seat, Earthworks M23. That is careq's
moving-mic method, so the curves apply directly. Derived from the author's
tuning practice, not listening tests; he says they are "not one-size-fits-all"
and that the upper-mid dip is partly specific to his own car (tweeters
crossed at 5 kHz to dodge a reflection).

| relative to 200 Hz-2 kHz | 40-80 Hz | 2-3 kHz | 4-8 kHz | 10-16 kHz | 20 kHz |
|---|---|---|---|---|---|
| `resonix_2026` | +10.5 | ~-5 | -2.6 | -2.7 | -2.8 |
| `resonix_laid_back_2025` | +10.1 | ~-5 | -5.0 | -5.0 | -5.9 |
| `resonix_accurate_2023` | +10.3 | ~-2 | -1.4 | -1.7 | -0.8 |
| `mazda_by_ear` | +3.1 | -0.4 | -1.8 | -5.6 | -7.7 |

About twice the bass of the research car target and a deliberate 2-3 kHz
dip. On this head unit (max boost 6) the fits cut bands 8-9 to -9 and fit
worse than the other targets: 2026 `+6 -5 -9 0 -6 +3 -6 -9 -9 -1 -5 -1 +2`
(4.58 -> 2.31 dB), Laid Back `+6 -6 -9 0 -4 +4 -8 -9 -9 -2 -8 -2 -1`
(4.92 -> 2.60), Accurate `+6 -6 -9 -1 -6 +2 -7 -9 -6 +1 -5 0 +1` (4.24 ->
2.22). Their bass lift assumes a subwoofer; below 45 Hz the doors cannot
follow. Figures in `results/final/share/mazda3_eq_resonix_*.png`.

**Microphone orientation, open question.** The ResoNix folder's "90 degree"
calibration for the M23 is 0 dB to 2 kHz, -0.5 at 4k, -1.5 at 8k, -4 at 16k,
-6 at 20k: a capsule pointed up loses treble. The session 6 plan held the
iMM-6 capsule up, and Dayton supplies one (on-axis) calibration file. If the
iMM-6 behaves like the M23 at 90 degrees, the calibrated treble above 8 kHz
reads 1.5-4 dB low, part of what the ear then trimmed. Not measured; a
same-spot pink take capsule-up vs capsule-forward would settle it.
