"""Extended Effects Pack 2 — 5 more professional audio effects."""
from __future__ import annotations
import math, random
from typing import Any, Dict, List, Optional

EXTENDED_FX2_TYPES = ["ring-modulator","frequency-shifter","resonator","chorus-ensemble","phaser-stages"]

DEFAULT_PARAMS2 = {
    "ring-modulator": {"frequency":100,"depth":1.0,"mix":0.5},
    "frequency-shifter": {"shift":200,"feedback":0.3,"mix":0.5},
    "resonator": {"frequency":440,"resonance":10,"decay":0.5,"mix":0.5},
    "chorus-ensemble": {"rate":0.5,"depth":0.3,"voices":3,"width":0.8,"mix":0.5},
    "phaser-stages": {"rate":0.3,"depth":0.7,"stages":6,"feedback":0.3,"mix":0.5},
}

class ExtendedFX2Config:
    def __init__(self, fx_type, enabled=False, mix=1.0, params=None): self.type=fx_type; self.enabled=enabled; self.mix=mix; self.params=params or DEFAULT_PARAMS2.get(fx_type,{}).copy()
    def to_dict(self): return {"type":self.type,"enabled":self.enabled,"mix":self.mix,"params":self.params}

class ExtendedFX2:
    def __init__(self): self.chain=[]
    def add(self, fx_type, enabled=False, mix=1.0, params=None): c=ExtendedFX2Config(fx_type,enabled,mix,params); self.chain.append(c); return c
    def process(self, samples, sample_rate=44100):
        out=list(samples)
        for cfg in self.chain:
            if not cfg.enabled: continue
            wet=self._apply(out,cfg,sample_rate); out=[d*(1-cfg.mix)+w*cfg.mix for d,w in zip(out,wet)]
        return out
    def _apply(self, samples, cfg, sr):
        p=cfg.params
        if cfg.type=="ring-modulator":
            freq=p.get("frequency",100); return [s*math.sin(2*math.pi*freq*i/sr) for i,s in enumerate(samples)]
        elif cfg.type=="chorus-ensemble":
            voices=int(p.get("voices",3)); rate=p.get("rate",0.5); depth=p.get("depth",0.3); out=[0.0]*len(samples)
            for v in range(voices):
                for i in range(len(samples)):
                    lfo=math.sin(2*math.pi*rate*(1+v*0.1)*i/sr); delay=int((0.02+lfo*depth*0.05)*sr)
                    out[i]+=samples[max(0,i-delay)]
            return [s/max(voices,1) for s in out]
        return list(samples)
    def get_state(self): return {"chain":[c.to_dict() for c in self.chain]}
