"""Sample Packs — sample pack management."""
from __future__ import annotations
import math, time, uuid
from typing import Any, Dict, List, Optional

SAMPLE_CATEGORIES = [{"id":"kick","name":"Kicks"},{"id":"snare","name":"Snares"},{"id":"hihat","name":"Hi-Hats"},{"id":"bass","name":"Bass"},{"id":"synth","name":"Synths"},{"id":"vocal","name":"Vocals"},{"id":"fx","name":"FX"}]

class Sample:
    def __init__(self, name, pack_id, category, samples=None, **kw): self.id=str(uuid.uuid4()); self.name=name; self.pack_id=pack_id; self.category=category; self.samples=samples; self.tags=kw.get("tags",[]); self.bpm=kw.get("bpm"); self.key=kw.get("key"); self.waveform=[]
    def to_dict(self): return {"id":self.id,"name":self.name,"packId":self.pack_id,"category":self.category,"hasSamples":self.samples is not None}

class SamplePack:
    def __init__(self, name, desc="", category="", source="builtin"): self.id=str(uuid.uuid4()); self.name=name; self.description=desc; self.category=category; self.samples=[]; self.created_at=time.time(); self.source=source
    def to_dict(self): return {"id":self.id,"name":self.name,"samples":[s.to_dict() for s in self.samples],"source":self.source}

def _make_tone(freq, dur, sr=44100, decay=0.3): return [math.sin(2*math.pi*freq*i/sr)*math.exp(-i/(decay*sr)) for i in range(int(dur*sr))]

class SamplePackManager:
    def __init__(self): self.packs=[]; self._create_builtin()
    def _create_builtin(self):
        p=SamplePack("Builtin Sounds","Default synthesized samples")
        for name,cat,freq in [("Kick","kick",60),("Snare","snare",200),("Hi-Hat","hihat",8000),("Bass","bass",80),("Synth","synth",440)]:
            s=Sample(name,p.id,cat,samples=_make_tone(freq,0.3)); s.duration_sec=0.3; p.samples.append(s)
        self.packs.append(p)
    def add_pack(self, name, desc="", category=""): p=SamplePack(name,desc,category,"local"); self.packs.append(p); return p
    def get_all_samples(self): return [s for p in self.packs for s in p.samples]
    def get_state(self): return {"packs":[p.to_dict() for p in self.packs]}
