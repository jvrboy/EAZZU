"""MIDI Tools — parse, export, and transform MIDI data. Pure Python."""
from __future__ import annotations
from typing import Any, Dict, List, Optional

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

class MidiNote:
    def __init__(self, note, velocity, start_tick, duration, channel): self.note=note; self.velocity=velocity; self.start_tick=start_tick; self.duration=duration; self.channel=channel
    def to_dict(self): return {"note":self.note,"velocity":self.velocity,"startTick":self.start_tick,"duration":self.duration,"channel":self.channel}

class MidiTrack:
    def __init__(self, name="", notes=None, instrument=0, channel=0): self.name=name; self.notes=notes or []; self.instrument=instrument; self.channel=channel
    def to_dict(self): return {"name":self.name,"notes":[n.to_dict() for n in self.notes],"instrument":self.instrument,"channel":self.channel}

class MidiFile:
    def __init__(self, tracks=None, ticks_per_quarter=480, tempo=500000, duration=0): self.tracks=tracks or []; self.ticks_per_quarter=ticks_per_quarter; self.tempo=tempo; self.duration=duration
    def to_dict(self): return {"tracks":[t.to_dict() for t in self.tracks],"ticksPerQuarter":self.ticks_per_quarter,"tempo":self.tempo,"duration":self.duration}

def _read_uint32(data, offset): return ((data[offset]<<24)|(data[offset+1]<<16)|(data[offset+2]<<8)|data[offset+3]) & 0xFFFFFFFF, offset+4
def _read_uint16(data, offset): return ((data[offset]<<8)|data[offset+1]) & 0xFFFF, offset+2
def _read_var_len(data, offset):
    value=0
    while True:
        byte=data[offset]; offset+=1; value=(value<<7)|(byte&0x7F)
        if not (byte&0x80): break
    return value, offset
def _write_var_len(value):
    b=[value&0x7F]; value>>=7
    while value>0: b.insert(0,(value&0x7F)|0x80); value>>=7
    return b

def parse_midi(buffer):
    data=bytes(buffer); offset=0
    _,offset=_read_uint32(data,offset); _,offset=_read_uint32(data,offset)
    _,offset=_read_uint16(data,offset); num_tracks,offset=_read_uint16(data,offset); tpq,offset=_read_uint16(data,offset)
    tracks=[]
    for t in range(num_tracks):
        if offset+8>len(data): break
        _,offset=_read_uint32(data,offset); tlen,offset=_read_uint32(data,offset); tend=offset+tlen
        notes=[]; tick=0; active={}; tn=f"Track {t+1}"; inst=0; ch=0
        while offset<tend and offset<len(data):
            delta,offset=_read_var_len(data,offset); tick+=delta
            if offset>=len(data): break
            status=data[offset]; offset+=1
            if status<0x80: offset-=1; status=0x80
            et=status&0xf0; ch=status&0x0f
            if et in (0x80,0x90):
                if offset+2>len(data): break
                note=data[offset]; vel=data[offset+1]; offset+=2
                if et==0x90 and vel>0: active[note]={"start_tick":tick,"velocity":vel,"channel":ch}
                else:
                    a=active.pop(note,None)
                    if a: notes.append(MidiNote(note,a["velocity"],a["start_tick"],tick-a["start_tick"],a["channel"]))
            elif et==0xb0: offset+=2
            elif et==0xc0:
                if offset<len(data): inst=data[offset]; offset+=1
            elif et==0xe0: offset+=2
            elif status==0xff:
                if offset>=len(data): break
                mt=data[offset]; offset+=1; length,offset=_read_var_len(data,offset)
                if mt==0x03: tn=data[offset:offset+length].decode("utf-8",errors="replace")
                offset+=length
            else: offset+=1
        tracks.append(MidiTrack(tn,notes,inst,ch))
    duration=max((n.start_tick+n.duration for t in tracks for n in t.notes), default=0)
    return MidiFile(tracks,tpq,500000,duration)

def export_midi(midi):
    chunks=[0x4D,0x54,0x68,0x64,0,0,0,6,0,0,0,len(midi.tracks),(midi.ticks_per_quarter>>8)&0xff,midi.ticks_per_quarter&0xff]
    for tr in midi.tracks:
        td=[0,0xff,0x03,len(tr.name)]+list(tr.name.encode())+[0,0xff,0x51,0x03,(midi.tempo>>16)&0xff,(midi.tempo>>8)&0xff,midi.tempo&0xff]+[0,0xc0|(tr.channel&0x0f),tr.instrument&0x7f]
        events=[]
        for n in tr.notes: events.append((n.start_tick,"on",n.note,n.velocity)); events.append((n.start_tick+n.duration,"off",n.note,0))
        events.sort(key=lambda e:e[0]); pt=0
        for ev in events: td+=_write_var_len(ev[0]-pt); pt=ev[0]; td+=[0x90|(tr.channel&0x0f),ev[2]&0x7f,ev[3]&0x7f] if ev[1]=="on" else [0x80|(tr.channel&0x0f),ev[2]&0x7f,0]
        td+=[0,0xff,0x2f,0]; chunks+=[0x4d,0x54,0x72,0x6b,(len(td)>>24)&0xff,(len(td)>>16)&0xff,(len(td)>>8)&0xff,len(td)&0xff]+td
    return bytes(chunks)

def transform_midi(midi, transpose=0, quantize=0, time_stretch=1.0, velocity_scale=1.0):
    nt=[]
    for tr in midi.tracks:
        nn=[MidiNote(max(0,min(127,n.note+transpose)),max(0,min(127,round(n.velocity*velocity_scale))),round(n.start_tick/quantize)*quantize if quantize>0 else n.start_tick,round(n.duration*time_stretch),n.channel) for n in tr.notes]
        nt.append(MidiTrack(tr.name,nn,tr.instrument,tr.channel))
    return MidiFile(nt,midi.ticks_per_quarter,midi.tempo,midi.duration)

def midi_to_note_name(midi_note): return f"{NOTE_NAMES[midi_note%12]}{midi_note//12-1}"

def generate_midi(tracks, ticks_per_quarter=480, tempo=500000):
    mt=[]
    for ti,tr in enumerate(tracks):
        notes=[MidiNote(na[0],na[1] if len(na)>1 else 100,i*ticks_per_quarter,ticks_per_quarter,tr.get("channel",ti)) for i,na in enumerate(tr.get("notes",[]))]
        mt.append(MidiTrack(tr.get("name",f"Track {ti+1}"),notes,tr.get("instrument",0),tr.get("channel",ti)))
    duration=max((len(t.notes)*ticks_per_quarter for t in mt), default=0)
    return MidiFile(mt,ticks_per_quarter,tempo,duration)
