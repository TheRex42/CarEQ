import numpy as np
import pytest

from careq.signals import SweepSpec
from careq.simulate import Scenario


@pytest.fixture(scope="session")
def short_spec():
    # 4 s sweeps keep the suite fast; the 2nd harmonic IR still lands 0.4 s early,
    # beyond the synthetic cabin's tail.
    return SweepSpec(duration=4.0, pre_silence=0.5, post_silence=1.5, repeats=2)


@pytest.fixture(scope="session")
def scenario(short_spec):
    return Scenario.default(short_spec, seed=0)


def band_mask(freq, lo=40.0, hi=16000.0):
    return (freq >= lo) & (freq <= hi)


def max_abs(a, b, freq, lo=40.0, hi=16000.0):
    m = band_mask(freq, lo, hi)
    d = np.asarray(a) - np.asarray(b)
    return float(np.max(np.abs(d[m])))


def rms(a, freq, lo=40.0, hi=16000.0):
    m = band_mask(freq, lo, hi)
    return float(np.sqrt(np.mean(np.asarray(a)[m] ** 2)))
