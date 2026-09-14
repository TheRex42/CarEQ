# Harmonic distortion in the cabin (2026-09-14)

Prompted by an observation that something around 100 Hz sounded distorted
before any of this work started. The Farina sweep separates harmonic
distortion from the linear response for free: the k-th harmonic impulse
response lands `duration * ln(k) / ln(f2/f1)` seconds *before* the linear
one, 1.00 s for the 2nd and 1.59 s for the 3rd with this stimulus. The
existing recordings therefore already contain the answer.
`results/distortion/measure_thd.py` reproduces the numbers.

## The correction that matters

The microphone hears a harmonic through the cabin response at 2f or 3f, not
at f. Near 80 Hz the cabin is 17 dB louder than at 40 Hz, so raw harmonic
ratios wildly overstate distortion at the bottom: an uncorrected 12 % at
40 Hz becomes 2.2 % once `resp(kf) - resp(f)` is subtracted. All figures
below are corrected, i.e. distortion roughly as the speaker produces it.

## Result, EQ flat

Two independent nine-recording sessions, which agree to within 0.2
percentage points everywhere:

| fundamental | THD |
|---|---|
| 40 Hz | 2.2 % |
| 50 Hz | 1.9 % |
| 63 Hz | 1.1 % |
| 80 Hz | 1.0 % |
| 100 Hz | 1.0 % |
| 125 Hz | 1.0 % |
| 160 Hz | 0.5 % |
| 200 Hz | 1.0 % |
| 250 Hz-800 Hz | 0.2-0.45 % |

So the bass really is the dirty region: about 1 % from 63 to 200 Hz and
2 % below 50 Hz, against 0.2 to 0.4 % above 250 Hz, a factor of three to
five. The original observation was right in substance. It is a broad bass
elevation rather than a spike at 100 Hz, and at the sweep's modest level it
is not gross; at real listening volume it will be higher.

## With the EQ in

The `Session_4_target_shelf` recordings (pass-1 settings) were also made at
a higher absolute level, so this is not a clean comparison. With that
caveat:

| fundamental | flat | EQ on |
|---|---|---|
| 40 Hz | 2.2 % | 5.7 % |
| 63 Hz | 1.1 % | 1.1 % |
| 80 Hz | 1.0 % | 1.3 % |
| 100 Hz | 1.0 % | 0.8 % |
| 200 Hz | 1.0 % | 0.8 % |

From 63 to 200 Hz the EQ'd set is no worse despite being louder, which is
the 7 dB cut at 80 Hz doing its job: bands 2 and 3 at -9 reduce speaker
drive exactly where the distortion lives. At 40 Hz it is 2.6 times worse,
where band 1 is boosting.

This also partly settles the unexplained 18.6 dB level difference between
the flat and EQ-on recordings. Distortion depends on acoustic level and not
at all on recorder gain, so the rise at 40 Hz means at least part of that
difference was a genuine volume increase rather than a gain change.

## Consequence for band 1

40 to 50 Hz is the most distorted part of the spectrum before any boost is
applied, and it is the one band the fit wants to push up. Boosting band 1
adds drive precisely where the speakers are already worst. `--max-boost 4`
was chosen for head-unit headroom; the distortion data is a second,
independent reason for it.

Anyone raising band 1 above +4 in search of deep bass should expect the
distortion to climb steeply and should listen for it at volume. The
symptom is softness or a woolly quality on sustained low notes, not an
obvious crackle.
