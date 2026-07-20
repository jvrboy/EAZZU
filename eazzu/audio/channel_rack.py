"""Channel Rack — step sequencer with per-channel samples, pitch, pan, gain, FX."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

class ChannelRackStep:
    def __init__(self): self.active=False; self.velocity=100; self.pitch=0; self.pan=0.0; self.gain=1.0; self.retrigger=1; self.reverse=False
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class ChannelRackChannel:
    def __init__(self, name, steps=16):
        self.id=str(uuid.uuid4()); self.name=name; self.color="#3b82f6"; self.sample_id=None
        self.volume=0.8; self.pan=0.0; self.muted=False; self.solo=False
        self.steps=[ChannelRackStep() for _ in range(steps)]
        self.reverb=0.0; self.delay=0.0; self.filter=1.0; self.filter_freq=20000.0; self.distortion=0.0
        self.swing=0.0; self.humanize=0.0; self.midi_channel=0; self.output_bus="master"
    def to_dict(self): return {"id":self.id,"name":self.name,"color":self.color,"sampleId":self.sample_id,"volume":self.volume,"pan":self.pan,"muted":self.muted,"solo":self.solo,"steps":[s.to_dict() for s in self.steps],"reverb":self.reverb,"delay":self.delay,"filter":self.filter}

class ChannelRackState:
    def __init__(self): self.id=str(uuid.uuid4()); self.name="Pattern 1"; self.bpm=120; self.steps=16; self.steps_per_beat=4; self.channels=[]; self.playing=False; self.current_step=0; self.swing=0.0; self.master_volume=0.8; self.loop_mode=True; self.loop_start=0; self.loop_end=15
    def to_dict(self): return {"id":self.id,"name":self.name,"bpm":self.bpm,"steps":self.steps,"stepsPerBeat":self.steps_per_beat,"channels":[c.to_dict() for c in self.channels],"playing":self.playing,"currentStep":self.current_step,"swing":self.swing,"masterVolume":self.master_volume}

def create_default_channel_rack():
    s=ChannelRackState(); s.channels=[ChannelRackChannel(n, s.steps) for n in ["Kick","Snare","Hi-Hat","Clap","Perc","Bass","Synth","FX"]]; return s

class ChannelRack:
    def __init__(self): self.state=create_default_channel_rack()
    def toggle_step(self, cid, si):
        for ch in self.state.channels:
            if ch.id==cid and 0<=si<len(ch.steps): ch.steps[si].active = not ch.steps[si].active; return {"channelId":cid,"step":si,"active":ch.steps[si].active}
        return {"error":"not_found"}
    def get_state(self): return self.state.to_dict()
