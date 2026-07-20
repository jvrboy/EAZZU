"""Advanced Mixing Console — professional channel strips, buses, sends, master."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

class EQBand:
    def __init__(self, et="peaking", freq=1000.0, gain=0.0, q=1.0): self.id=str(uuid.uuid4()); self.type=et; self.frequency=freq; self.gain=gain; self.q=q; self.enabled=True
    def to_dict(self): return {"id":self.id,"type":self.type,"frequency":self.frequency,"gain":self.gain,"q":self.q,"enabled":self.enabled}

class CompressorSettings:
    def __init__(self): self.enabled=False; self.threshold=-18.0; self.ratio=3.0; self.attack=0.003; self.release=0.1; self.knee=6.0; self.makeup_gain=0.0; self.sidechain_source=None
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class ChannelStrip:
    def __init__(self, name, ct="audio"):
        self.id=str(uuid.uuid4()); self.name=name; self.type=ct; self.input_gain=1.0; self.volume=0.8; self.pan=0.0
        self.mute=False; self.solo=False; self.eq=[EQBand("highpass",80,0,0.7),EQBand("peaking",250,0,1.0),EQBand("peaking",2500,0,0.7),EQBand("highshelf",8000,0,0.7)]
        self.compressor=CompressorSettings(); self.sends=[]; self.inserts=[]; self.output_bus="master"; self.color="#3b82f6"
        self.meter_level=0.0; self.meter_peak=0.0; self.meter_rms=0.0; self.armed=False; self.phase_invert=False; self.stereo_width=1.0
    def to_dict(self): return {"id":self.id,"name":self.name,"type":self.type,"volume":self.volume,"pan":self.pan,"mute":self.mute,"solo":self.solo,"eq":[e.to_dict() for e in self.eq],"compressor":self.compressor.to_dict(),"outputBus":self.output_bus,"color":self.color,"meterLevel":self.meter_level}

class MixingConsole:
    def __init__(self):
        self.channels=[ChannelStrip("Kick","drum"),ChannelStrip("Snare","drum"),ChannelStrip("Hat","drum"),ChannelStrip("Bass","instrument"),ChannelStrip("Lead","instrument"),ChannelStrip("Pad","instrument"),ChannelStrip("Vocal","audio"),ChannelStrip("FX","fx")]
        self.buses=[]; self.master={"volume":0.9}; self.selected_channel_id=None
    def add_channel(self, name, ct="audio"): c=ChannelStrip(name,ct); self.channels.append(c); return c
    def remove_channel(self, cid): self.channels=[c for c in self.channels if c.id!=cid]
    def get_channel(self, cid):
        for c in self.channels:
            if c.id==cid: return c
    def toggle_mute(self, cid):
        c=self.get_channel(cid)
        if c: c.mute = not c.mute
    def set_volume(self, cid, vol):
        c=self.get_channel(cid)
        if c: c.volume=max(0,min(2,vol))
    def get_state(self): return {"channels":[c.to_dict() for c in self.channels],"buses":self.buses,"master":self.master}
