"""One-Shot Sampler — record, load, and trigger one-shot samples."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

class OneShotPad:
    def __init__(self, index):
        keys=["a","s","d","f","g","h","j","k","l"]
        self.id=str(uuid.uuid4()); self.name=f"Pad {index+1}"; self.buffer=None; self.key=keys[index%len(keys)]; self.midi_note=36+index
        self.pitch=0.0; self.pan=0.0; self.gain=1.0; self.reverse=False; self.start_offset=0.0; self.end_offset=1.0
        self.loop_mode=False; self.reverb=0.0; self.delay=0.0; self.filter=1.0; self.duration_sec=0.0; self.waveform=[]
    def to_dict(self): return {"id":self.id,"name":self.name,"key":self.key,"midiNote":self.midi_note,"pitch":self.pitch,"gain":self.gain,"hasBuffer":self.buffer is not None}

class OneShotSampler:
    def __init__(self, pad_count=16): self.pads=[OneShotPad(i) for i in range(pad_count)]; self.master_volume=0.8
    def get_pad(self, pid):
        for p in self.pads:
            if p.id==pid: return p
    def assign_buffer(self, pid, buf, sample_rate=44100):
        p=self.get_pad(pid)
        if p: p.buffer=buf; p.duration_sec=len(buf)/sample_rate
    def render_pad(self, pid, sample_rate=44100):
        p=self.get_pad(pid)
        if not p or not p.buffer: return []
        buf=p.buffer
        if p.start_offset>0 or p.end_offset<1:
            si=int(len(buf)*p.start_offset); ei=int(len(buf)*p.end_offset); buf=buf[si:ei]
        if p.reverse: buf=list(reversed(buf))
        pr=2**(p.pitch/12); return [buf[int(i*pr)] for i in range(int(len(buf)/max(pr,0.01))) if int(i*pr)<len(buf)]
    def get_state(self): return {"pads":[p.to_dict() for p in self.pads],"masterVolume":self.master_volume}
