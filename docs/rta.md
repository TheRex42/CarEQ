# Pink noise alongside sweeps

Added 2026-09-15. `careq gen --pink 60` already wrote the stimulus; the
analysis side is now `careq rta`, which turns a continuous-noise recording
into the same 1/3-octave CSV a sweep produces, so it drops straight into
`careq fit --measurement`.

## What each stimulus is actually good for

| | swept sine | pink noise |
|---|---|---|
| impulse response, phase, waterfall | yes | no |
| harmonic distortion separated in time | yes | no |
| processing gain against steady noise | ~40 dB for a 10 s sweep | none |
| can window out late room energy | yes | no, always steady-state |
| microphone may move during the take | no | **yes** |
| survives a transient (door, passing truck) | no, corrupts one frequency region | yes, averages out |
| excites the system like music does | no, one frequency at a time | yes |
| live, updates as you adjust | no | yes |

The two that matter here are the last three rows and the "mic may move" row.

**Spatial averaging in one take.** The tuning baseline needed nine separate
37 s recordings plus repositioning. A single 60-90 s noise take with the
microphone moved slowly through the volume a head occupies gives a
*continuous* spatial average, which is arguably a better estimate than nine
discrete points, in a fifth of the time. A sweep cannot do this: moving the
microphone mid-sweep smears position changes onto the frequency axis,
because at any instant the sweep is only exciting one frequency.

**Broadband loading.** The head unit's limiter and ALC respond to broadband
content, not to a single swept tone. This project was bitten by exactly
that: ALC quietly added 6 dB and the limiter clipped large boosts, and it
looked like a head-unit design quirk for two sessions. Noise at a realistic
level shows the system as music loads it.

## Do they agree?

On the synthetic car, with the same cabin, microphone and 40 dB SNR:

| | error vs known truth |
|---|---|
| swept sine | 0.02 dB rms, 0.18 dB max |
| pink noise | 0.03 dB rms, 0.17 dB max |
| the two against each other | 0.04 dB rms |

They should agree in a car, and this confirms it. The reason is that a car
decays in about 25 ms while the sweep analysis window is 500 ms, so the
window already contains essentially all the room energy that steady-state
noise measures. In a large room the two would diverge in the bass, and a
target written for one would not transfer to the other.

That makes a real-car comparison worth doing as a check rather than a
formality: if they agree, both methods are sound. If they disagree, the
difference is diagnostic, pointing at level-dependent behaviour, at
something time-varying, or at the microphone having moved during a sweep.

## Division of labour

- **Identification** stays on sweeps. It needs precise ratios, benefits from
  the noise immunity, and the microphone is clamped still anyway.
- **Distortion, impulse response, the REW cross-check** are sweeps only.
- **Tuning baseline**: either. Noise with a moving microphone is faster and
  samples space more thoroughly; sweeps at discrete positions are the
  existing, validated path. Doing both and comparing costs five minutes.
- **Verification after changing sliders**: noise, for speed.

## Commands

```
careq gen --out stimulus --pink 60          # already done; file is in stimulus/

careq rta REC.wav --out rta.csv --plot rta.png
careq rta REC.wav --compare results/session4/baseline_pooled_18.csv --plot cmp.png
careq rta p1.wav p2.wav p3.wav --out rta.csv        # pooled, power domain
careq fit --measurement rta.csv --model results/session3/eq_model.json --target mazda_neutral
```

`--stimulus-wav` defaults to `stimulus/careq_pink_48k_60s.wav` and its
spectrum is divided out, which is more accurate than assuming ideal pink
because it removes the generator's band edges. Leading and trailing silence
is trimmed automatically, and the half second before the noise starts is
used for an SNR estimate.

## Limits worth remembering

Magnitude only. No phase, no impulse response, no distortion, and no
processing gain, so the SNR is roughly that of the raw recording rather than
40 dB better. In a quiet parked car that is still ample, and it was never
the binding constraint here: road noise only mattered below 31 Hz even for
sweeps.
