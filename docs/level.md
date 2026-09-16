# Measurement volume

Asked 2026-09-15: what should the standard measurement volume be? Every
session so far used Mazda volume **25** with ALC off, which is the right
instinct, but the number is only meaningful inside this one car and is lost
if the head unit is ever reset.

## Why the absolute level matters at all

Less than you might expect, and then suddenly a lot.

The band model is a ratio, so a constant gain cancels. The fit normalises
level, so the target comparison is of shape. For a perfectly linear system
the volume would be irrelevant and only consistency would matter.

It stops being irrelevant at both ends:

- **Too loud** and the system is no longer linear. The head unit's limiter
  engages, and the door speakers are already at about 2 % distortion at
  40-50 Hz (`docs/distortion.md`). A measurement taken into a limiter
  describes the limiter, not the car. Two sessions were misread this way
  when ALC was quietly adding 6 dB.
- **Too quiet** and the SNR falls. This was never the binding constraint
  here: achieved SNR was 45-65 dB and road noise only mattered below 31 Hz.
- **Far from how you listen** and the tonal balance you tune for is not the
  one you hear, because perceived balance shifts with level.

## The recommendation

**Set it with the pink noise file, to 75 dB SPL, C-weighted, slow, at the
driver's head position.** Then note which Mazda volume number that is and
use that number for everything.

Pink noise rather than sweeps because SPL meters are built for steady
broadband signals and a sweep's reading wanders. The two stimulus files are
not at the same level:

| file | RMS while playing |
|---|---|
| `careq_pink_48k_60s.wav` | -20.0 dBFS |
| `careq_sweep_48k_10s_x3.wav` | -15.0 dBFS |

So **the sweep runs 5.0 dB hotter than the pink file at the same volume
setting.** Set 75 dB on pink and the sweep will produce about 80 dB. Either
is a fine reference as long as it is stated; this document means the pink
one.

75 dB is a common measurement reference, sits near real in-car listening
levels, and leaves headroom before the limiter. A phone SPL app is accurate
enough, since what is wanted is a repeatable and recoverable number rather
than metrology.

## Verify the level is in the linear region

Worth doing once. Record the same position at the chosen volume and about
6 dB higher, then:

```
careq measure loud.wav --stimulus stimulus/stimulus.json --out loud.csv
careq measure normal.wav --stimulus stimulus/stimulus.json --out normal.csv --compare loud.csv --plot lin.png
```

Both are level-normalised before comparison, so a difference is a change in
*shape*, which a linear system cannot produce. Agreement within the usual
1 dB repeatability means the chosen volume is safely linear. A systematic
difference, especially bass flattening at the louder setting, means the
limiter is active and the measurement volume should come down.

This is the same test that would have caught ALC on the first day, which is
the reason it is worth building into the routine rather than running once.

## Changing it

If the reference volume ever changes, say so in the session notes. The
existing baselines (`results/session4/`) were taken at volume 25 and a new
one at a different level is still directly comparable in *shape*, since
everything is level-normalised, but only if both are inside the linear
region. That is what the check above establishes.
