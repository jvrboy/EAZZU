"""Step Sequencer — 16-step polyrhythmic sequencer."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

DRUM_NAMES = ["Kick", "Snare", "Hat", "Clap", "Tom", "Rim", "Crash", "Perc"]

class StepData:
    def __init__(self): self.active=False; self.note="C4"; self.velocity=0.8; self.gate=0.8; self.accent=False; self.glide=False
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class SequencerTrack:
    def __init__(self, tid, name, ttype, steps=16):
        self.id=tid; self.name=name; self.type=ttype; self.steps=[StepData() for _ in range(steps)]
        self.waveform="sawtooth" if ttype=="synth" else None; self.muted=False; self.volume=0.7
    def to_dict(self): return {"id":self.id,"name":self.name,"type":self.type,"steps":[s.to_dict() for s in self.steps],"waveform":self.waveform,"muted":self.muted,"volume":self.volume}

class SequencerState:
    def __init__(self): self.tracks=[]; self.bpm=120; self.swing=0.0; self.current_step=0; self.playing=False; self.steps_per_beat=4; self.total_steps=16
    def to_dict(self): return {"tracks":[t.to_dict() for t in self.tracks],"bpm":self.bpm,"swing":self.swing,"currentStep":self.current_step,"playing":self.playing,"stepsPerBeat":self.steps_per_beat,"totalSteps":self.total_steps}

def create_default_track(tid, name, ttype, steps=16): return SequencerTrack(tid, name, ttype, steps)

def create_default_sequencer():
    s = SequencerState()
    s.tracks = [create_default_track("kick","Kick","drum"), create_default_track("snare","Snare","drum"), create_default_track("hat","Hat","drum"), create_default_track("bass","Bass","synth"), create_default_track("lead","Lead","synth")]
    for i in [0,4,8,12]: s.tracks[0].steps[i].active = True
    for i in [4,12]: s.tracks[1].steps[i].active = True
    for i in [0,2,4,6,8,10,12,14]: s.tracks[2].steps[i].active = True
    for i in [0,3,6,8,11,14]: s.tracks[3].steps[i].active = True
    for i in [0,2,4,6,8,10,12,14]: s.tracks[4].steps[i].active = True
    return s

class Sequencer:
    def __init__(self, engine=None): self.engine=engine; self.state=create_default_sequencer()
    def play(self): self.state.playing=True; self.state.current_step=0
    def stop(self): self.state.playing=False
    def toggle_step(self, tid, si):
        for t in self.state.tracks:
            if t.id==tid and 0<=si<len(t.steps): t.steps[si].active = not t.steps[si].active; return {"trackId":tid,"step":si,"active":t.steps[si].active}
        return {"error":"not_found"}
    def set_bpm(self, bpm): self.state.bpm = max(20, min(300, bpm))
    def get_state(self): return self.state.to_dict()
