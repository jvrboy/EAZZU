"""Vinny Pro — 15 advanced AI music generation and arrangement tools.

Extends Vinny with sophisticated composition: counter-melody generation,
harmonic motion planning, genre-aware arrangement, adaptive variation,
canon/fugue construction, and intelligent orchestration suggestions.
All pure-Python, stdlib-only.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional

from eazzu.audio.engine import NOTE_NAMES, SCALES
from eazzu.audio.advanced_music import (
    EXTENDED_SCALES, CHORD_FORMULAS, build_chord, diatonic_chords,
    neo_riemannian_transform, harmonic_field, modulation_path,
    circle_of_fifths,
)
from eazzu.audio.vinny_extended import (
    generate_ai_melody, generate_chord_progression, generate_drum_pattern,
    generate_arpeggio, generate_bass_line, generate_euclidean_rhythm,
    generate_song_structure, find_scales, harmonize,
    optimize_voice_leading,
)


def generate_counter_melody(melody: List[List[int]], key: str = "C",
                             scale_type: str = "major", bars: int = 4) -> Dict[str, Any]:
    """Generate a counter-melody that complements an existing melody.

    The counter-melody moves in contrary motion where possible, uses
    consonant intervals (3rds, 5ths, 6ths), and avoids parallel octaves.
    """
    scale = EXTENDED_SCALES.get(scale_type, SCALES.get(scale_type, SCALES["major"]))
    ki = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
    counter = []
    for bar_idx, bar in enumerate(melody[:bars]):
        cp_bar = []
        for i, note in enumerate(bar):
            if note < 0:
                cp_bar.append(-1)
                continue
            if i > 0 and bar[i - 1] >= 0:
                direction = -1 if note > bar[i - 1] else 1
            else:
                direction = random.choice([-1, 1])
            intervals = [3, 5, 7, 9, 12]
            iv = random.choice(intervals)
            cp_note = note + iv * direction
            pc = (cp_note - ki) % 12
            scale_pcs = [iv2 % 12 for iv2 in scale]
            if pc not in scale_pcs:
                cp_note += 1 if direction > 0 else -1
            cp_note = max(0, min(127, cp_note))
            cp_bar.append(cp_note)
        counter.append(cp_bar)
    return {"key": key, "scale": scale_type, "counter_melody": counter}


def generate_canon(theme: List[List[int]], voices: int = 2, interval: int = 2,
                   key: str = "C") -> Dict[str, Any]:
    """Generate a canon from a theme: each voice enters after a delay, transposed.

    interval = bars of delay between voice entries.
    """
    all_voices = []
    for v in range(voices):
        voice = []
        for _ in range(v * interval):
            voice.append([-1] * len(theme[0]) if theme else [])
        for bar in theme:
            voice.append(list(bar))
        all_voices.append(voice)
    max_len = max(len(v) for v in all_voices)
    for v in all_voices:
        while len(v) < max_len:
            v.append([-1] * len(theme[0]) if theme else [])
    return {"key": key, "voices": voices, "interval_bars": interval, "canon": all_voices}


def generate_fugue(subject: List[int], key: str = "C", scale_type: str = "major",
                   voices: int = 4) -> Dict[str, Any]:
    """Generate a basic fugue exposition from a subject.

    Each voice enters with the subject (or its transposition/inversion),
    staggered, creating a standard fugal exposition.
    """
    answer = [(s - 7) % 12 + 60 for s in subject]
    entries = []
    for v in range(voices):
        if v % 2 == 0:
            entry = [s + v * 12 for s in subject]
        else:
            entry = [a + v * 12 for a in answer]
        entries.append({"voice": v + 1, "entry": entry, "type": "subject" if v % 2 == 0 else "answer"})
    return {"key": key, "scale": scale_type, "voices": voices, "exposition": entries}


def generate_chord_melody(chords: List[Dict[str, str]], key: str = "C",
                          scale_type: str = "major") -> Dict[str, Any]:
    """Generate a melody that outlines a given chord progression (chord-melody style).

    Each bar arpeggiates the chord tones with passing notes from the scale.
    """
    scale = EXTENDED_SCALES.get(scale_type, SCALES.get(scale_type, SCALES["major"]))
    ki = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
    melody = []
    for chord in chords:
        root = chord.get("root", "C")
        ctype = chord.get("type", "maj")
        chord_data = build_chord(root, ctype, octave=5)
        chord_tones = chord_data.get("midi_notes", [60, 64, 67])
        bar = []
        for i in range(8):
            if random.random() < 0.7:
                bar.append(random.choice(chord_tones))
            else:
                pc = (ki + random.choice(scale)) % 12
                bar.append(pc + 60)
        melody.append(bar)
    return {"key": key, "scale": scale_type, "chords": chords, "melody": melody}


def generate_walking_bass(chords: List[Dict[str, str]], key: str = "C",
                          bpm: int = 120) -> Dict[str, Any]:
    """Generate a jazz walking bass line over a chord progression.

    Uses chord tones on beats 1 and 3, scale/approach tones on beats 2 and 4.
    """
    bass = []
    prev_note = 36
    for chord in chords:
        root = chord.get("root", "C")
        ctype = chord.get("type", "maj")
        chord_data = build_chord(root, ctype, octave=3)
        tones = chord_data.get("midi_notes", [36, 40, 43])
        bar = [tones[0], tones[1] if len(tones) > 1 else tones[0] + 7,
               tones[-1], tones[0] + 12 if random.random() < 0.5 else tones[1] + 12 if len(tones) > 1 else tones[0] + 7]
        if abs(bar[0] - prev_note) > 7:
            bar[0] = bar[0] - 12 if bar[0] > prev_note else bar[0] + 12
        bar = [max(24, min(84, n)) for n in bar]
        bass.append(bar)
        prev_note = bar[-1]
    return {"key": key, "bpm": bpm, "chords": chords, "walking_bass": bass}


def generate_ostinato(pattern: List[int], key: str = "C", scale_type: str = "major",
                      bars: int = 4, variations: int = 2) -> Dict[str, Any]:
    """Generate an ostinato pattern with rhythmic and melodic variations."""
    scale = EXTENDED_SCALES.get(scale_type, SCALES.get(scale_type, SCALES["major"]))
    ki = NOTE_NAMES.index(key) if key in NOTE_NAMES else 0
    all_variations = []
    for v in range(variations + 1):
        var = []
        for bar in range(bars):
            bar_notes = []
            for p in pattern:
                if p < 0:
                    bar_notes.append(-1)
                else:
                    pc = (ki + scale[(p + v + bar) % len(scale)]) % 12
                    bar_notes.append(pc + 48 + (v * 12 if v > 0 else 0))
            var.append(bar_notes)
        all_variations.append({"variation": v, "pattern": var})
    return {"key": key, "scale": scale_type, "ostinato_variations": all_variations}


def generate_pad_layer(key: str = "C", scale_type: str = "major", bars: int = 4,
                       chord_type: str = "maj9") -> Dict[str, Any]:
    """Generate a sustained pad/synth layer that holds chord tones across bars."""
    diatonic = diatonic_chords(key, scale_type)
    triads = diatonic.get("triads", [])
    pad = []
    for i in range(bars):
        triad = triads[i % len(triads)] if triads else {"root": key, "type": chord_type}
        chord_data = build_chord(triad["root"], chord_type, octave=4)
        pad.append({
            "bar": i + 1,
            "chord": f"{triad['root']}{chord_type}",
            "notes": chord_data.get("midi_notes", []),
            "duration_bars": 1,
        })
    return {"key": key, "scale": scale_type, "chord_type": chord_type, "pad": pad}


def generate_arp_pattern(chord_root: str, chord_type: str = "maj7", pattern: str = "updown",
                         octaves: int = 2, steps: int = 16) -> Dict[str, Any]:
    """Generate an arpeggio pattern for a chord with various patterns."""
    chord_data = build_chord(chord_root, chord_type, octave=4)
    chord_tones = chord_data.get("midi_notes", [60, 64, 67])
    all_tones = []
    for o in range(octaves):
        all_tones.extend([t + o * 12 for t in chord_tones])
    arp = []
    for i in range(steps):
        if pattern == "up":
            idx = i % len(all_tones)
        elif pattern == "down":
            idx = len(all_tones) - 1 - (i % len(all_tones))
        elif pattern == "updown":
            cycle = 2 * len(all_tones)
            pos = i % cycle
            idx = pos if pos < len(all_tones) else cycle - 1 - pos
        elif pattern == "random":
            idx = random.randint(0, len(all_tones) - 1)
        else:
            idx = i % len(all_tones)
        arp.append(all_tones[idx])
    return {"chord": f"{chord_root}{chord_type}", "pattern": pattern, "arpeggio": arp}


def generate_drum_fill(bars: int = 1, steps_per_bar: int = 16, intensity: float = 0.8) -> Dict[str, Any]:
    """Generate a drum fill pattern with increasing density."""
    fill = []
    total_steps = bars * steps_per_bar
    for i in range(4):
        voice = []
        for s in range(total_steps):
            progress = s / total_steps
            threshold = intensity * (0.3 + 0.7 * progress)
            voice.append(random.random() < threshold)
        fill.append(voice)
    return {"bars": bars, "steps_per_bar": steps_per_bar, "intensity": intensity, "fill": fill}


def generate_song_arrangement(genre: str = "pop", sections: int = 8) -> Dict[str, Any]:
    """Generate a full song arrangement with section types, energy levels, and instrument layers."""
    structure = generate_song_structure(genre)
    arrangement = []
    for i, section in enumerate(structure[:sections]):
        name = section.get("name", "verse")
        energy = section.get("energy", 0.5)
        layers = []
        if energy > 0.4:
            layers.append("drums")
        if energy > 0.3:
            layers.append("bass")
        if energy > 0.5:
            layers.append("chords")
        if energy > 0.6:
            layers.append("lead_melody")
        if energy > 0.8:
            layers.append("counter_melody")
        if name == "intro" or name == "outro":
            layers = ["pad"] if energy < 0.4 else layers
        if name == "break":
            layers = ["pad", "ambient"]
        arrangement.append({
            "section": name,
            "bars": section.get("bars", 8),
            "energy": energy,
            "instrument_layers": layers,
            "bpm_suggestion": 120 + int(energy * 30),
        })
    return {"genre": genre, "arrangement": arrangement}


def generate_modulation_progression(from_key: str, to_key: str, bars: int = 4) -> Dict[str, Any]:
    """Generate a chord progression that modulates from one key to another."""
    path = modulation_path(from_key, to_key)
    pivot = path.get("pivot_chords", [])
    progression = []
    from_diatonic = diatonic_chords(from_key, "major")
    to_diatonic = diatonic_chords(to_key, "major")
    from_triads = from_diatonic.get("triads", [])
    to_triads = to_diatonic.get("triads", [])
    for i in range(bars):
        if i < bars // 2:
            triad = from_triads[i % len(from_triads)] if from_triads else {"root": from_key, "type": "maj"}
        elif pivot and i == bars // 2:
            triad = {"root": pivot[0]["chord"], "type": "maj"}
        else:
            triad = to_triads[i % len(to_triads)] if to_triads else {"root": to_key, "type": "maj"}
        progression.append({"root": triad["root"], "type": triad["type"]})
    return {"from_key": from_key, "to_key": to_key, "bars": bars, "progression": progression}


def generate_genre_dna(genre: str) -> Dict[str, Any]:
    """Return the 'DNA' of a genre: typical BPM, scales, chord types, instruments, and structure."""
    genre_map = {
        "pop": {"bpm": (100, 130), "scales": ["major", "pentatonic_major"], "chords": ["maj", "min", "7"],
                "instruments": ["piano", "guitar", "synth", "drums"], "structure": "ABABCB"},
        "trap": {"bpm": (130, 170), "scales": ["natural_minor", "phrygian"], "chords": ["min", "min7", "7"],
                 "instruments": ["808_bass", "hihats", "snare", "pad"], "structure": "ABAB"},
        "house": {"bpm": (120, 130), "scales": ["major", "dorian"], "chords": ["maj7", "min7", "9"],
                  "instruments": ["four_on_floor", "bass", "synth", "hat"], "structure": "ABAB"},
        "lofi": {"bpm": (70, 90), "scales": ["dorian", "natural_minor"], "chords": ["maj7", "min7", "9"],
                 "instruments": ["piano", "vinyl_crackle", "bass", "soft_drums"], "structure": "ABAB"},
        "techno": {"bpm": (125, 150), "scales": ["phrygian", "whole_tone"], "chords": ["min", "min7"],
                   "instruments": ["kick", "hat", "bass", "synth"], "structure": "ABAB"},
        "jazz": {"bpm": (80, 200), "scales": ["dorian", "mixolydian", "bebop_dorian"], "chords": ["maj7", "min7", "7", "m7b5"],
                 "instruments": ["piano", "bass", "drums", "sax"], "structure": "AABA"},
        "dnb": {"bpm": (160, 180), "scales": ["natural_minor", "phrygian"], "chords": ["min", "min7"],
                "instruments": ["breakbeat", "sub_bass", "synth", "atmosphere"], "structure": "ABAB"},
        "ambient": {"bpm": (60, 90), "scales": ["major", "lydian", "whole_tone"], "chords": ["maj7", "maj9", "add9"],
                    "instruments": ["pad", "reverb", "texture", "drone"], "structure": "through_composed"},
    }
    dna = genre_map.get(genre, genre_map["pop"])
    return {"genre": genre, **dna}


def generate_melody_variation(melody: List[List[int]], variation_type: str = "ornament",
                               intensity: float = 0.3) -> Dict[str, Any]:
    """Generate a variation of a melody: ornamentation, rhythmic displacement, or interval expansion."""
    varied = []
    for bar in melody:
        v_bar = []
        for i, note in enumerate(bar):
            if note < 0:
                v_bar.append(-1)
                continue
            if variation_type == "ornament" and random.random() < intensity:
                v_bar.append(note + random.choice([1, -1]))
                v_bar.append(note)
            elif variation_type == "displace" and random.random() < intensity:
                v_bar.append(note + 12 if random.random() < 0.5 else note - 12)
            elif variation_type == "expand" and random.random() < intensity:
                v_bar.append(note + random.choice([2, -2, 3, -3]))
            else:
                v_bar.append(note)
            v_bar = [max(0, min(127, n)) if n >= 0 else -1 for n in v_bar]
        varied.append(v_bar)
    return {"variation_type": variation_type, "intensity": intensity, "varied_melody": varied}


def generate_harmonic_rhythm(chords: List[Dict[str, str]], bpm: int = 120) -> Dict[str, Any]:
    """Plan the harmonic rhythm: how many bars each chord lasts based on genre energy."""
    rhythm = []
    for i, chord in enumerate(chords):
        if i == 0 or i == len(chords) - 1:
            bars = 2
        elif chord.get("type") in ("7", "9", "dim7", "m7b5"):
            bars = 1
        else:
            bars = 2 if random.random() < 0.6 else 1
        rhythm.append({"chord": f"{chord.get('root','C')}{chord.get('type','maj')}", "bars": bars})
    total_bars = sum(r["bars"] for r in rhythm)
    return {"bpm": bpm, "harmonic_rhythm": rhythm, "total_bars": total_bars,
            "total_seconds": round(total_bars * 4 * 60 / bpm, 1)}


def generate_intelligent_orchestration(melody: List[List[int]], genre: str = "pop",
                                       energy: float = 0.7) -> Dict[str, Any]:
    """Suggest orchestration: which instruments play what, based on melody and genre."""
    dna = generate_genre_dna(genre)
    instruments = dna.get("instruments", ["piano", "bass", "drums"])
    orchestration = {}
    for inst in instruments:
        if inst in ("piano", "guitar", "synth"):
            orchestration[inst] = {"role": "harmony", "plays": "chords", "octave": 4}
        elif inst in ("bass", "808_bass", "sub_bass"):
            orchestration[inst] = {"role": "foundation", "plays": "bass_line", "octave": 2}
        elif inst in ("drums", "soft_drums", "breakbeat", "four_on_floor"):
            orchestration[inst] = {"role": "rhythm", "plays": "drum_pattern", "octave": None}
        elif inst in ("pad", "reverb", "texture", "drone"):
            orchestration[inst] = {"role": "atmosphere", "plays": "sustained_chords", "octave": 3}
        elif inst in ("sax", "lead_melody", "counter_melody"):
            orchestration[inst] = {"role": "melody", "plays": "melody", "octave": 5}
        else:
            orchestration[inst] = {"role": "support", "plays": "varies", "octave": 4}
    return {"genre": genre, "energy": energy, "orchestration": orchestration}
