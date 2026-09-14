import numpy as np, sys, json, os
sys.path.insert(0,'.')
from careq.measure import Response, LOG_GRID as G
from careq.identify import EqModel
from careq.fit import (fit_eq, load_target, default_weights, erb_weights, erb_density,
                       weighted_rms, effective_steps, plot_fit)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib import ticker
model=EqModel.load('results/session3/eq_model.json'); A=model.per_step_matrix()
base=Response.from_csv('results/session4/baseline_pooled_18.csv')
names={'mazda_neutral':'neutral','mazda_warm':'warm','mazda_bass':'bass-forward'}
wl, we = default_weights(G), erb_weights(G)
def err(db, tgt, w):
    r=np.asarray(db)-tgt.db; return weighted_rms(r-np.sum(w*r)/np.sum(w), w)
R={}
for t in names:
    tgt=load_target(t)
    a=fit_eq(base,model,tgt,max_boost=4)
    b=fit_eq(base,model,tgt,weights=we,max_boost=4,erb_weighted=True)
    json.dump(b.to_dict(), open(f'results/session4/three_erb/fit_{t}_erb.json','w'), indent=1)
    plot_fit(b, f'results/session4/three_erb/fit_{t}_erb.png', f'target: {t} (ERB-weighted fit)')
    R[t]=(a,b,tgt)

print("SETTINGS, bands 1-13\n")
for t,(a,b,tgt) in R.items():
    d=b.steps_int-a.steps_int
    print(f"{names[t]:12} log  {' '.join(f'{v:+d}' for v in a.steps_int)}")
    print(f"{'':12} ERB  {' '.join(f'{v:+d}' for v in b.steps_int)}")
    print(f"{'':12} diff {' '.join((f'{v:+d}' if v else '  ') for v in d)}   ({int(np.sum(d!=0))} bands move, max {np.abs(d).max()})\n")

print("ERROR, each set of settings judged both ways (dB)\n")
print(f"{'voicing':12} {'settings':10} {'equal/octave':>13} {'auditory bw':>13}")
for t,(a,b,tgt) in R.items():
    for lbl,r in (("log-opt",a),("ERB-opt",b)):
        p=r.predicted_int.db
        print(f"{names[t]:12} {lbl:10} {err(p,r.target,wl):13.2f} {err(p,r.target,we):13.2f}")
    print()

print("COST OF USING THE OTHER WEIGHTING (dB, positive = worse)\n")
print(f"{'voicing':12} {'ERB-opt judged equal/oct':>26} {'log-opt judged auditory':>25}")
for t,(a,b,tgt) in R.items():
    c1=err(b.predicted_int.db,b.target,wl)-err(a.predicted_int.db,a.target,wl)
    c2=err(a.predicted_int.db,a.target,we)-err(b.predicted_int.db,b.target,we)
    print(f"{names[t]:12} {c1:+26.2f} {c2:+25.2f}")

print("\nWHERE THE TWO PREDICTIONS DIFFER (dB, ERB-opt minus log-opt)\n")
print(f"{'voicing':12}" + "".join(f"{f:>8g}" for f in (40,63,100,160,250,500,1000,2000,4000,8000,16000)))
for t,(a,b,tgt) in R.items():
    d=b.predicted_int.db-a.predicted_int.db
    print(f"{names[t]:12}" + "".join(f"{d[np.argmin(np.abs(G-f))]:+8.1f}" for f in (40,63,100,160,250,500,1000,2000,4000,8000,16000)))

# plot
def setup(ax,title,yl="dB"):
    ax.set_xlim(20,20000); ax.set_xticks([20,50,100,200,500,1000,2000,5000,10000,20000])
    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda v,_: f"{v/1000:g}k" if v>=1000 else f"{v:g}"))
    ax.grid(True,which="both",color="#e6e5e1",lw=0.6); ax.set_title(title,loc="left"); ax.set_ylabel(yl)
    for s in ("top","right"): ax.spines[s].set_visible(False)
cols={'mazda_neutral':'#2a78d6','mazda_warm':'#eb6834','mazda_bass':'#1baf7a'}
fig,axs=plt.subplots(2,2,figsize=(16,9))
ax=axs[0,0]
ax.semilogx(G, wl, 'k--', lw=1.5, label="equal per octave (current)")
ax.semilogx(G, we, 'k', lw=2, label="scaled by auditory bandwidth")
ax.semilogx(G, erb_density(G), color='#8a8985', lw=1, ls=':', label="erb_density = f/(f+228.8)")
ax.set_ylim(0,1.1); ax.legend(frameon=False,fontsize=8); setup(ax,"The two weightings","weight")
ax=axs[0,1]
for t,(a,b,tgt) in R.items():
    ax.semilogx(G, b.predicted_int.db-a.predicted_int.db, color=cols[t], lw=1.6, label=names[t])
ax.axhline(0,color='k',lw=0.5); ax.set_ylim(-3,3); ax.legend(frameon=False,fontsize=8)
setup(ax,"Predicted response: ERB-optimised minus log-optimised")
ax=axs[1,0]
for t,(a,b,tgt) in R.items():
    r=b.predicted_int.db-b.target.db; r-=np.sum(we*r)/np.sum(we)
    ax.semilogx(G, r, color=cols[t], lw=1.6, label=f"{names[t]} ERB-opt")
    r2=a.predicted_int.db-a.target.db; r2-=np.sum(we*r2)/np.sum(we)
    ax.semilogx(G, r2, color=cols[t], lw=0.9, ls='--', alpha=0.7)
ax.fill_between([20,20000],-2,2,color='#e6e5e1',alpha=0.5); ax.axhline(0,color='k',lw=0.5)
ax.set_ylim(-10,8); ax.legend(frameon=False,fontsize=8); setup(ax,"Residual vs target (dashed = log-optimised)")
ax=axs[1,1]
x=np.arange(13); wd=0.26
for i,(t,(a,b,tgt)) in enumerate(R.items()):
    ax.bar(x+(i-1)*wd, b.steps_int-a.steps_int, wd, color=cols[t], label=names[t])
ax.set_xticks(x); ax.set_xticklabels([f"{i+1}\n{l:g}" for i,l in enumerate([40,63,100,160,250,500,1000,1600,2500,4000,6300,10000,16000])],fontsize=8)
ax.set_ylim(-1,5); ax.axhline(0,color="k",lw=0.5); ax.grid(True,axis="y",color="#e6e5e1",lw=0.6)
ax.legend(frameon=False,fontsize=8); ax.set_title("Step change, ERB-optimised minus log-optimised",loc='left'); ax.set_ylabel("steps")
for s in ("top","right"): ax.spines[s].set_visible(False)
fig.tight_layout(); fig.savefig('results/session4/three_erb/comparison.png',dpi=110)
print("\nwrote results/session4/three_erb/comparison.png")
