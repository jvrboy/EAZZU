"""VINNY Extended — 10 AI-powered music creation tools."""
from __future__ import annotations
import math, random
from typing import Any, Dict, List, Optional
from eazzu.audio.engine import NOTE_NAMES, SCALES

def generate_ai_melody(key="C", scale_type="major", bars=4, mood="happy", complexity=0.5):
    scale=SCALES.get(scale_type, SCALES["major"]); ki=NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
    mi={"happy":[0,2,4,7,9],"sad":[0,3,5,7,10],"energetic":[0,2,4,5,7,9,11],"calm":[0,2,4,7],"dark":[0,1,3,6,8]}
    intervals=mi.get(mood, mi["happy"]); melody=[]
    for bar in range(bars):
        bn=[]; prev=ki+12
        for i in range(8):
            if random.random()>complexity and i>0: bn.append(-1); continue
            note=ki+random.choice(intervals)+random.choice([0,12])
            if abs(note-prev)>7 and random.random()>0.3: note=prev+random.choice([2,-2])
            note=max(0,min(127,note)); bn.append(note); prev=note
        melody.append(bn)
    return melody

PROGRESSIONS={"pop":{"chords":[[0,4,7],[5,9,12],[7,11,14],[5,9,12]],"roman":["I","vi","V","vi"]},"jazz":{"chords":[[0,4,7],[5,9,12],[7,11,14],[2,5,9]],"roman":["Imaj7","vi7","ii7","V7"]},"blues":{"chords":[[0,4,7],[5,9,12],[7,11,14],[7,11,14]],"roman":["I7","IV7","V7","V7"]}}

def generate_chord_progression(key="C", style="pop", bars=4):
    ki=NOTE_NAMES.index(key) if key in NOTE_NAMES else 0; prog=PROGRESSIONS.get(style, PROGRESSIONS["pop"])
    return {"name":style,"chords":[[ki+n for n in prog["chords"][bar%len(prog["chords"])] ] for bar in range(bars)],"romanNumerals":[prog["roman"][bar%len(prog["roman"])] for bar in range(bars)]}

def generate_drum_pattern(genre="house", steps=16):
    pat=[[{"active":False,"velocity":100} for _ in range(steps)] for _ in range(4)]
    ks={"trap":[0,6,7,10],"lofi":[0,4,8,12],"house":[0,4,8,12],"techno":[0,2,4,6,8,10,12,14],"dnb":[0,5,8,13]}
    for s in ks.get(genre, ks["house"]):
        if s<steps: pat[0][s]["active"]=True
    for s in [4,12]:
        if s<steps: pat[1][s]["active"]=True
    for i in range(0,steps,2): pat[2][i]["active"]=True; pat[2][i]["velocity"]=60+random.random()*40
    for s in [2,6,10,14]:
        if s<steps: pat[3][s]["active"]=True
    return pat

def generate_arpeggio(notes, pattern="up", octaves=2, steps=16):
    all_n=[n+o*12 for o in range(octaves) for n in notes]; result=[]
    for i in range(steps):
        if pattern=="up": idx=i%len(all_n)
        elif pattern=="down": idx=len(all_n)-1-(i%len(all_n))
        elif pattern=="random": idx=random.randint(0,len(all_n)-1)
        else: idx=i%len(all_n)
        result.append(all_n[idx])
    return result

def generate_bass_line(key="C", scale_type="major", genre="house", bars=4):
    ki=NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
    patterns={"trap":[0,0,0,3,0,0,5,0],"lofi":[0,-1,3,-1,5,-1,3,-1],"house":[0,0,3,0,5,5,3,0],"techno":[0,0,0,0,0,0,0,3],"dnb":[0,-1,-1,0,-1,5,-1,0]}
    pat=patterns.get(genre, patterns["house"])
    return [[ki+iv+36 if iv>=0 else -1 for iv in pat] for _ in range(bars)]

def find_scales(notes):
    ns=set(n%12 for n in notes); return [sn for sn, iv in SCALES.items() if ns.issubset(set(iv2%12 for iv2 in iv))]

def harmonize(melody, intervals=None):
    if intervals is None: intervals=[3,5]
    return [[n+iv for iv in intervals] if n>=0 else [-1,-1] for n in melody]

def generate_euclidean_rhythm(steps, pulses, rotation=0):
    rhythm=[False]*steps; bs=pulses/steps; bucket=rotation*bs
    for i in range(steps):
        bucket+=bs
        if bucket>=1: rhythm[i]=True; bucket-=1
    return rhythm

def optimize_voice_leading(chords):
    if not chords: return chords
    result=[[n+48 for n in chords[0]]]
    for i in range(1,len(chords)):
        prev=result[i-1]; opt=[]
        for j,note in enumerate(chords[i]):
            pn=prev[j] if j<len(prev) else prev[0]; best=note+48; bd=abs(best-pn)
            for o in range(-2,3):
                c=note+48+o*12; d=abs(c-pn)
                if d<bd: bd=d; best=c
            opt.append(best)
        result.append(opt)
    return result

def generate_song_structure(genre="pop"):
    structures={"pop":["intro","verse","chorus","verse","chorus","bridge","chorus","outro"],"trap":["intro","hook","verse","hook","verse","hook","outro"],"house":["intro","build","drop","break","build","drop","outro"],"lofi":["intro","verse","chorus","verse","bridge","outro"],"techno":["intro","build","peak","break","peak","outro"]}
    sections=structures.get(genre, structures["pop"])
    em={"intro":0.3,"verse":0.5,"chorus":0.9,"bridge":0.6,"outro":0.3,"hook":0.85,"build":0.6,"drop":1.0,"break":0.3,"peak":1.0}
    return [{"name":n,"bars":8,"energy":em.get(n,0.5)} for n in sections]
