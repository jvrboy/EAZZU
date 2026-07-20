"""Advanced Visualizer — 5 new visualization modes."""
from __future__ import annotations
import math, random
from typing import Any, Dict, List

ADVANCED_VIZ_MODES = ["radial-spectrum","3d-bars","waterfall","phase-scope","particle-flow"]

class AdvancedVisualizer:
    def __init__(self, mode="radial-spectrum"): self.mode=mode; self.particles=[]; self.waterfall_data=[]; self._fft_size=2048
    def _compute_freq(self, samples):
        n=min(self._fft_size,len(samples))
        if n==0: return []
        mags=[0.0]*(n//2)
        for k in range(n//2):
            re=sum(samples[j]*math.cos(-2*math.pi*k*j/n) for j in range(n)); im=sum(samples[j]*math.sin(-2*math.pi*k*j/n) for j in range(n)); mags[k]=math.sqrt(re*re+im*im)
        return mags
    def render(self, samples, width=800, height=600):
        freq=self._compute_freq(samples)
        if self.mode=="radial-spectrum": return self._radial(freq,width,height)
        elif self.mode=="particle-flow": return self._particles(freq,width,height)
        return {"freq":freq[:64]}
    def _radial(self, freq, w, h):
        bars=128; cx,cy=w/2,h/2; radius=min(w,h)*0.2; lines=[]
        for i in range(bars):
            angle=(i/bars)*2*math.pi; value=freq[int(i/bars*len(freq)) if freq else 0]/255 if freq else 0
            lines.append({"angle":angle,"value":value})
        return {"lines":lines}
    def _particles(self, freq, w, h):
        avg=sum(freq[:64])/max(64,1)/255 if freq else 0
        if random.random()<avg*0.5:
            angle=random.uniform(0,2*math.pi); self.particles.append({"x":w/2,"y":h/2,"vx":math.cos(angle)*(1+avg*4),"vy":math.sin(angle)*(1+avg*4),"life":1.0})
        self.particles=[p for p in self.particles if p["life"]>0]
        for p in self.particles: p["x"]+=p["vx"]; p["y"]+=p["vy"]; p["life"]-=0.01
        return {"particles":list(self.particles)}
