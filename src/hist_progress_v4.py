"""Causal offline specification for v4 display; not a Pine interpreter."""
from dataclasses import dataclass
import math

def proximity(margin,scale,band=1):
    return max(0.,min(100.,100*(1+margin/(scale*band))))

def formation(price,hist,pivot_price,pivot_hist,side,atr,hvol,price_band=1,hist_band=1):
    p=proximity(side*(pivot_price-price),atr,price_band)
    h=proximity(side*(hist-pivot_hist),hvol,hist_band)
    return min(99.,p,h),p,h

def structure(price,invalid,target):
    return max(0.,min(100.,100*(price-invalid)/(target-invalid)))

def touched(side,low,high,invalid):
    return low<=invalid if side==1 else high>=invalid

def clear_line(c,h,t,p,bull):
    sh=(h[t]-h[p])/(t-p);sp=(c[t]-c[p])/(t-p)
    vh=h[t]-sh;vp=c[t]-sp
    for y in range(1,t-p):
        if (h[t-y]<vh or c[t-y]<vp) if bull else (h[t-y]>vh or c[t-y]>vp):return False
        vh-=sh;vp-=sp
    return True

@dataclass
class Candidate:
    ref:int=-1
    atr:float=0.
    vol:float=0.
    price_was_met:bool=False
    hist_was_met:bool=False

    def step(self,c,h,t,positions,side,atr_prior,vol_prior,enabled=True,confirmed=True,tick=.1):
        chosen=next((p for p in positions[:10] if 5<t-p<=100 and math.isfinite(h[p])),-1) if enabled else -1
        changed=chosen!=self.ref;lost=chosen==-1 and self.ref!=-1
        # Local state is returned without committing during live executions (Pine rollback).
        a=max(atr_prior if math.isfinite(atr_prior) else tick,tick) if changed else self.atr
        v=max(vol_prior if math.isfinite(vol_prior) else tick,tick) if changed else self.vol
        pw=False if changed else self.price_was_met;hw=False if changed else self.hist_was_met
        row=dict(ref=chosen,changed=changed,lost=lost,score=None,price_pct=None,hist_pct=None,broken=False,clear=False,atr=a,vol=v)
        if chosen!=-1:
            score,pp,hp=formation(c[t],h[t],c[chosen],h[chosen],side,a,v)
            pm=side*(c[chosen]-c[t]);hm=side*(h[t]-h[chosen])
            clear=clear_line(c,h,t,chosen,side==1)
            broken=not clear or (pw and pm<=0) or (hw and hm<=0)
            row.update(score=score,price_pct=pp,hist_pct=hp,broken=broken,clear=clear,pivot_price=float(c[chosen]),pivot_hist=float(h[chosen]))
            pw=pw or pm>0;hw=hw or hm>0
        if confirmed:self.ref,self.atr,self.vol,self.price_was_met,self.hist_was_met=chosen,a,v,pw,hw
        return row
