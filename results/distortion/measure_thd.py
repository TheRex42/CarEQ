"""Harmonic distortion vs frequency, using the Farina separation already in the pipeline.

The k-th harmonic impulse response lands duration*ln(k)/ln(f2/f1) seconds BEFORE
the linear one, so it can be windowed out separately. Level of the k-th harmonic
at output frequency k*f, over the linear response at f, is the k-th harmonic
distortion at fundamental f.
"""
import numpy as np, sys, os, glob
sys.path.insert(0,'.')
from careq.signals import SweepSpec, exp_sweep, inverse_filter
from careq.measure import (load_wav, find_onsets, deconvolve, window_ir, LOG_GRID as G,
                           frac_octave_average, EPS)
from scipy.fft import rfft, rfftfreq, next_fast_len
spec=SweepSpec.load('stimulus/stimulus.json'); fs=spec.fs
sweep=exp_sweep(spec); inv=inverse_filter(spec,sweep)
L = spec.duration/np.log(spec.f2/spec.f1)          # seconds per neper of frequency
DT = {k: L*np.log(k) for k in (2,3)}
NF = 1<<17
def harmonics(path):
    rec,_ = load_wav(path, fs_target=fs)
    onsets,_ = find_onsets(rec, sweep, min_separation=spec.n_sweep//2)
    cache={}; out={1:[],2:[],3:[]}
    for on in onsets:
        margin=int(2.0*fs); tail=int(1.0*fs)
        start=on-margin; stop=on+spec.n_sweep+tail
        seg=np.zeros(stop-start); lo,hi=max(0,start),min(len(rec),stop)
        seg[lo-start:hi-start]=rec[lo:hi]
        h=deconvolve(seg,inv,cache)
        expect=(on-start)+spec.n_sweep-1
        w=int(0.02*fs); a,b=max(0,expect-w),min(len(h),expect+w)
        peak=a+int(np.argmax(np.abs(h[a:b])))
        out[1].append(rfft(window_ir(h,peak,fs,20.0,300.0,0.3),NF))
        for k in (2,3):
            c=peak-int(round(DT[k]*fs))
            # narrower window: harmonic IRs are short and must not catch neighbours
            out[k].append(rfft(window_ir(h,c,fs,30.0,120.0,0.4),NF))
    return {k: np.mean([np.abs(x)**2 for x in v],axis=0) for k,v in out.items()}
fl = rfftfreq(NF,1/fs)
def thd_curve(paths):
    P={1:0,2:0,3:0}
    for p in paths:
        h=harmonics(p)
        for k in (1,2,3): P[k]=P[k]+h[k]
    sm={k: frac_octave_average(fl,P[k]/len(paths),6.0,G) for k in (1,2,3)}
    return sm
def at(a,f): return a[np.argmin(np.abs(G-f))]
sets={
 'EQ flat (Session_4, 9 files)': sorted([f for f in glob.glob('Recordings/Session_4/*.wav')
                                          if not any(k in f for k in ('165057','165617'))]),
 'EQ flat (Session4a, 9 files)': sorted(glob.glob('Recordings/Session4a/*.wav')),
 'EQ on   (target_shelf, 5)':    sorted([f for f in glob.glob('Recordings/Session_4_target_shelf/*.wav')
                                          if '174957' not in f]),
}
FR=[40,50,63,80,100,125,160,200,250,315,400,500,800]
print("Harmonic level relative to the fundamental, dB (more negative = cleaner).")
print("H2 at 2f and H3 at 3f, per fundamental frequency f.\n")
res={}
for name,paths in sets.items():
    sm=thd_curve(paths); res[name]=sm
    l=10*np.log10(sm[1]+EPS)
    def rel(k,f):
        num=at(10*np.log10(sm[k]+EPS), k*f); return num-at(l,f)
    print(f"{name}")
    print("      f:  " + " ".join(f"{f:>6g}" for f in FR))
    print("     H2:  " + " ".join(f"{rel(2,f):+6.1f}" for f in FR))
    print("     H3:  " + " ".join(f"{rel(3,f):+6.1f}" for f in FR))
    thd=[10*np.log10(10**(rel(2,f)/10)+10**(rel(3,f)/10)) for f in FR]
    print("  H2+H3:  " + " ".join(f"{v:+6.1f}" for v in thd))
    print("     %:   " + " ".join(f"{100*10**(v/20):>6.1f}" for v in thd))
    print()

print("="*78)
print("CORRECTED: the mic sees the harmonic through the cabin response at 2f/3f,")
print("which near 80 Hz is up to 17 dB louder than at the 40 Hz fundamental.")
print("Subtracting resp(kf)-resp(f) gives distortion as the SPEAKER makes it.\n")
for name,sm in res.items():
    l=10*np.log10(sm[1]+EPS)
    def cor(k,f):
        raw=at(10*np.log10(sm[k]+EPS),k*f)-at(l,f)
        return raw-(at(l,k*f)-at(l,f))
    print(f"{name}")
    print("      f:  " + " ".join(f"{f:>6g}" for f in FR))
    print("     H2:  " + " ".join(f"{cor(2,f):+6.1f}" for f in FR))
    print("     H3:  " + " ".join(f"{cor(3,f):+6.1f}" for f in FR))
    t=[10*np.log10(10**(cor(2,f)/10)+10**(cor(3,f)/10)) for f in FR]
    print("    THD:  " + " ".join(f"{100*10**(v/20):>6.2f}" for v in t) + "   %")
    print()
print("cabin response used for the correction (dB re 200 Hz-2 kHz):")
sm=res['EQ flat (Session_4, 9 files)']; l=10*np.log10(sm[1]+EPS); l=l-np.mean(l[(G>=200)&(G<=2000)])
print("      f:  " + " ".join(f"{f:>6g}" for f in [40,80,120,100,200,300,160,320,480]))
print("   resp:  " + " ".join(f"{at(l,f):+6.1f}" for f in [40,80,120,100,200,300,160,320,480]))
