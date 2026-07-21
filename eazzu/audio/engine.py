"""Audio Engine — core synthesis, effects, and signal routing.

Converted from infinite-loop-sound's engine.ts. The Web Audio API graph is
represented as an in-memory state machine: nodes are dicts, connections are
tracked as adjacency lists, and DSP is computed on demand via pure-Python
float math. No external dependencies.
"""
from __future__ import annotations

import math
import random
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

Waveform = str  # "sine" | "square" | "sawtooth" | "triangle" | "noise"

WAVEFORMS: List[str] = ["sine", "square", "sawtooth", "triangle", "noise"]

NOTE_NAMES: List[str] = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

SCALES: Dict[str, List[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonicMinor": [0, 2, 3, 5, 7, 8, 11],
    "melodicMinor": [0, 2, 3, 5, 7, 9, 11],
    "pentatonic": [0, 2, 4, 7, 9],
    "minorPentatonic": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "chromatic": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11],
    "wholeTone": [0, 2, 4, 6, 8, 10],
    "augmented": [0, 3, 4, 7, 8, 11],
    "diminished": [0, 2, 3, 5, 6, 8, 9, 11],
}

NOTE_FREQS: Dict[str, float] = {}
for _i, _name in enumerate(NOTE_NAMES):
    for _oct in range(-1, 10):
        _midi = (_i + 12) + _oct * 12
        NOTE_FREQS[f"{_name}{_oct}"] = 440.0 * (2.0 ** ((_midi - 69) / 12))


def note_to_freq(note: str) -> float:
    return NOTE_FREQS.get(note, 440.0)


def midi_to_freq(note: int) -> float:
    return 440.0 * (2.0 ** ((note - 69) / 12))


def midi_to_note_name(note: int) -> str:
    return f"{NOTE_NAMES[note % 12]}{note // 12 - 1}"


class SynthVoiceParams:
    def __init__(self, waveform="sawtooth", attack=0.02, decay=0.2, sustain=0.6, release=0.4, detune=0.0, gain=0.5):
        self.waveform = waveform; self.attack = attack; self.decay = decay
        self.sustain = sustain; self.release = release; self.detune = detune; self.gain = gain
    def to_dict(self): return {k: v for k, v in vars(self).items()}


class GranularParams:
    def __init__(self, grain_size=0.1, grain_density=20.0, pitch=1.0, spread=0.5, position=0.0, position_jitter=0.1, envelope=0.5, mix=0.5):
        self.grain_size = grain_size; self.grain_density = grain_density; self.pitch = pitch
        self.spread = spread; self.position = position; self.position_jitter = position_jitter
        self.envelope = envelope; self.mix = mix
    def to_dict(self): return {k: v for k, v in vars(self).items()}


class EffectParams:
    def __init__(self, reverb=0.0, delay=0.0, delay_time=0.25, delay_feedback=0.3, filter=1.0, filter_freq=20000.0, distortion=0.0, compressor=0.5):
        self.reverb = reverb; self.delay = delay; self.delay_time = delay_time
        self.delay_feedback = delay_feedback; self.filter = filter; self.filter_freq = filter_freq
        self.distortion = distortion; self.compressor = compressor
    def to_dict(self): return {k: v for k, v in vars(self).items()}


DEFAULT_SYNTH = SynthVoiceParams()
DEFAULT_GRANULAR = GranularParams()
DEFAULT_EFFECTS = EffectParams()


def _generate_waveform(waveform, freq, duration, sample_rate=44100):
    n = int(duration * sample_rate); out = [0.0] * n
    if waveform == "sine":
        out = [math.sin(2*math.pi*freq*i/sample_rate) for i in range(n)]
    elif waveform == "square":
        out = [1.0 if math.sin(2*math.pi*freq*i/sample_rate) >= 0 else -1.0 for i in range(n)]
    elif waveform == "sawtooth":
        out = [2.0*((freq*i/sample_rate) % 1.0) - 1.0 for i in range(n)]
    elif waveform == "triangle":
        out = [2.0*abs(2.0*((freq*i/sample_rate) % 1.0) - 1.0) - 1.0 for i in range(n)]
    elif waveform == "noise":
        out = [random.uniform(-1, 1) for _ in range(n)]
    return out


def _apply_adsr(samples, params, sample_rate=44100):
    n = len(samples); a = int(params.attack*sample_rate); d = int(params.decay*sample_rate)
    r = int(params.release*sample_rate); sl = params.gain * params.sustain; out = list(samples)
    for i in range(n):
        if i < a: env = i/max(a,1)
        elif i < a+d: env = params.gain - (params.gain-sl)*((i-a)/max(d,1))
        elif i < n-r: env = sl
        else: env = sl * max(0.0, 1.0 - (i-(n-r))/max(r,1))
        out[i] *= env
    return out


class AudioEngine:
    def __init__(self, sample_rate=44100):
        self.sample_rate = sample_rate; self.master_volume = 0.8; self.bus_volume = 0.9
        self.dry_gain = 1.0; self.wet_gain = 0.0; self.delay_wet = 0.0; self.delay_time = 0.25
        self.delay_feedback = 0.3; self.filter_freq = 20000.0; self.filter_type = "lowpass"
        self.distortion_amount = 0.0; self.compressor_threshold = 0.5; self.ready = True
        self.active_voices = {}; self.granular_buffer = None; self.granular_playing = False
        self.granular_params = GranularParams(); self.effects = EffectParams()
        self._analyser_data = []
    def init(self): self.ready = True
    def resume(self): pass
    def note_on(self, vid, freq, params=None):
        if params is None: params = DEFAULT_SYNTH
        self.active_voices[vid] = {"id": vid, "freq": freq, "params": params.to_dict(), "started_at": time.time()}
        return {"active": True, "voiceId": vid, "freq": freq}
    def note_off(self, vid):
        v = self.active_voices.pop(vid, None); return {"active": False, "voiceId": vid, "hadVoice": v is not None}
    def render_note(self, freq, duration, params=None):
        if params is None: params = DEFAULT_SYNTH
        return _apply_adsr(_generate_waveform(params.waveform, freq, duration, self.sample_rate), params, self.sample_rate)
    def set_effects(self, effects):
        self.effects = effects
        self.wet_gain = effects.reverb
        self.delay_wet = effects.delay
        self.delay_time = effects.delay_time
        self.delay_feedback = effects.delay_feedback
        self.filter_freq = effects.filter_freq
        self.distortion_amount = effects.distortion
    def set_master_volume(self, vol): self.master_volume = max(0.0, min(2.0, vol))
    def get_state(self):
        return {"ready": self.ready, "masterVolume": self.master_volume, "activeVoices": len(self.active_voices),
                "effects": self.effects.to_dict(), "filterFreq": self.filter_freq, "distortionAmount": self.distortion_amount}
    def granular_play(self, buf, params=None):
        if params is None: params = self.granular_params
        self.granular_buffer = buf; self.granular_params = params; self.granular_playing = True
    def granular_stop(self): self.granular_playing = False; self.granular_buffer = None
    def render_granular(self, duration):
        if not self.granular_buffer or not self.granular_playing: return []
        p = self.granular_params; n = int(duration*self.sample_rate); out = [0.0]*n
        bl = len(self.granular_buffer)
        if bl == 0: return out
        gs = int(p.grain_size*self.sample_rate); gc = int(duration*p.grain_density)
        for g in range(gc):
            si = int(g/p.granular_density*self.sample_rate)
            pos = int(p.position*bl) + random.randint(-int(p.position_jitter*bl*0.1), int(p.position_jitter*bl*0.1))
            for i in range(gs):
                src = int((pos + i*p.pitch) % bl)
                env = math.sin(math.pi*i/gs) if p.envelope > 0.5 else 1.0
                if 0 <= si+i < n: out[si+i] += self.granular_buffer[src] * env * p.mix
        return out

AudioEngineInstance = AudioEngine()
