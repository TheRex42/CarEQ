# Equal-per-octave vs auditory-bandwidth weighting (2026-09-14)

All three voicings refit with `--erb-weight` and compared against the
log-uniform fits. Script `results/session4/three_erb/compare_weightings.py`,
plot and fit JSONs in the same folder.

## Settings

| voicing | | bands 1-13 |
|---|---|---|
| neutral | log | +4 -9 -9 +3 -1 +4 +3 -7 0 +4 -2 -2 -1 |
| | ERB | +4 -9 -8 +4 0 +4 +4 -6 +1 +4 -1 -2 0 |
| warm | log | +4 -9 -9 +4 -3 +2 +1 -9 -2 +2 -5 -5 -5 |
| | ERB | +4 -8 -5 +4 0 +4 +4 -7 -1 +3 -3 -3 -4 |
| bass-forward | log | +4 -9 -9 +2 -4 +1 0 -9 -2 +2 -4 -4 -2 |
| | ERB | +4 -6 -7 +4 -1 +4 +3 -7 0 +4 -1 -2 0 |

Neutral moves 8 bands by one step. Warm moves 11 bands by up to 4, and
bass-forward 12 bands by up to 3. Every change is in the same direction:
the ERB fit cuts less.

## Error, each set judged both ways

| voicing | settings | equal/octave | auditory bw |
|---|---|---|---|
| neutral | log-opt | **2.52** | 1.87 |
| neutral | ERB-opt | 2.58 | **1.84** |
| warm | log-opt | **2.53** | 1.95 |
| warm | ERB-opt | 2.73 | **1.84** |
| bass-forward | log-opt | **2.66** | 1.98 |
| bass-forward | ERB-opt | 2.82 | **1.87** |

Each fit wins on its own metric, as it must. The cost of using the wrong
one is 0.03 to 0.19 dB, which is far inside the 1 dB repeatability of the
multi-position baseline.

## The point

**The metric cannot choose between them, but they do not sound the same.**
The predicted responses differ by up to 2.6 dB at 40 Hz and 1.7 dB at
2 kHz, which is plainly audible, while the error numbers differ by less
than 0.2 dB, which is not measurable. This is a flat optimum: many settings
score alike and the score has no opinion about which to prefer. That
decision belongs to the ear.

Direction of the difference, consistently across all three: the ERB fit
leaves more of the 63-100 Hz hump in, adds 1 to 1.5 dB around 1 kHz, and
cuts the treble bands less.

How much it matters tracks how much bass the target asks for. Neutral
(+3 dB shelf) is nearly immune to the choice; bass-forward (+7 dB) is the
most sensitive. The more of the cabin hump a target tries to keep, the more
the weighting of the bass decides the answer.

## A practical side effect

The ERB fits use markedly less cut, so fewer bands sit at the rail:

| voicing | log (boost/cut steps) | ERB |
|---|---|---|
| neutral | 18 / 31 | 21 / 26 |
| warm | 13 / 47 | 19 / 31 |
| bass-forward | 9 / 43 | 19 / 24 |

Less extreme settings leave room to adjust afterwards, which matters given
that bands 2 and 3 pinned at -9 are the main thing preventing any further
bass correction.

## Conclusion

For the neutral voicing, which is what is loaded, the two agree within a
step on most bands and 0.05 dB on the result. No reason to change. For warm
or bass-forward the two are genuinely different tunings and both are
defensible; pick by listening, not by the number.
