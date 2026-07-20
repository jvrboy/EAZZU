"""Advanced Pitch & Formant Processing."""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional

class PitcherConfig:
    def __init__(self, pitch_ratio=1.0, pitch_shift=0.0, formant_shift=0.0, mix=1.0, feedback=0.0, window_size=40.0, crossfade=0.5, stereo_width=1.0, detune=0.0): self.pitch_ratio=pitch_ratio; self.pitch_shift=pitch_shift; self.formant_shift=formant_shift; self.mix=mix; self.feedback=feedback; self.window_size=window_size; self.crossfade=crossfade; self.stereo_width=stereo_width; self.detune=detune
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class SoundPitcher:
    def __init__(self, config=None, sample_rate=44100): self.config=config or PitcherConfig(); self.sample_rate=sample_rate
    def process(self, samples):
        cfg=self.config; ratio=cfg.pitch_ratio*(2**(cfg.pitch_shift/12)); n=len(samples); out=[0.0]*n
        gs=int(cfg.window_size/1000*self.sample_rate); gs=max(gs,256); hop=max(int(gs*(1-cfg.crossfade)),1)
        for pos in range(0, n-gs, hop):
            for i in range(gs):
                src=int((pos+i)/ratio)
                if src<n: out[pos+i]+=samples[src]*math.sin(math.pi*i/gs)
        return {"samples":out,"ratio":ratio,"grainSize":gs}
    def get_state(self): return self.config.to_dict()
