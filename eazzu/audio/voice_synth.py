"""Voice Synthesis Engine — singing voice synthesis."""
from __future__ import annotations
import math, random, re, uuid
from typing import Any, Dict, List, Optional

VOWEL_MAP = {"a":"ah","e":"eh","i":"ee","o":"oh","u":"oo"}

class LyricSyllable:
    def __init__(self, text, phoneme, midi, duration_sec, vibrato, intensity): self.text=text; self.phoneme=phoneme; self.midi=midi; self.duration_sec=duration_sec; self.vibrato=vibrato; self.intensity=intensity
    def to_dict(self): return {k:v for k,v in vars(self).items()}

def parse_lyrics(lyrics, tempo=120):
    words=[w for w in re.split(r"\s+", lyrics) if w]; syls=[]; spb=60.0/tempo
    for word in words:
        syls_re=re.findall(r"[bcdfghjklmnpqrstvwxyz]*[aeiouAEIOU]+[bcdfghjklmnpqrstvwxyz]*", word) or [word]
        for syl in syls_re:
            vm=re.search(r"[aeiouAEIOU]", syl); ph=VOWEL_MAP.get(vm.group(0).lower(),"ah") if vm else "ah"
            syls.append(LyricSyllable(syl, ph, 60, spb, 0.2, 0.7))
    return syls

def apply_variation(melody, variation="none", randomness=0.0):
    if variation=="none" or randomness==0: return melody
    result=[LyricSyllable(s.text,s.phoneme,s.midi,s.duration_sec,s.vibrato,s.intensity) for s in melody]
    for s in result:
        r=random.random()
        if variation in ("rhythm","all") and r<randomness: s.duration_sec*=random.choice([0.5,0.75,1.0,1.5,2.0])
        if variation in ("pitch","all") and r<randomness*0.7: s.midi=max(36,min(84,s.midi+(random.randint(0,4)-2)*2))
    return result

class VoiceSynth:
    def synthesize(self, voice, lyrics, tempo=120, variation="none", randomness=0.0, sample_rate=44100):
        melody=parse_lyrics(lyrics, tempo); melody=apply_variation(melody, variation, randomness)
        total=sum(s.duration_sec for s in melody); ts=int(total*sample_rate); out=[0.0]*ts; offset=0
        for syl in melody:
            ph=next((p for p in voice.phonemes if p.phoneme==syl.phoneme), voice.phonemes[0] if voice.phonemes else None)
            if ph:
                tf=440*(2**((syl.midi-69)/12)); pr=tf/max(voice.formants.pitch,1)
                sl=min(ph.length, int(syl.duration_sec*sample_rate))
                for i in range(sl):
                    if offset+i>=ts: break
                    si=int(ph.buffer_offset+i*pr)
                    if si<len(voice.buffer): out[offset+i]+=voice.buffer[si]*math.sin(math.pi*i/max(sl,1))*syl.intensity
            offset+=int(syl.duration_sec*sample_rate)
        return {"samples":out,"duration":total,"syllables":len(melody)}
