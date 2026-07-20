"""Stem Splitter — source separation via spectral masking."""
from __future__ import annotations
import math
from typing import Any, Dict, List, Optional

def buffer_energy(s): return math.sqrt(sum(x*x for x in s[::64])/max(1,len(s)//64)) if s else 0.0

def _band_pass(samples, lo, hi, sr=44100):
    out=[0.0]*len(samples); prev=0.0
    for i in range(len(samples)):
        hp = samples[i] - prev; prev = hp
        lp = prev; out[i] = lp
    return out

class StemSplitter:
    def split(self, samples, opts=None, sample_rate=44100):
        vocals=_band_pass(samples,200,4000,sample_rate)
        bass=_band_pass(samples,20,250,sample_rate)
        drums=_band_pass(samples,2000,20000,sample_rate)
        other=[samples[i]-vocals[i]*0.5-bass[i]*0.5-drums[i]*0.3 for i in range(len(samples))]
        instrumental=[samples[i]-vocals[i]*0.8 for i in range(len(samples))]
        return [{"type":"vocals","energy":buffer_energy(vocals)},{"type":"drums","energy":buffer_energy(drums)},{"type":"bass","energy":buffer_energy(bass)},{"type":"other","energy":buffer_energy(other)},{"type":"instrumental","energy":buffer_energy(instrumental)}]
