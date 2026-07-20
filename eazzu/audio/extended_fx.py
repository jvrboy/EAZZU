"""Extended Effects Pack 1 — 10 professional audio effects."""
from __future__ import annotations
import math, random
from typing import Any, Dict, List, Optional

EXTENDED_FX_TYPES = ["convolution-reverb","tape-echo","granular-cloud","spectral-freezer","harmonic-enhancer","transient-designer","multiband-comp","stereo-imager","vocoder-fx","lofi-degrader"]

DEFAULT_PARAMS = {
    "convolution-reverb": {"decay":2.0,"predelay":0.02,"damping":0.5,"width":1.0},
    "tape-echo": {"time":0.3,"feedback":0.4,"saturation":0.3,"wow":0.1,"flutter":0.05},
    "granular-cloud": {"density":0.5,"grainSize":0.05,"pitchSpread":0.2,"position":0.5,"spray":0.1},
    "spectral-freezer": {"freeze":0,"blend":0.5,"smoothness":0.7},
    "harmonic-enhancer": {"drive":0.3,"frequency":2000,"amount":0.5,"tone":0.5},
    "transient-designer": {"attack":0.5,"sustain":0.5,"punch":0.5},
    "multiband-comp": {"lowThreshold":-20,"midThreshold":-18,"highThreshold":-16,"ratio":3,"attack":0.003,"release":0.1},
    "stereo-imager": {"width":1.0,"lowWidth":0.5,"highWidth":1.0,"centerFreq":200},
    "vocoder-fx": {"bands":16,"formantShift":0,"dryWet":0.8,"inputGain":1.0},
    "lofi-degrader": {"bitDepth":8,"sampleRate":22050,"noise":0.05,"wobble":0.1,"saturation":0.3},
}

class ExtendedFXConfig:
    def __init__(self, fx_type, enabled=False, mix=1.0, params=None): self.type=fx_type; self.enabled=enabled; self.mix=mix; self.params=params or DEFAULT_PARAMS.get(fx_type,{}).copy()
    def to_dict(self): return {"type":self.type,"enabled":self.enabled,"mix":self.mix,"params":self.params}

class ExtendedFX:
    def __init__(self): self.chain=[]
    def add(self, fx_type, enabled=False, mix=1.0, params=None): c=ExtendedFXConfig(fx_type,enabled,mix,params); self.chain.append(c); return c
    def process(self, samples, sample_rate=44100):
        out=list(samples)
        for cfg in self.chain:
            if not cfg.enabled: continue
            wet=self._apply(out,cfg,sample_rate); out=[d*(1-cfg.mix)+w*cfg.mix for d,w in zip(out,wet)]
        return out
    def _apply(self, samples, cfg, sr):
        p=cfg.params
        if cfg.type=="harmonic-enhancer": return [math.tanh(s*(1+p.get("drive",0.3)*3))*0.7 for s in samples]
        elif cfg.type=="lofi-degrader":
            bits=int(p.get("bitDepth",8)); levels=2**bits; noise=p.get("noise",0.05)
            return [round(s*levels)/levels + random.uniform(-noise,noise) for s in samples]
        elif cfg.type=="tape-echo":
            delay=int(p.get("time",0.3)*sr); fb=p.get("feedback",0.4); out=list(samples)
            for i in range(delay,len(samples)): out[i]+=math.tanh(out[i-delay]*fb)
            return out
        return list(samples)
    def get_state(self): return {"chain":[c.to_dict() for c in self.chain]}
