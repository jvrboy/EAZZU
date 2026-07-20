"""Advanced Music Theory Engine — 20 professional music theory functions.

Extends Vinny with deeper harmonic analysis, counterpoint, Neo-Riemannian
transformations, set theory, serialism, and advanced rhythmic generation.
All pure-Python, stdlib-only.
"""
from __future__ import annotations

import math
import random
from typing import Any, Dict, List, Optional, Tuple

from eazzu.audio.engine import NOTE_NAMES, SCALES

# ─── Extended scale library ──────────────────────────────────────────────

EXTENDED_SCALES: Dict[str, List[int]] = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "natural_minor": [0, 2, 3, 5, 7, 8, 10],
    "harmonic_minor": [0, 2, 3, 5, 7, 8, 11],
    "melodic_minor": [0, 2, 3, 5, 7, 9, 11],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
    "pentatonic_major": [0, 2, 4, 7, 9],
    "pentatonic_minor": [0, 3, 5, 7, 10],
    "blues": [0, 3, 5, 6, 7, 10],
    "whole_tone": [0, 2, 4, 6, 8, 10],
    "diminished": [0, 2, 3, 5, 6, 8, 9, 11],
    "augmented": [0, 3, 4, 7, 8, 11],
    "bebop_major": [0, 2, 4, 5, 7, 9, 10, 11],
    "bebop_dorian": [0, 2, 3, 4, 5, 7, 9, 10],
    "bebop_mixolydian": [0, 2, 4, 5, 7, 9, 10, 11],
    "hungarian_minor": [0, 2, 3, 6, 7, 8, 11],
    "byzantine": [0, 1, 4, 5, 7, 8, 11],
    "enigmatic": [0, 1, 4, 6, 8, 10, 11],
    "persian": [0, 1, 4, 5, 6, 8, 11],
    "hirajoshi": [0, 2, 3, 7, 8],
    "in_sen": [0, 1, 5, 7, 10],
    "iwato": [0, 1, 5, 6, 10],
}

# ─── Chord library ───────────────────────────────────────────────────────

CHORD_FORMULAS: Dict[str, List[int]] = {
    "maj": [0, 4, 7], "min": [0, 3, 7], "dim": [0, 3, 6],
    "aug": [0, 4, 8], "sus2": [0, 2, 7], "sus4": [0, 5, 7],
    "maj7": [0, 4, 7, 11], "min7": [0, 3, 7, 10], "7": [0, 4, 7, 10],
    "dim7": [0, 3, 6, 9], "m7b5": [0, 3, 6, 10], "maj9": [0, 4, 7, 11, 14],
    "min9": [0, 3, 7, 10, 14], "9": [0, 4, 7, 10, 14], "7b9": [0, 4, 7, 10, 13],
    "7#9": [0, 4, 7, 10, 15], "6": [0, 4, 7, 9], "m6": [0, 3, 7, 9],
    "add9": [0, 4, 7, 14], "6/9": [0, 4, 7, 9, 14], "maj11": [0, 4, 7, 11, 14, 17],
    "min11": [0, 3, 7, 10, 14, 17], "11": [0, 4, 7, 10, 14, 17],
    "maj13": [0, 4, 7, 11, 14, 17, 21], "min13": [0, 3, 7, 10, 14, 17, 21],
    "13": [0, 4, 7, 10, 14, 17, 21], "lydian_dominant": [0, 4, 7, 10, 14, 18],
}

# ─── Functions ──────────────────────────────────────────────────────────


def list_all_scales() -> Dict[str, Any]:
    """List all available scales with their interval formulas."""
    return {"scales": {name: {"intervals": iv, "notes": len(iv)} for name, iv in EXTENDED_SCALES.items()}}


def list_all_chords() -> Dict[str, Any]:
    """List all available chord types with their interval formulas."""
    return {"chords": {name: {"intervals": iv, "notes": len(iv)} for name, iv in CHORD_FORMULAS.items()}}


def build_chord(root: str, chord_type: str = "maj", octave: int = 4) -> Dict[str, Any]:
    """Build a chord from a root note name and chord type."""
    if root not in NOTE_NAMES:
        return {"error": f"unknown root: {root}"}
    if chord_type not in CHORD_FORMULAS:
        return {"error": f"unknown chord type: {chord_type}"}
    root_idx = NOTE_NAMES.index(root)
    intervals = CHORD_FORMULAS[chord_type]
    midi_notes = [root_idx + iv + octave * 12 for iv in intervals]
    note_names = [NOTE_NAMES[n % 12] for n in midi_notes]
    return {
        "root": root, "type": chord_type, "octave": octave,
        "midi_notes": midi_notes, "note_names": note_names,
        "frequencies": [440.0 * 2 ** ((n - 69) / 12) for n in midi_notes],
    }


def analyze_chord(notes: List[int]) -> Dict[str, Any]:
    """Analyze a collection of MIDI notes and identify the chord."""
    if not notes:
        return {"error": "no_notes"}
    pitch_classes = sorted(set(n % 12 for n in notes))
    best_match = None
    best_score = -1
    for root_pc in pitch_classes:
        normalized = sorted(set((n - root_pc) % 12 for n in notes))
        for name, formula in CHORD_FORMULAS.items():
            formula_set = set(iv % 12 for iv in formula)
            note_set = set(normalized)
            score = len(formula_set & note_set) - len(note_set - formula_set) * 0.5
            if score > best_score:
                best_score = score
                best_match = {"root_pc": root_pc, "root": NOTE_NAMES[root_pc], "type": name, "score": score}
    return {
        "input_notes": notes,
        "pitch_classes": pitch_classes,
        "pitch_class_names": [NOTE_NAMES[pc] for pc in pitch_classes],
        "best_match": best_match,
    }


def get_scale_notes(key: str, scale_name: str = "major", octaves: int = 2) -> Dict[str, Any]:
    """Get all notes in a scale across N octaves."""
    if key not in NOTE_NAMES:
        return {"error": f"unknown key: {key}"}
    scale = EXTENDED_SCALES.get(scale_name) or SCALES.get(scale_name)
    if not scale:
        return {"error": f"unknown scale: {scale_name}"}
    root_idx = NOTE_NAMES.index(key)
    notes = []
    for o in range(octaves):
        for iv in scale:
            midi = root_idx + iv + o * 12
            notes.append({"midi": midi, "name": NOTE_NAMES[midi % 12], "octave": o})
    return {"key": key, "scale": scale_name, "notes": notes}


def diatonic_chords(key: str, scale_name: str = "major") -> Dict[str, Any]:
    """Generate diatonic triads and sevenths for a scale."""
    scale = EXTENDED_SCALES.get(scale_name) or SCALES.get(scale_name)
    if not scale:
        return {"error": f"unknown scale: {scale_name}"}
    if key not in NOTE_NAMES:
        return {"error": f"unknown key: {key}"}
    root_idx = NOTE_NAMES.index(key)
    triads = []
    sevenths = []
    for degree in range(len(scale)):
        root_pc = (root_idx + scale[degree]) % 12
        third = (root_idx + scale[(degree + 2) % len(scale)] + 12 * ((degree + 2) >= len(scale))) % 12
        fifth = (root_idx + scale[(degree + 4) % len(scale)] + 12 * ((degree + 4) >= len(scale))) % 12
        seventh = (root_idx + scale[(degree + 6) % len(scale)] + 12 * ((degree + 6) >= len(scale))) % 12
        third_iv = (third - root_pc) % 12
        fifth_iv = (fifth - root_pc) % 12
        seventh_iv = (seventh - root_pc) % 12
        if third_iv == 4 and fifth_iv == 7:
            triad_type = "maj"
        elif third_iv == 3 and fifth_iv == 7:
            triad_type = "min"
        elif third_iv == 3 and fifth_iv == 6:
            triad_type = "dim"
        elif third_iv == 4 and fifth_iv == 8:
            triad_type = "aug"
        else:
            triad_type = "other"
        if seventh_iv == 11:
            seventh_type = triad_type + "7" if triad_type == "maj" else "maj7"
        elif seventh_iv == 10:
            seventh_type = triad_type + "7" if triad_type in ("maj", "min") else "7"
        elif seventh_iv == 9:
            seventh_type = "dim7" if triad_type == "dim" else "m7b5"
        else:
            seventh_type = triad_type + "7"
        triads.append({"degree": degree + 1, "root": NOTE_NAMES[root_pc], "type": triad_type})
        sevenths.append({"degree": degree + 1, "root": NOTE_NAMES[root_pc], "type": seventh_type})
    return {"key": key, "scale": scale_name, "triads": triads, "sevenths": sevenths}


def roman_numeral_analysis(key: str, scale_name: str, chord_root: str, chord_type: str) -> Dict[str, Any]:
    """Determine the Roman numeral for a chord within a key."""
    scale = EXTENDED_SCALES.get(scale_name) or SCALES.get(scale_name)
    if not scale or key not in NOTE_NAMES or chord_root not in NOTE_NAMES:
        return {"error": "invalid input"}
    root_idx = NOTE_NAMES.index(key)
    chord_idx = NOTE_NAMES.index(chord_root)
    scale_pcs = [(root_idx + iv) % 12 for iv in scale]
    if chord_idx not in scale_pcs:
        return {"error": "chord_root not in scale"}
    degree = scale_pcs.index(chord_idx) + 1
    roman = ["I", "II", "III", "IV", "V", "VI", "VII"][degree - 1]
    is_minor = chord_type in ("min", "min7", "m7b5", "dim", "dim7")
    is_dim = chord_type in ("dim", "dim7", "m7b5")
    if is_dim:
        roman = roman.lower() + "°"
    elif is_minor:
        roman = roman.lower()
    return {"key": key, "scale": scale_name, "chord": f"{chord_root}{chord_type}", "roman_numeral": roman, "degree": degree}


def secondary_dominant(key: str, scale_name: str, target_degree: int) -> Dict[str, Any]:
    """Find the secondary dominant (V/X) for a target scale degree."""
    scale = EXTENDED_SCALES.get(scale_name) or SCALES.get(scale_name)
    if not scale or key not in NOTE_NAMES:
        return {"error": "invalid input"}
    root_idx = NOTE_NAMES.index(key)
    if target_degree < 1 or target_degree > len(scale):
        return {"error": "invalid degree"}
    target_pc = (root_idx + scale[target_degree - 1]) % 12
    dom_pc = (target_pc + 7) % 12
    return {
        "key": key, "target_degree": target_degree, "target_chord": NOTE_NAMES[target_pc],
        "secondary_dominant": NOTE_NAMES[dom_pc], "secondary_dominant_type": "7",
    }


def chord_progression_analyzer(progression: List[Dict[str, str]]) -> Dict[str, Any]:
    """Analyze a chord progression for harmonic function, movement, and quality."""
    functions = []
    for i, chord in enumerate(progression):
        root = chord.get("root", "")
        ctype = chord.get("type", "maj")
        if i == 0:
            function = "tonic"
        elif ctype in ("7", "9", "13"):
            function = "dominant" if root in ("G", "D", "A", "E") else "subdominant"
        elif ctype in ("min", "min7"):
            function = "submediant" if root in ("A", "E") else "subdominant"
        elif ctype in ("dim", "dim7"):
            function = "leading_tone"
        else:
            function = "subdominant" if root in ("F", "B") else "tonic"
        functions.append({"chord": f"{root}{ctype}", "function": function})
    movements = []
    for i in range(1, len(progression)):
        prev = progression[i - 1].get("root", "")
        curr = progression[i].get("root", "")
        if prev and curr and prev in NOTE_NAMES and curr in NOTE_NAMES:
            interval = (NOTE_NAMES.index(curr) - NOTE_NAMES.index(prev)) % 12
            direction = "up" if interval <= 6 else "down"
            movements.append({"from": prev, "to": curr, "interval": interval, "direction": direction})
    return {
        "progression": [f"{c.get('root','')}{c.get('type','maj')}" for c in progression],
        "functions": functions,
        "movements": movements,
        "length": len(progression),
    }


def neo_riemannian_transform(chord_root: str, chord_type: str, transform: str = "P") -> Dict[str, Any]:
    """Apply a Neo-Riemannian transformation (P, R, L) to a chord.

    P = Parallel (maj↔min same root), R = Relative (maj→vi, min→III),
    L = Leading-tone exchange (maj→V of vi, min→IV of III).
    """
    if chord_root not in NOTE_NAMES:
        return {"error": "invalid root"}
    root_idx = NOTE_NAMES.index(chord_root)
    if transform == "P":
        new_type = "min" if chord_type == "maj" else "maj" if chord_type == "min" else chord_type
        new_root = chord_root
    elif transform == "R":
        if chord_type == "maj":
            new_root = NOTE_NAMES[(root_idx + 9) % 12]
            new_type = "min"
        elif chord_type == "min":
            new_root = NOTE_NAMES[(root_idx + 3) % 12]
            new_type = "maj"
        else:
            new_root, new_type = chord_root, chord_type
    elif transform == "L":
        if chord_type == "maj":
            new_root = NOTE_NAMES[(root_idx + 4) % 12]
            new_type = "min"
        elif chord_type == "min":
            new_root = NOTE_NAMES[(root_idx + 8) % 12]
            new_type = "maj"
        else:
            new_root, new_type = chord_root, chord_type
    else:
        return {"error": f"unknown transform: {transform} (use P, R, or L)"}
    return {"original": f"{chord_root}{chord_type}", "transform": transform, "result": f"{new_root}{new_type}",
            "new_root": new_root, "new_type": new_type}


def interval_matrix(notes: List[int]) -> Dict[str, Any]:
    """Compute the interval matrix (all pairwise intervals) for a set of notes."""
    if not notes:
        return {"error": "no_notes"}
    pcs = sorted(set(n % 12 for n in notes))
    matrix = []
    for a in pcs:
        row = [(b - a) % 12 for b in pcs]
        matrix.append(row)
    return {"pitch_classes": pcs, "names": [NOTE_NAMES[pc] for pc in pcs], "matrix": matrix}


def forte_set_class(notes: List[int]) -> Dict[str, Any]:
    """Compute the Forte set class (prime form) for a collection of pitch classes."""
    pcs = sorted(set(n % 12 for n in notes))
    if not pcs:
        return {"error": "no_notes"}
    n = len(pcs)
    rotations = []
    for i in range(n):
        rotated = sorted((pc - pcs[i]) % 12 for pc in pcs)
        rotations.append(rotated)
    inversions = [sorted((12 - iv) % 12 for iv in r) for r in rotations]
    inversions = [[v - min(inv) for v in inv] for inv in inversions]
    candidates = rotations + inversions
    prime = min(candidates)
    return {"input_pcs": pcs, "prime_form": prime, "cardinality": n}


def twelve_tone_row(start_pc: int = 0) -> Dict[str, Any]:
    """Generate a random twelve-tone row (serialism) starting at a given pitch class."""
    pcs = list(range(12))
    pcs.remove(start_pc)
    random.shuffle(pcs)
    row = [start_pc] + pcs
    return {"row": row, "names": [NOTE_NAMES[pc] for pc in row]}


def retrograde(row: List[int]) -> Dict[str, Any]:
    """Return the retrograde (reverse) of a tone row."""
    return {"original": row, "retrograde": list(reversed(row))}


def inversion(row: List[int], axis: int = 0) -> Dict[str, Any]:
    """Return the inversion of a tone row around a given axis."""
    return {"original": row, "inversion": [(axis * 2 - n) % 12 for n in row]}


def retrograde_inversion(row: List[int], axis: int = 0) -> Dict[str, Any]:
    """Return the retrograde inversion of a tone row."""
    inv = [(axis * 2 - n) % 12 for n in row]
    return {"original": row, "retrograde_inversion": list(reversed(inv))}


def polyrhythm_generator(pulses: List[int], steps: int = 16) -> Dict[str, Any]:
    """Generate polyrhythmic patterns for multiple pulse counts."""
    patterns = []
    for p in pulses:
        pattern = [i % p == 0 for i in range(steps)]
        patterns.append({"pulse": p, "pattern": pattern})
    return {"steps": steps, "patterns": patterns}


def cross_rhythm(base: int, cross: int, steps: int = 16) -> Dict[str, Any]:
    """Generate a cross-rhythm (e.g., 3 against 4) as boolean patterns."""
    base_pat = [i % base == 0 for i in range(steps)]
    cross_pat = [i % cross == 0 for i in range(steps)]
    coincidences = [a and b for a, b in zip(base_pat, cross_pat)]
    return {"base": base, "cross": cross, "base_pattern": base_pat, "cross_pattern": cross_pat,
            "coincidences": coincidences, "coincidence_count": sum(coincidences)}


def harmonic_field(key: str, scale_name: str = "major") -> Dict[str, Any]:
    """Generate the complete harmonic field: triads, sevenths, and extensions for every degree."""
    scale = EXTENDED_SCALES.get(scale_name) or SCALES.get(scale_name)
    if not scale or key not in NOTE_NAMES:
        return {"error": "invalid input"}
    root_idx = NOTE_NAMES.index(key)
    field = []
    for degree in range(len(scale)):
        root_pc = (root_idx + scale[degree]) % 12
        chord_pcs = [(root_idx + scale[(degree + 2 * k) % len(scale)] + 12 * ((degree + 2 * k) >= len(scale))) % 12
                     for k in range(1, 5)]
        field.append({
            "degree": degree + 1,
            "root": NOTE_NAMES[root_pc],
            "third": NOTE_NAMES[chord_pcs[0]],
            "fifth": NOTE_NAMES[chord_pcs[1]],
            "seventh": NOTE_NAMES[chord_pcs[2]],
            "ninth": NOTE_NAMES[chord_pcs[3]],
        })
    return {"key": key, "scale": scale_name, "harmonic_field": field}


def voice_leading(from_chord: List[int], to_chord: List[int]) -> Dict[str, Any]:
    """Compute optimal voice leading between two chords (minimize total movement)."""
    if not from_chord or not to_chord:
        return {"error": "no_notes"}
    mapping = []
    used = set()
    for fn in from_chord:
        best_tn = None
        best_d = 999
        best_j = 0
        for j, tn in enumerate(to_chord):
            if j in used:
                continue
            d = abs(fn - tn)
            if d < best_d:
                best_d = d
                best_tn = tn
                best_j = j
        if best_tn is not None:
            mapping.append({"from": fn, "to": best_tn, "distance": best_d})
            used.add(best_j)
    total = sum(m["distance"] for m in mapping)
    return {"from_chord": from_chord, "to_chord": to_chord, "mapping": mapping, "total_movement": total}


def counterpoint_species1(cantus: List[int]) -> Dict[str, Any]:
    """Generate a first-species counterpoint line above a given cantus firmus."""
    if not cantus:
        return {"error": "no_cantus"}
    consonant = [0, 3, 5, 7, 8, 10, 12]
    cp = []
    for i, note in enumerate(cantus):
        if i == 0 or i == len(cantus) - 1:
            cp.append(note + 12)
        else:
            choices = [note + iv for iv in consonant if 0 <= note + iv <= 127]
            cp.append(random.choice(choices) if choices else note + 12)
    return {"cantus": cantus, "counterpoint": cp, "species": 1}


def circle_of_fifths() -> Dict[str, Any]:
    """Return the circle of fifths with key signatures and relative minors."""
    fifths = []
    for i in range(12):
        pc = (i * 7) % 12
        rel_minor = (pc + 9) % 12
        fifths.append({
            "position": i,
            "major_key": NOTE_NAMES[pc],
            "relative_minor": NOTE_NAMES[rel_minor],
            "sharps": i if i <= 6 else 0,
            "flats": (12 - i) % 12 if i > 6 else 0,
        })
    return {"circle": fifths}


def modulation_path(from_key: str, to_key: str) -> Dict[str, Any]:
    """Suggest a modulation path between two keys via common chords."""
    if from_key not in NOTE_NAMES or to_key not in NOTE_NAMES:
        return {"error": "invalid key"}
    from_idx = NOTE_NAMES.index(from_key)
    to_idx = NOTE_NAMES.index(to_key)
    distance = abs(to_idx - from_idx) % 12
    min_dist = min(distance, 12 - distance)
    pivot_chords = []
    for i in range(7):
        from_pc = (from_idx + [0, 2, 4, 5, 7, 9, 11][i]) % 12
        for j in range(7):
            to_pc = (to_idx + [0, 2, 4, 5, 7, 9, 11][j]) % 12
            if from_pc == to_pc:
                pivot_chords.append({"chord": NOTE_NAMES[from_pc], "from_degree": i + 1, "to_degree": j + 1})
    return {"from_key": from_key, "to_key": to_key, "distance_semitones": min_dist, "pivot_chords": pivot_chords[:5]}
