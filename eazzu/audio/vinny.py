"""VINNY — The All-in-One Sound Architect Engine."""
from __future__ import annotations
import math, random, uuid
from typing import Any, Dict, List, Optional
from eazzu.audio.engine import AudioEngine, note_to_freq, NOTE_NAMES, SCALES

class OscLayer:
    def __init__(self, shape="sawtooth", frequency=440.0, detune=0.0, volume=0.5, phase=0.0, unison=1, unison_spread=0.0, wavetable_index=0, fm_mod=None, fm_depth=0.0, ring_mod=None, pan=0.0):
        self.id=str(uuid.uuid4()); self.shape=shape; self.frequency=frequency; self.detune=detune; self.volume=volume; self.phase=phase; self.unison=unison; self.unison_spread=unison_spread; self.wavetable_index=wavetable_index; self.fm_mod=fm_mod; self.fm_depth=fm_depth; self.ring_mod=ring_mod; self.pan=pan
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class SoundEngineConfig:
    def __init__(self): self.oscillators=[OscLayer()]; self.filter={"type":"lowpass","cutoff":20000,"resonance":0.7}; self.amp_env={"attack":0.02,"decay":0.2,"sustain":0.6,"release":0.4}; self.master_volume=0.8
    def to_dict(self): return {"oscillators":[o.to_dict() for o in self.oscillators],"filter":self.filter,"ampEnv":self.amp_env,"masterVolume":self.master_volume}

class Vinny:
    def __init__(self, engine=None): self.engine=engine or AudioEngine(); self.config=SoundEngineConfig(); self._active_notes={}
    def note_on(self, note, velocity=0.8): freq=note_to_freq(note); self._active_notes[note]={"freq":freq,"velocity":velocity}; return {"note":note,"freq":freq,"active":True}
    def note_off(self, note): self._active_notes.pop(note,None); return {"note":note,"active":False}
    def render_note(self, note, duration, sample_rate=44100):
        freq=note_to_freq(note); out=[0.0]*int(duration*sample_rate)
        for osc in self.config.oscillators:
            of=freq*(osc.frequency/440.0) if osc.frequency!=440 else freq; dr=2**(osc.detune/1200)
            for i in range(len(out)):
                t=i/sample_rate
                if osc.shape=="sine": out[i]+=math.sin(2*math.pi*of*t)*osc.volume
                elif osc.shape=="sawtooth": out[i]+=(2*((of*t)%1)-1)*osc.volume
                elif osc.shape=="square": out[i]+=(1.0 if math.sin(2*math.pi*of*t)>=0 else -1.0)*osc.volume
                elif osc.shape=="triangle": out[i]+=(2*abs(2*((of*t)%1)-1)-1)*osc.volume
        env=self.config.amp_env; a=int(env["attack"]*sample_rate); d=int(env["decay"]*sample_rate); r=int(env["release"]*sample_rate); sl=env["sustain"]; n=len(out)
        for i in range(n):
            if i<a: g=i/max(a,1)
            elif i<a+d: g=1-(1-sl)*((i-a)/max(d,1))
            elif i<n-r: g=sl
            else: g=sl*max(0,1-(i-(n-r))/max(r,1))
            out[i]*=g*self.config.master_volume
        return out
    def add_oscillator(self, shape="sawtooth", freq=440, detune=0, volume=0.5): osc=OscLayer(shape,freq,detune,volume); self.config.oscillators.append(osc); return osc
    def get_state(self): return {"config":self.config.to_dict(),"activeNotes":list(self._active_notes.keys()),"engine":self.engine.get_state()}
