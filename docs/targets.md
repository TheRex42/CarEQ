# Where our targets came from, and what that is worth

Asked directly on 2026-09-14: why did we vary from the JBL or Crutchfield
car curves, is there a research standard for in-car listener preference, and
were we just moving the target to make the error smaller? Answering
honestly, in that order.

## Is there a research standard for cars?

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
> by-ear overrides; the final profiles are pure fits (`docs/session6_results.md`,
> `results/final/`). Kept for the record.

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
used off-axis (`docs/microphone.md`), and it is the first independent check
on it.

It cannot separate microphone error from preference, since wanting less
treble than the target looks identical to the microphone under-reading it.
Either way the correction is the same size and small, which further reduces
what a calibrated microphone would have bought for this car.
