"""LFO & Modulation Matrix — assignable modulators for any audio parameter."""
from __future__ import annotations
import math, time, uuid
from typing import Any, Dict, List, Optional

class LFOParams:
    def __init__(self, rate=2.0, depth=0.5, waveform="sine", free_running=True): self.rate=rate; self.depth=depth; self.waveform=waveform; self.free_running=free_running
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class EnvelopeParams:
    def __init__(self, attack=0.01, decay=0.2, sustain=0.7, release=0.3, depth=0.5): self.attack=attack; self.decay=decay; self.sustain=sustain; self.release=release; self.depth=depth
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class ModulationRouting:
    def __init__(self, source, target, depth=0.5, enabled=True): self.id=f"{source}-{target}-{uuid.uuid4().hex[:8]}"; self.source=source; self.target=target; self.depth=depth; self.enabled=enabled
    def to_dict(self): return {"id":self.id,"source":self.source,"target":self.target,"depth":self.depth,"enabled":self.enabled}

class ModulationState:
    def __init__(self): self.lfos={"lfo1":LFOParams(2,0.5,"sine"),"lfo2":LFOParams(0.5,0.3,"triangle"),"lfo3":LFOParams(5,0.2,"sawtooth"),"lfo4":LFOParams(0.1,0.4,"sine")}; self.envelopes={"env1":EnvelopeParams(),"env2":EnvelopeParams(0.5,1.0,0.5,2.0,0.3)}; self.routings=[]; self.active=False
    def to_dict(self): return {"lfos":{k:v.to_dict() for k,v in self.lfos.items()},"envelopes":{k:v.to_dict() for k,v in self.envelopes.items()},"routings":[r.to_dict() for r in self.routings],"active":self.active}

DEFAULT_MODULATION = ModulationState()

class ModulationEngine:
    def __init__(self, state=None): self.state=state or ModulationState(); self._step=0; self._start_time=0.0
    def start(self): self.state.active=True; self._start_time=time.time()
    def stop(self): self.state.active=False
    def add_routing(self, source, target, depth): r=ModulationRouting(source,target,depth); self.state.routings.append(r); return r
    def remove_routing(self, rid): self.state.routings=[r for r in self.state.routings if r.id!=rid]
    def get_modulation_values(self, t):
        vals={}
        for lid,lfo in self.state.lfos.items():
            phase = t*lfo.rate*2*math.pi
            if lfo.waveform=="sine": v=math.sin(phase)
            elif lfo.waveform=="square": v=1.0 if math.sin(phase)>=0 else -1.0
            elif lfo.waveform=="sawtooth": v=2.0*((t*lfo.rate)%1.0)-1.0
            elif lfo.waveform=="triangle": v=2.0*abs(2.0*((t*lfo.rate)%1.0)-1.0)-1.0
            else: v=0.0
            vals[lid]=v*lfo.depth
        vals["step1"]=(self._step%16)/16.0; vals["random1"]=(hash(("rand",self._step))%2000-1000)/1000.0
        return vals
    def apply_modulations(self, t):
        mv=self.get_modulation_values(t); out={}
        for r in self.state.routings:
            if r.enabled: out[r.target]=out.get(r.target,0)+mv.get(r.source,0)*r.depth
        return out
    def tick(self): self._step+=1
    def get_state(self): return self.state.to_dict()
