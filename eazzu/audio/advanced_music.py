"""Advanced music tools — extended DSP, composition and production utilities.

Adds granular synthesis, spectral processing, harmonic analysis, advanced
sequencing, voice-leading, counterpoint, generative algorithms, and a
lightweight WAV writer. Pure-Python, stdlib-only, iSH-safe.
"""
from __future__ import annotations

import math
import random
import struct
import wave
from typing import Any, Dict, List, Optional, Tuple

from eazzu.audio.engine import NOTE_NAMES, SCALES, note_to_freq


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


# ─── Granular synthesis ─────────────────────────────────────────────────

def granular_synthesize(samples: List[float], grain_size: float = 0.05,
                        density: float = 20.0, pitch: float = 1.0,
                        spread: float = 0.5, position: float = 0.0,
                        jitter: float = 0.1, duration: float = 2.0,
                        sample_rate: int = 44100) -> Dict[str, Any]:
    try:
        n = int(duration * sample_rate)
        out = [0.0] * n
        bl = len(samples)
        if bl == 0:
            return {"samples": [], "grains": 0}
        gs = max(1, int(grain_size * sample_rate))
        gc = int(duration * density)
        for g in range(gc):
            start = int((g / max(density, 1)) * sample_rate)
            pos = int(position * bl) + random.randint(-int(jitter * bl * 0.1), int(jitter * bl * 0.1))
            for i in range(gs):
                src = int((pos + i * pitch) % bl)
                env = math.sin(math.pi * i / gs)
                if 0 <= start + i < n:
                    out[start + i] += samples[src] * env * spread
        peak = max(abs(x) for x in out) or 1.0
        out = [x / max(peak, 1e-9) * 0.9 for x in out]
        return {"samples": out, "grains": gc, "duration": duration}
    except Exception as exc:
        return _error("granular_failed", exc)


# ─── Spectral processing ────────────────────────────────────────────────

def spectral_dft(samples: List[float], sample_rate: int = 44100,
                  max_bins: int = 256) -> Dict[str, Any]:
    try:
        n = min(len(samples), 2048)
        if n == 0:
            return {"frequencies": [], "magnitudes": [], "peak_freq": 0, "centroid": 0}
        mags = [0.0] * (n // 2)
        for k in range(n // 2):
            re = sum(samples[j] * math.cos(-2 * math.pi * k * j / n) for j in range(n))
            im = sum(samples[j] * math.sin(-2 * math.pi * k * j / n) for j in range(n))
            mags[k] = math.sqrt(re * re + im * im)
        freqs = [k * sample_rate / n for k in range(n // 2)]
        peak_idx = max(range(n // 2), key=lambda i: mags[i])
        total = sum(mags) or 1.0
        centroid = sum(f * m for f, m in zip(freqs, mags)) / total
        return {
            "frequencies": freqs[:max_bins],
            "magnitudes": mags[:max_bins],
            "peak_freq": freqs[peak_idx],
            "centroid": centroid,
            "spread": math.sqrt(sum(((f - centroid) ** 2) * m for f, m in zip(freqs, mags)) / total),
        }
    except Exception as exc:
        return _error("dft_failed", exc)


def spectral_freeze(samples: List[float], freeze: float = 0.8,
                    sample_rate: int = 44100) -> Dict[str, Any]:
    try:
        n = min(len(samples), 2048)
        if n == 0:
            return {"samples": []}
        mags = [0.0] * (n // 2)
        phases = [0.0] * (n // 2)
        for k in range(n // 2):
            re = sum(samples[j] * math.cos(-2 * math.pi * k * j / n) for j in range(n))
            im = sum(samples[j] * math.sin(-2 * math.pi * k * j / n) for j in range(n))
            mags[k] = math.sqrt(re * re + im * im)
            phases[k] = math.atan2(im, re)
        out_len = len(samples)
        out = [0.0] * out_len
        for i in range(out_len):
            s = 0.0
            for k in range(min(n // 2, 64)):
                s += mags[k] * math.cos(2 * math.pi * k * i / n + phases[k])
            out[i] = s * freeze / (n // 2)
        return {"samples": out, "frozen": True}
    except Exception as exc:
        return _error("freeze_failed", exc)


# ─── Harmonic analysis ──────────────────────────────────────────────────

def harmonic_analysis(samples: List[float], fundamental: float = 440.0,
                      sample_rate: int = 44100, harmonics: int = 16) -> Dict[str, Any]:
    try:
        n = len(samples)
        if n == 0:
            return {"harmonics": []}
        amps = []
        for h in range(1, harmonics + 1):
            freq = fundamental * h
            if freq >= sample_rate / 2:
                break
            re = sum(samples[j] * math.cos(-2 * math.pi * freq * j / sample_rate) for j in range(n))
            im = sum(samples[j] * math.sin(-2 * math.pi * freq * j / sample_rate) for j in range(n))
            amps.append({"harmonic": h, "frequency": round(freq, 2),
                         "amplitude": round(math.sqrt(re * re + im * im) / n, 6)})
        total = sum(a["amplitude"] for a in amps) or 1.0
        for a in amps:
            a["ratio"] = round(a["amplitude"] / total, 4)
        return {"fundamental": fundamental, "harmonics": amps}
    except Exception as exc:
        return _error("harmonic_failed", exc)


def detect_pitch_autocorrelation(samples: List[float], sample_rate: int = 44100,
                                 min_freq: float = 80.0, max_freq: float = 1000.0) -> Dict[str, Any]:
    try:
        n = len(samples)
        if n < 256:
            return {"pitch": 0, "note": None, "confidence": 0}
        min_lag = int(sample_rate / max_freq)
        max_lag = int(sample_rate / min_freq)
        max_lag = min(max_lag, n // 2)
        best_lag, best_corr = 0, 0.0
        for lag in range(min_lag, max_lag):
            corr = sum(samples[i] * samples[i + lag] for i in range(n - max_lag))
            if corr > best_corr:
                best_corr, best_lag = corr, lag
        if best_lag == 0:
            return {"pitch": 0, "note": None, "confidence": 0}
        pitch = sample_rate / best_lag
        midi = round(69 + 12 * math.log2(pitch / 440.0))
        note = NOTE_NAMES[midi % 12] + str(midi // 12 - 1)
        return {"pitch": round(pitch, 2), "note": note, "midi": midi,
                "confidence": round(min(1.0, best_corr / (sum(s * s for s in samples[:n - max_lag]) or 1)), 3)}
    except Exception as exc:
        return _error("pitch_failed", exc)


# ─── Advanced composition ───────────────────────────────────────────────

def generate_counterpoint(melody: List[int], species: int = 1,
                          key: str = "C", scale_type: str = "major") -> Dict[str, Any]:
    try:
        scale = SCALES.get(scale_type, SCALES["major"])
        ki = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
        intervals = [3, 5, 6, 8]
        cp = []
        for n in melody:
            if n < 0:
                cp.append(-1)
                continue
            choice = n + random.choice(intervals)
            while (choice - ki) % 12 not in [s % 12 for s in scale] and random.random() > 0.2:
                choice = n + random.choice(intervals)
            cp.append(max(0, min(127, choice)))
        return {"counterpoint": cp, "species": species, "key": key, "scale": scale_type}
    except Exception as exc:
        return _error("counterpoint_failed", exc)


def generate_fugue(subject: List[int], key: str = "C", scale_type: str = "major",
                   voices: int = 4, entries: int = 4) -> Dict[str, Any]:
    try:
        answer = [(n + 7) % 12 + (n // 12) * 12 if n >= 0 else -1 for n in subject]
        parts: List[List[int]] = [[] for _ in range(voices)]
        for e in range(entries):
            v = e % voices
            line = subject if e % 2 == 0 else answer
            transpose = (e // 2) * 12
            for n in line:
                parts[v].append(max(0, min(127, n + transpose)) if n >= 0 else -1)
        return {"subject": subject, "answer": answer, "voices": parts, "key": key}
    except Exception as exc:
        return _error("fugue_failed", exc)


def markov_melody(seed_notes: List[int], length: int = 32, order: int = 2) -> Dict[str, Any]:
    try:
        if not seed_notes:
            return {"melody": []}
        transitions: Dict[Tuple[int, ...], List[int]] = {}
        for i in range(len(seed_notes) - order):
            key = tuple(seed_notes[i:i + order])
            transitions.setdefault(key, []).append(seed_notes[i + order])
        melody = list(seed_notes[:order])
        for _ in range(length - order):
            key = tuple(melody[-order:])
            opts = transitions.get(key)
            melody.append(random.choice(opts) if opts else random.choice(seed_notes))
        return {"melody": melody, "order": order, "length": len(melody)}
    except Exception as exc:
        return _error("markov_failed", exc)


def generate_scales_full() -> Dict[str, Any]:
    return {"scales": {name: list(iv) for name, iv in SCALES.items()}}


def chord_voicing(chord: List[int], voicing: str = "close") -> Dict[str, Any]:
    try:
        if not chord:
            return {"voicing": []}
        c = sorted(chord)
        if voicing == "close":
            v = list(c)
        elif voicing == "drop2":
            v = list(c)
            if len(v) >= 4:
                v[-2] -= 12
        elif voicing == "drop3":
            v = list(c)
            if len(v) >= 4:
                v[-3] -= 12
        elif voicing == "open":
            v = [c[0], c[-1]] + [n + 12 for n in c[1:-1]]
        elif voicing == "spread":
            v = []
            for i, n in enumerate(c):
                v.append(n + (12 if i % 2 else 0))
        else:
            v = list(c)
        return {"voicing": sorted(v), "type": voicing}
    except Exception as exc:
        return _error("voicing_failed", exc)


# ─── WAV writer ──────────────────────────────────────────────────────────

def write_wav(samples: List[float], path: str, sample_rate: int = 44100,
              normalize: bool = True) -> Dict[str, Any]:
    try:
        if normalize and samples:
            peak = max(abs(x) for x in samples) or 1.0
            samples = [x / peak * 0.95 for x in samples]
        with wave.open(path, "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(sample_rate)
            frames = b"".join(struct.pack("<h", int(max(-1, min(1, s)) * 32767)) for s in samples)
            w.writeframes(frames)
        return {"path": path, "samples": len(samples), "sample_rate": sample_rate}
    except Exception as exc:
        return _error("wav_failed", exc)


# ─── Advanced effects ───────────────────────────────────────────────────

def _one_pole_lowpass(samples: List[float], cutoff: float = 0.5) -> List[float]:
    out = [0.0] * len(samples)
    a = 1 - cutoff
    out[0] = samples[0] * cutoff
    for i in range(1, len(samples)):
        out[i] = out[i - 1] * a + samples[i] * cutoff
    return out


def apply_distortion(samples: List[float], drive: float = 0.5,
                     tone: float = 0.5, mix: float = 1.0) -> Dict[str, Any]:
    try:
        k = 1 + drive * 10
        out = [math.tanh(s * k) * 0.8 for s in samples]
        if tone < 0.5:
            out = _one_pole_lowpass(out, 1.0 - tone)
        return {"samples": [d * (1 - mix) + w * mix for d, w in zip(samples, out)]}
    except Exception as exc:
        return _error("distortion_failed", exc)


def apply_chorus(samples: List[float], rate: float = 1.5, depth: float = 0.3,
                 mix: float = 0.5, sample_rate: int = 44100) -> Dict[str, Any]:
    try:
        n = len(samples)
        out = [0.0] * n
        max_delay = int(0.05 * sample_rate)
        buf = [0.0] * max_delay
        idx = 0
        for i in range(n):
            delay = int((0.02 + depth * 0.02 * math.sin(2 * math.pi * rate * i / sample_rate)) * sample_rate)
            delay = min(max_delay - 1, max(0, delay))
            buf[idx] = samples[i]
            read = (idx - delay) % max_delay
            out[i] = samples[i] * (1 - mix) + buf[read] * mix
            idx = (idx + 1) % max_delay
        return {"samples": out}
    except Exception as exc:
        return _error("chorus_failed", exc)


def apply_compressor(samples: List[float], threshold: float = -18.0,
                     ratio: float = 4.0, attack: float = 0.003,
                     release: float = 0.1, makeup: float = 0.0,
                     sample_rate: int = 44100) -> Dict[str, Any]:
    try:
        thr = 10 ** (threshold / 20)
        a_coef = math.exp(-1 / (attack * sample_rate))
        r_coef = math.exp(-1 / (release * sample_rate))
        env = 0.0
        gain = 1.0
        out = [0.0] * len(samples)
        for i, s in enumerate(samples):
            x = abs(s)
            if x > env:
                env = a_coef * env + (1 - a_coef) * x
            else:
                env = r_coef * env + (1 - r_coef) * x
            if env > thr:
                gain = (env / thr) ** (1 / ratio - 1)
            else:
                gain = 1.0
            out[i] = s * gain * (10 ** (makeup / 20))
        return {"samples": out}
    except Exception as exc:
        return _error("compressor_failed", exc)


# ─── Advanced sequencing ────────────────────────────────────────────────

def generate_polyrhythm(patterns: List[int], steps: int = 16) -> Dict[str, Any]:
    try:
        tracks = []
        for pulses in patterns:
            track = []
            bucket = 0.0
            for i in range(steps):
                bucket += pulses
                if bucket >= steps:
                    track.append(True)
                    bucket -= steps
                else:
                    track.append(False)
            tracks.append(track)
        return {"tracks": tracks, "steps": steps, "patterns": patterns}
    except Exception as exc:
        return _error("polyrhythm_failed", exc)


def swing_quantize(rhythm: List[bool], swing: float = 0.6) -> Dict[str, Any]:
    try:
        out = list(rhythm)
        for i in range(1, len(out), 2):
            if out[i] and i + 1 < len(out):
                out[i] = False
                out[i + 1] = True
        return {"rhythm": out, "swing": swing}
    except Exception as exc:
        return _error("swing_failed", exc)


TOOLS = [
    {"name": "granular_synthesize", "description": "Granular re-synthesis: spawn grains from a source buffer.",
     "params": {"samples": "array[float]", "grain_size": "float", "density": "float", "pitch": "float",
                "spread": "float", "position": "float", "jitter": "float", "duration": "float", "sample_rate": "int"},
     "run": granular_synthesize},
    {"name": "spectral_dft", "description": "Compute a DFT and return magnitudes, peak frequency and spectral centroid.",
     "params": {"samples": "array[float]", "sample_rate": "int", "max_bins": "int"}, "run": spectral_dft},
    {"name": "spectral_freeze", "description": "Freeze the spectral frame of audio and sustain it.",
     "params": {"samples": "array[float]", "freeze": "float", "sample_rate": "int"}, "run": spectral_freeze},
    {"name": "harmonic_analysis", "description": "Estimate the amplitude of each harmonic of a fundamental frequency.",
     "params": {"samples": "array[float]", "fundamental": "float", "sample_rate": "int", "harmonics": "int"},
     "run": harmonic_analysis},
    {"name": "detect_pitch_autocorrelation", "description": "Estimate fundamental pitch via autocorrelation.",
     "params": {"samples": "array[float]", "sample_rate": "int", "min_freq": "float", "max_freq": "float"},
     "run": detect_pitch_autocorrelation},
    {"name": "generate_counterpoint", "description": "Generate a species-1 counterpoint line above a melody.",
     "params": {"melody": "array[int]", "species": "int", "key": "string", "scale_type": "string"},
     "run": generate_counterpoint},
    {"name": "generate_fugue", "description": "Generate a fugue skeleton (subject + answer + voices) from a subject.",
     "params": {"subject": "array[int]", "key": "string", "scale_type": "string", "voices": "int", "entries": "int"},
     "run": generate_fugue},
    {"name": "markov_melody", "description": "Generate a melody from a Markov chain trained on seed notes.",
     "params": {"seed_notes": "array[int]", "length": "int", "order": "int"}, "run": markov_melody},
    {"name": "generate_scales_full", "description": "Return all available scales and their interval structures.",
     "params": {}, "run": generate_scales_full},
    {"name": "chord_voicing", "description": "Voice a chord (close, drop2, drop3, open, spread).",
     "params": {"chord": "array[int]", "voicing": "string"}, "run": chord_voicing},
    {"name": "write_wav", "description": "Write 16-bit PCM mono WAV file from float samples.",
     "params": {"samples": "array[float]", "path": "string", "sample_rate": "int", "normalize": "bool"},
     "run": write_wav},
    {"name": "apply_distortion", "description": "Soft-clip distortion (tanh) with tone control.",
     "params": {"samples": "array[float]", "drive": "float", "tone": "float", "mix": "float"}, "run": apply_distortion},
    {"name": "apply_chorus", "description": "LFO-modulated delay chorus effect.",
     "params": {"samples": "array[float]", "rate": "float", "depth": "float", "mix": "float", "sample_rate": "int"},
     "run": apply_chorus},
    {"name": "apply_compressor", "description": "Feed-forward compressor with attack/release envelope.",
     "params": {"samples": "array[float]", "threshold": "float", "ratio": "float", "attack": "float",
                "release": "float", "makeup": "float", "sample_rate": "int"}, "run": apply_compressor},
    {"name": "generate_polyrhythm", "description": "Generate a polyrhythm from a list of pulse counts per track.",
     "params": {"patterns": "array[int]", "steps": "int"}, "run": generate_polyrhythm},
    {"name": "swing_quantize", "description": "Apply swing to a 16-step rhythm.",
     "params": {"rhythm": "array[bool]", "swing": "float"}, "run": swing_quantize},
]
