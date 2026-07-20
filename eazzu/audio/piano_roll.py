"""Advanced Piano Roll — per-note slide system with infinite glide automation."""
from __future__ import annotations
import math, uuid
from typing import Any, Dict, List, Optional

class AutomationPoint:
    def __init__(self, tick, value, curve="linear"): self.tick=tick; self.value=value; self.curve=curve
    def to_dict(self): return {"tick":self.tick,"value":self.value,"curve":self.curve}

class NoteSlide:
    def __init__(self, start_tick=0, end_tick=0, start_pitch=60.0, end_pitch=60.0, curve_type="linear", curve_amount=0.5):
        self.id=str(uuid.uuid4()); self.start_tick=start_tick; self.end_tick=end_tick; self.start_pitch=start_pitch; self.end_pitch=end_pitch; self.curve_type=curve_type; self.curve_amount=curve_amount
    def to_dict(self): return {"id":self.id,"startTick":self.start_tick,"endTick":self.end_tick,"startPitch":self.start_pitch,"endPitch":self.end_pitch,"curveType":self.curve_type,"curveAmount":self.curve_amount}

class PianoNote:
    def __init__(self, midi=60, start_tick=0, duration=480, velocity=100, pan=0.0, channel=0):
        self.id=str(uuid.uuid4()); self.midi=midi; self.start_tick=start_tick; self.duration=duration; self.velocity=velocity; self.pan=pan; self.channel=channel
        self.slides=[]; self.pitch_bend=0; self.micro_tuning=0.0; self.gain=1.0; self.mute=False; self.solo=False
        self.color="#3b82f6"; self.group=""; self.locked=False; self.vibrato=0.0; self.vibrato_rate=5.0
        self.tremolo=0.0; self.tremolo_rate=6.0; self.expression=1.0; self.breath=0.0
        self.volume_automation=[]; self.pan_automation=[]; self.filter_automation=[]
    def to_dict(self): return {"id":self.id,"midi":self.midi,"startTick":self.start_tick,"duration":self.duration,"velocity":self.velocity,"pan":self.pan,"channel":self.channel,"slides":[s.to_dict() for s in self.slides],"vibrato":self.vibrato,"expression":self.expression}

class PianoRoll:
    def __init__(self, ticks_per_quarter=480): self.notes=[]; self.ticks_per_quarter=ticks_per_quarter; self.snap=ticks_per_quarter//4; self.zoom=1.0; self.scroll_x=0; self.scroll_y=0; self.playhead_tick=0
    def add_note(self, note): self.notes.append(note); return note
    def remove_note(self, nid): self.notes=[n for n in self.notes if n.id!=nid]
    def update_note(self, nid, patch):
        for n in self.notes:
            if n.id==nid:
                for k,v in patch.items():
                    if hasattr(n,k): setattr(n,k,v)
    def add_slide(self, nid, slide):
        for n in self.notes:
            if n.id==nid: n.slides.append(slide)
    def get_pitch_at_tick(self, note, tick):
        rel = tick - note.start_tick
        if rel < 0 or rel > note.duration: return float(note.midi)
        pitch = float(note.midi) + note.micro_tuning/100
        for sl in note.slides:
            if sl.start_tick <= rel <= sl.end_tick:
                t = (rel - sl.start_tick)/max(1, sl.end_tick - sl.start_tick)
                pitch = sl.start_pitch + (sl.end_pitch - sl.start_pitch) * t
        if note.vibrato > 0: pitch += math.sin(2*math.pi*note.vibrato_rate*rel/480) * note.vibrato
        return pitch
    def get_state(self): return {"notes":[n.to_dict() for n in self.notes],"ticksPerQuarter":self.ticks_per_quarter,"snap":self.snap,"playheadTick":self.playhead_tick}
