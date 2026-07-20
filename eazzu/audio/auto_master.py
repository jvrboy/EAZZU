"""Auto Mixing & Mastering Engine."""
from __future__ import annotations
import math, time
from typing import Any, Dict, List

class MasterPreset:
    def __init__(self, pid, name, desc, target_lufs, true_peak, comp_ratio, comp_thresh, lim_ceiling, exciter, stereo_w, bass, air):
        self.id=pid; self.name=name; self.description=desc; self.target_lufs=target_lufs; self.true_peak=true_peak
        self.compressor_ratio=comp_ratio; self.compressor_threshold=comp_thresh; self.limiter_ceiling=lim_ceiling
        self.exciter_amount=exciter; self.stereo_wideness=stereo_w; self.bass_enhance=bass; self.air_boost=air
    def to_dict(self): return {k:v for k,v in vars(self).items()}

MASTER_PRESETS = [
    MasterPreset("transparent","Transparent","Subtle glue.",-16,-1.5,1.5,-18,-1.5,0.1,1.05,0.1,0.15),
    MasterPreset("streaming","Streaming","Loud, punchy.",-14,-1.0,3,-14,-1.0,0.35,1.2,0.3,0.4),
    MasterPreset("club","Club","Maximum loudness.",-9,-0.5,4,-10,-0.5,0.5,1.4,0.6,0.3),
    MasterPreset("vinyl","Vinyl","Warm, analog.",-18,-2.0,2,-16,-2.0,0.2,0.9,0.2,0.1),
    MasterPreset("podcast","Podcast","Voice-optimized.",-16,-1.5,4,-18,-1.5,0.15,1.0,0.05,0.5),
    MasterPreset("lofi","Lo-Fi","Soft, tape-saturated.",-14,-1.0,2,-12,-1.0,0.25,1.1,0.4,0.2),
]

def _estimate_lufs(s): return 20*math.log10(max(1e-10, math.sqrt(sum(x*x for x in s[::256])/max(1,len(s)//256)))) + 0.691 if s else -70.0
def _measure_peak(s): return 20*math.log10(max(1e-10, max(abs(x) for x in s))) if s else -70.0

def auto_master(samples, preset, sample_rate=44100):
    start=time.time(); processed=list(samples)
    input_lufs=_estimate_lufs(samples); gain_db=preset.target_lufs-input_lufs; gain=10**(gain_db/20)
    processed=[s*gain for s in processed]
    return {"samples":len(processed),"presetId":preset.id,"measuredLufs":round(_estimate_lufs(processed),1),"measuredPeak":round(_measure_peak(processed),1),"gainReduction":round(gain_db,1),"durationMs":int((time.time()-start)*1000)}

def auto_mix(stems, preset, sample_rate=44100):
    if not stems: return {"error":"no_stems"}
    max_len=max(len(s.get("samples",[])) for s in stems); mixed=[0.0]*max_len
    gf={"vocals":0.9,"drums":0.8,"bass":0.75,"other":0.7}
    for stem in stems:
        g=gf.get(stem.get("type",""),0.7); buf=stem.get("samples",[])
        for i in range(min(len(buf),max_len)): mixed[i]+=buf[i]*g
    return auto_master(mixed, preset, sample_rate)
