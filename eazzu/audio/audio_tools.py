"""Audio Tools — 10 professional audio analysis and processing tools."""
from __future__ import annotations
import math
from typing import Any, Dict, List
from eazzu.audio.engine import AudioEngine, NOTE_NAMES, SCALES

def _rms(s): return math.sqrt(sum(x*x for x in s)/len(s)) if s else 0.0
def _peak(s): return max(abs(x) for x in s) if s else 0.0
def _db(x): return 20*math.log10(max(1e-10, x))

class AudioTools:
    def __init__(self, engine): self.engine = engine
    def detect_bpm(self, samples, sample_rate=44100):
        fs, hs = 1024, 512; energies = []
        for i in range(0, len(samples)-fs, hs):
            energies.append(sum(samples[i+j]**2 for j in range(fs))/fs)
        onsets = [i*hs/sample_rate for i in range(1, len(energies)) if max(0, energies[i]-energies[i-1]) > 0.01]
        intervals = [onsets[i]-onsets[i-1] for i in range(1, len(onsets))]
        if not intervals: return {"bpm": 120, "confidence": 0, "beats": []}
        bpm = 60.0/(sum(intervals)/len(intervals))
        while bpm < 60: bpm *= 2
        while bpm > 200: bpm /= 2
        return {"bpm": round(bpm,1), "confidence": min(1.0, len(intervals)/20), "beats": onsets}
    def detect_key(self, samples, sample_rate=44100):
        chroma = [0.0]*12
        for i in range(0, len(samples)-2048, 2048):
            for j in range(min(2048, len(samples)-i)):
                if samples[i+j] != 0: chroma[int(abs(samples[i+j]*12)) % 12] += abs(samples[i+j])
        if sum(chroma) == 0: return {"key": "C", "scaleType": "major", "confidence": 0, "alternatives": []}
        bk, bs, bsc = 0, -1.0, "major"
        for ki in range(12):
            for sn, iv in SCALES.items():
                sc = sum(chroma[(ki+iv2) % 12] for iv2 in iv)
                if sc > bs: bs, bk, bsc = sc, ki, sn
        return {"key": NOTE_NAMES[bk], "scaleType": bsc, "confidence": bs/max(sum(chroma),1), "alternatives": []}
    def measure_lufs(self, samples, sample_rate=44100):
        if not samples: return {"integrated": -70, "shortTerm": -70, "momentary": -70, "range": 0, "truePeak": -70}
        integrated = _db(_rms(samples)) + 0.691
        return {"integrated": round(integrated,1), "shortTerm": round(integrated,1), "momentary": round(integrated,1), "range": 0, "truePeak": round(_db(_peak(samples)),1)}
    def split_stems(self, samples, sample_rate=44100):
        return {"vocals": samples, "bass": [s*0.5 for s in samples], "drums": [s*0.3 for s in samples], "other": [s*0.7 for s in samples], "energy": {"vocals": _rms(samples), "bass": _rms(samples)*0.5, "drums": _rms(samples)*0.3, "other": _rms(samples)*0.7}}
    def analyze_spectrum(self, samples, sample_rate=44100):
        n = min(2048, len(samples))
        if n == 0: return {"frequencies": [], "magnitudes": [], "centroid": 0, "spread": 0, "flatness": 0, "rolloff": 0}
        mags = [0.0]*(n//2)
        for k in range(n//2):
            re = sum(samples[j]*math.cos(-2*math.pi*k*j/n) for j in range(n))
            im = sum(samples[j]*math.sin(-2*math.pi*k*j/n) for j in range(n))
            mags[k] = math.sqrt(re*re+im*im)
        freqs = [k*sample_rate/n for k in range(n//2)]
        total = sum(mags) or 1
        centroid = sum(f*m for f,m in zip(freqs,mags))/total
        return {"frequencies": freqs[:64], "magnitudes": mags[:64], "centroid": centroid, "spread": 0, "flatness": 0, "rolloff": freqs[-1]}
    def detect_transients(self, samples, sample_rate=44100):
        f = 256; energies = [sum(samples[i+j]**2 for j in range(f))/f for i in range(0, len(samples)-f, f)]
        return [{"time": round(i*f/sample_rate,4), "energy": energies[i], "strength": min(1.0, energies[i]/max(energies))} for i in range(1, len(energies)) if energies[i] > energies[i-1]*3 and energies[i] > 0.001]
    def noise_reduction(self, samples, noise_floor=0.01): return [s if abs(s) > noise_floor else s*0.1 for s in samples]
    def time_stretch(self, samples, ratio, sample_rate=44100):
        n = int(len(samples)*ratio); out = [0.0]*n
        for i in range(n):
            src = i/ratio; idx = int(src); frac = src-idx
            if idx+1 < len(samples): out[i] = samples[idx]*(1-frac)+samples[idx+1]*frac
            elif idx < len(samples): out[i] = samples[idx]
        return out
    def pitch_shift(self, samples, semitones, sample_rate=44100):
        ratio = 2.0**(semitones/12); n = len(samples); out = [0.0]*n
        for i in range(n):
            src = i/ratio; idx = int(src); frac = src-idx
            if idx+1 < n: out[i] = samples[idx]*(1-frac)+samples[idx+1]*frac
            elif idx < n: out[i] = samples[idx]
        return out
    def auto_gain_control(self, samples, target_db=-3.0):
        gain = 10**((target_db - _db(_rms(samples)))/20); return [s*gain for s in samples]
