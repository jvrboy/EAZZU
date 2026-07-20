"""Spectrogram & Analysis Visualizer."""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional

class VizConfig:
    def __init__(self, viz_type="spectrum", fft_size=2048, smoothing=0.8, color="#6366f1", waterfall=False): self.type=viz_type; self.fft_size=fft_size; self.smoothing=smoothing; self.color=color; self.waterfall=waterfall
    def to_dict(self): return {k:v for k,v in vars(self).items()}

DEFAULT_VIZ = VizConfig()

class Visualizer:
    def __init__(self, config=None): self.config=config or VizConfig(); self._loudness_history=[]; self._max_history=200
    def compute_spectrum(self, samples):
        n=min(self.config.fft_size,len(samples))
        if n==0: return {"bars":[],"size":0}
        mags=[0.0]*(n//2)
        for k in range(n//2):
            re=sum(samples[j]*math.cos(-2*math.pi*k*j/n) for j in range(n)); im=sum(samples[j]*math.sin(-2*math.pi*k*j/n) for j in range(n)); mags[k]=math.sqrt(re*re+im*im)
        return {"bars":mags[:128],"size":128}
    def compute_oscilloscope(self, samples): return {"waveform":samples[:min(self.config.fft_size,len(samples))]}
    def compute_loudness(self, samples):
        if not samples: return {"db":-70,"history":[]}
        rms=math.sqrt(sum(s*s for s in samples)/len(samples)); db=20*math.log10(max(rms,0.0001))
        self._loudness_history.append(db)
        if len(self._loudness_history)>self._max_history: self._loudness_history.pop(0)
        return {"db":db,"history":list(self._loudness_history)}
    def render(self, samples):
        if self.config.type=="spectrum": return self.compute_spectrum(samples)
        elif self.config.type=="oscilloscope": return self.compute_oscilloscope(samples)
        elif self.config.type=="loudness": return self.compute_loudness(samples)
        return {}
