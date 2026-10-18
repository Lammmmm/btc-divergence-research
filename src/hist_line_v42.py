"""Display-only v4.2 specification. Formal event engine is not changed or called here."""
from dataclasses import dataclass
import math
from hist_progress_v4 import clear_line

def score(z):
    return 100/(1+math.exp(-max(-20.,min(20.,z))))

def formation(price,hist,pivot_price,pivot_hist,side,atr,hvol):
    pp=score(side*(pivot_price-price)/atr)
    hp=score(side*(hist-pivot_hist)/hvol)
    return min(99.,pp,hp),pp,hp

def scale(short,long,tick=.1):
    return max(short if math.isfinite(short) else tick, .5*long if math.isfinite(long) else tick,tick)

@dataclass
class Candidate:
    ref:int=-1
    atr:float=.1
    vol:float=.1
    price_met:bool=False
    hist_met:bool=False
    bad:int=0

    def step(self,c,h,t,pivots,side,aa,vol,enabled=True,confirmed=True):
        eligible=[p for p in pivots[:10] if 5<t-p<=100]
        newest=eligible[0] if eligible else -1
        ref=-1 if not enabled else self.ref if self.ref in eligible else newest
        if enabled and self.bad>=3 and newest!=-1 and newest!=ref:ref=newest
        changed=ref!=self.ref
        a,v=(aa,vol) if changed else (self.atr,self.vol)
        pm,hm=(False,False) if changed else (self.price_met,self.hist_met)
        bad=0 if changed else self.bad
        row=dict(ref=ref,changed=changed,score=None,price_pct=None,hist_pct=None,broken=False,clear=False,atr=a,vol=v,bad=bad)
        if ref!=-1:
            value,pp,hp=formation(c[t],h[t],c[ref],h[ref],side,a,v)
            mp=side*(c[ref]-c[t]);mh=side*(h[t]-h[ref])
            clear=clear_line(c,h,t,ref,side==1)
            broken=not clear or (pm and mp<=0) or (hm and mh<=0)
            row.update(score=value,price_pct=pp,hist_pct=hp,clear=clear,broken=broken,pivot_price=float(c[ref]),pivot_hist=float(h[ref]))
            pm=pm or mp>0;hm=hm or mh>0;bad=bad+1 if broken else 0
        else:bad=0
        row['bad']=bad
        if confirmed:self.ref,self.atr,self.vol,self.price_met,self.hist_met,self.bad=ref,a,v,pm,hm,bad
        return row

@dataclass
class Display:
    focus:int=0
    challenger:int=0
    streak:int=0
    event:int=0
    context:tuple|None=None

    def step(self,r,confirmed=True):
        b,t=r['bull'],r['bear'];bs=b['score'] or 0.;ts=t['score'] or 0.
        active=r['active_direction'];forming=not active and not r['success'] and not r['failure']
        focus,challenger,streak,event=self.focus,self.challenger,self.streak,self.event
        if r['start']:event+=1
        if active:focus=active;challenger=0;streak=0
        elif forming:
            if focus==0 or (b if focus==1 else t)['ref']==-1:
                focus=0 if b['ref']==t['ref']==-1 else -1 if b['ref']==-1 else 1 if t['ref']==-1 else 1 if bs>=ts else -1
                challenger=0;streak=0
            else:
                other=-focus
                advantage=(ts-bs if focus==1 else bs-ts)>15
                exists=(t if focus==1 else b)['ref']!=-1
                if confirmed:
                    streak=streak+1 if advantage and exists and challenger==other else 1 if advantage and exists else 0
                    challenger=other if advantage and exists else 0
                    if streak>=3:focus=other;streak=0;challenger=0
        else:challenger=0;streak=0
        cand=b if focus==1 else t
        phase=2 if active else 3 if r['success'] or r['failure'] else 1 if focus and cand['ref']!=-1 else 0
        context=(2,event) if phase in (2,3) else (1,focus,cand['ref']) if phase==1 else (0,)
        seam=context!=self.context
        value=r['structure_progress'] if active else 100. if r['success'] else 0. if r['failure'] else cand['score'] if phase==1 else None
        warning=bool(r['invalid_touch'] or r['failure'] or (phase==1 and cand['broken']))
        out=dict(time=r['time'],value=value,phase=phase,focus=focus,ref=cand['ref'] if phase==1 else None,seam=seam,warning=warning,context=list(context))
        if confirmed:self.focus,self.challenger,self.streak,self.event,self.context=focus,challenger,streak,event,context
        return out
