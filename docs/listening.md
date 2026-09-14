# Listening: what each region does, and how to hear it

Written 2026-09-14 after the first real listening session, where all three
voicings sounded good and none sounded wrong, but the top three bands were
impossible to judge by ear.

## The general problem

A one-step change is about 0.9 dB. Nobody hears 0.9 dB on unfamiliar
material. That is why "it sounds about right" is the honest answer to a
small treble adjustment, and it is not a failure of listening.

The way to learn what a band does is to make the change far too big, hear
the character clearly, then bracket inwards. Set bands 11-13 to -6, listen
to something familiar, set them to +4, listen again. The difference will be
obvious. Now you know what that region sounds like, and a two-step
adjustment afterwards means something. Chasing single steps from the
start teaches nothing.

Always reset the volume between comparisons. Louder is reliably judged as
better, and the free level offset in the fit means some voicings need more
volume for the same loudness.

## What each region sounds like

| bands | region | too much | too little |
|---|---|---|---|
| 1-3 | 40-100 Hz | boom, one-note bass, muddy vocals | thin, no weight |
| 4-5 | 160-250 Hz | boxy, chesty, congested | hollow, lean |
| 6-7 | 500 Hz-1 kHz | honky, nasal, like a megaphone | scooped, distant |
| 8-9 | 1.6-2.5 kHz | shouty, forward, fatiguing | recessed, veiled |
| 10-11 | 4-6.3 kHz | harsh, spitty "s" sounds, edgy | dull, soft, lifeless |
| 12 | 10 kHz | thin, glassy, hissy cymbals | closed-in |
| 13 | 16 kHz | rarely audible at all | rarely audible at all |

**Test material by region.** For bands 10-11, any vocal with a lot of "s"
and "t" sounds: if sibilants sting or spit, that region is too high. For
band 12, hi-hats and ride cymbals should sound like metal being struck and
then decaying, not like a burst of white noise. For band 13, an acoustic
recording with real room ambience, listening for whether the space sounds
open or shut; most people hear nothing at all here.

## Before adjusting bands 12 and 13: check you can hear them

`stimulus/careq_hf_check_48k.wav` (regenerate with
`.venv/bin/python tools/make_hf_check.py`) plays ten 3-second tones in
order: 8, 10, 11, 12, 13, 14, 15, 16, 17, 18 kHz, with a 1.2 second gap
between each.

Every tone is level-compensated for this car's measured response *and* for
the EQ settings currently loaded, so all ten arrive at the driver's
position at the same sound pressure. Where they stop being audible is
therefore a property of the listener, not of the car.

Play it at a normal listening volume, ALC off, engine off, and count. If
the tones vanish at 14 kHz, band 13 at 16.9 kHz is doing nothing you can
perceive and should stay at 0. If they vanish at 12 kHz, the same applies
to band 12. This is completely normal: audibility above 15 kHz declines
with age in everyone, and a band you cannot hear is not a band worth
tuning.

It also bounds how much the microphone calibration is worth. The
uncertainty in the SoloCast's response lives above 4 kHz, and if the top of
that range is inaudible, a large part of that uncertainty stops mattering
for this car and this listener.

## Using a hard track as a distortion probe

Distortion at 40-50 Hz is the measured limit of this system, at about 2 %
before any boost (`docs/distortion.md`). Tracks with sustained deep
sub-bass are the only ones that expose it, and they make an excellent test
signal for setting band 1.

Turn band 1 up until such a track audibly softens or goes woolly on the
lowest notes, then come back two steps. That finds the excursion limit
directly rather than guessing at it. Note that the limit is
level-dependent, so set it at the loudest volume actually used.

On this car, band 1 at +6 was clean on everything except the deepest kick
in one track, which is close to the right place to be.
