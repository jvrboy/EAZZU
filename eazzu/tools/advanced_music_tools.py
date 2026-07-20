"""Advanced music tool wrappers — exposes the Advanced Music Theory Engine
and Vinny Pro to the EAZZU agent registry.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


# ─── Advanced Music Theory ──────────────────────────────────────────────

def list_all_scales() -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import list_all_scales as _f
        return _f()
    except Exception as exc:
        return _error("scales_list_failed", exc)


def list_all_chords() -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import list_all_chords as _f
        return _f()
    except Exception as exc:
        return _error("chords_list_failed", exc)


def build_chord(root: str, chord_type: str = "maj", octave: int = 4) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import build_chord as _f
        return _f(root, chord_type, octave)
    except Exception as exc:
        return _error("chord_build_failed", exc)


def analyze_chord(notes: List[int]) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import analyze_chord as _f
        return _f(notes)
    except Exception as exc:
        return _error("chord_analyze_failed", exc)


def get_scale_notes(key: str, scale_name: str = "major", octaves: int = 2) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import get_scale_notes as _f
        return _f(key, scale_name, octaves)
    except Exception as exc:
        return _error("scale_notes_failed", exc)


def diatonic_chords(key: str, scale_name: str = "major") -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import diatonic_chords as _f
        return _f(key, scale_name)
    except Exception as exc:
        return _error("diatonic_chords_failed", exc)


def roman_numeral_analysis(key: str, scale_name: str, chord_root: str, chord_type: str) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import roman_numeral_analysis as _f
        return _f(key, scale_name, chord_root, chord_type)
    except Exception as exc:
        return _error("roman_analysis_failed", exc)


def secondary_dominant(key: str, scale_name: str, target_degree: int) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import secondary_dominant as _f
        return _f(key, scale_name, target_degree)
    except Exception as exc:
        return _error("secondary_dominant_failed", exc)


def chord_progression_analyzer(progression: List[Dict[str, str]]) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import chord_progression_analyzer as _f
        return _f(progression)
    except Exception as exc:
        return _error("progression_analysis_failed", exc)


def neo_riemannian_transform(chord_root: str, chord_type: str, transform: str = "P") -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import neo_riemannian_transform as _f
        return _f(chord_root, chord_type, transform)
    except Exception as exc:
        return _error("neo_riemannian_failed", exc)


def interval_matrix(notes: List[int]) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import interval_matrix as _f
        return _f(notes)
    except Exception as exc:
        return _error("interval_matrix_failed", exc)


def forte_set_class(notes: List[int]) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import forte_set_class as _f
        return _f(notes)
    except Exception as exc:
        return _error("forte_set_failed", exc)


def twelve_tone_row(start_pc: int = 0) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import twelve_tone_row as _f
        return _f(start_pc)
    except Exception as exc:
        return _error("tone_row_failed", exc)


def tone_row_transformations(row: List[int], axis: int = 0) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import retrograde, inversion, retrograde_inversion
        return {
            "original": row,
            "retrograde": retrograde(row)["retrograde"],
            "inversion": inversion(row, axis)["inversion"],
            "retrograde_inversion": retrograde_inversion(row, axis)["retrograde_inversion"],
        }
    except Exception as exc:
        return _error("tone_row_transform_failed", exc)


def polyrhythm_generator(pulses: List[int], steps: int = 16) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import polyrhythm_generator as _f
        return _f(pulses, steps)
    except Exception as exc:
        return _error("polyrhythm_failed", exc)


def cross_rhythm(base: int, cross: int, steps: int = 16) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import cross_rhythm as _f
        return _f(base, cross, steps)
    except Exception as exc:
        return _error("cross_rhythm_failed", exc)


def harmonic_field(key: str, scale_name: str = "major") -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import harmonic_field as _f
        return _f(key, scale_name)
    except Exception as exc:
        return _error("harmonic_field_failed", exc)


def counterpoint_species1(cantus: List[int]) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import counterpoint_species1 as _f
        return _f(cantus)
    except Exception as exc:
        return _error("counterpoint_failed", exc)


def circle_of_fifths() -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import circle_of_fifths as _f
        return _f()
    except Exception as exc:
        return _error("circle_of_fifths_failed", exc)


def modulation_path_tool(from_key: str, to_key: str) -> Dict[str, Any]:
    try:
        from eazzu.audio.advanced_music import modulation_path as _f
        return _f(from_key, to_key)
    except Exception as exc:
        return _error("modulation_path_failed", exc)


# ─── Vinny Pro ───────────────────────────────────────────────────────────

def generate_counter_melody(melody: List[List[int]], key: str = "C",
                             scale_type: str = "major", bars: int = 4) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_counter_melody as _f
        return _f(melody, key, scale_type, bars)
    except Exception as exc:
        return _error("counter_melody_failed", exc)


def generate_canon(theme: List[List[int]], voices: int = 2, interval: int = 2,
                   key: str = "C") -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_canon as _f
        return _f(theme, voices, interval, key)
    except Exception as exc:
        return _error("canon_failed", exc)


def generate_fugue(subject: List[int], key: str = "C", scale_type: str = "major",
                   voices: int = 4) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_fugue as _f
        return _f(subject, key, scale_type, voices)
    except Exception as exc:
        return _error("fugue_failed", exc)


def generate_chord_melody(chords: List[Dict[str, str]], key: str = "C",
                          scale_type: str = "major") -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_chord_melody as _f
        return _f(chords, key, scale_type)
    except Exception as exc:
        return _error("chord_melody_failed", exc)


def generate_walking_bass(chords: List[Dict[str, str]], key: str = "C",
                          bpm: int = 120) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_walking_bass as _f
        return _f(chords, key, bpm)
    except Exception as exc:
        return _error("walking_bass_failed", exc)


def generate_ostinato(pattern: List[int], key: str = "C", scale_type: str = "major",
                      bars: int = 4, variations: int = 2) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_ostinato as _f
        return _f(pattern, key, scale_type, bars, variations)
    except Exception as exc:
        return _error("ostinato_failed", exc)


def generate_pad_layer(key: str = "C", scale_type: str = "major", bars: int = 4,
                       chord_type: str = "maj9") -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_pad_layer as _f
        return _f(key, scale_type, bars, chord_type)
    except Exception as exc:
        return _error("pad_layer_failed", exc)


def generate_arp_pattern(chord_root: str, chord_type: str = "maj7", pattern: str = "updown",
                         octaves: int = 2, steps: int = 16) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_arp_pattern as _f
        return _f(chord_root, chord_type, pattern, octaves, steps)
    except Exception as exc:
        return _error("arp_pattern_failed", exc)


def generate_drum_fill(bars: int = 1, steps_per_bar: int = 16, intensity: float = 0.8) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_drum_fill as _f
        return _f(bars, steps_per_bar, intensity)
    except Exception as exc:
        return _error("drum_fill_failed", exc)


def generate_song_arrangement(genre: str = "pop", sections: int = 8) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_song_arrangement as _f
        return _f(genre, sections)
    except Exception as exc:
        return _error("song_arrangement_failed", exc)


def generate_modulation_progression(from_key: str, to_key: str, bars: int = 4) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_modulation_progression as _f
        return _f(from_key, to_key, bars)
    except Exception as exc:
        return _error("modulation_progression_failed", exc)


def generate_genre_dna(genre: str) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_genre_dna as _f
        return _f(genre)
    except Exception as exc:
        return _error("genre_dna_failed", exc)


def generate_melody_variation(melody: List[List[int]], variation_type: str = "ornament",
                               intensity: float = 0.3) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_melody_variation as _f
        return _f(melody, variation_type, intensity)
    except Exception as exc:
        return _error("melody_variation_failed", exc)


def generate_harmonic_rhythm(chords: List[Dict[str, str]], bpm: int = 120) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_harmonic_rhythm as _f
        return _f(chords, bpm)
    except Exception as exc:
        return _error("harmonic_rhythm_failed", exc)


def generate_intelligent_orchestration(melody: List[List[int]], genre: str = "pop",
                                       energy: float = 0.7) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_pro import generate_intelligent_orchestration as _f
        return _f(melody, genre, energy)
    except Exception as exc:
        return _error("orchestration_failed", exc)


TOOLS = [
    # Advanced Music Theory
    {"name": "list_all_scales", "description": "List all available scales (25+ scales) with their interval formulas.",
     "params": {}, "run": list_all_scales},
    {"name": "list_all_chords", "description": "List all available chord types (25+) with their interval formulas.",
     "params": {}, "run": list_all_chords},
    {"name": "build_chord", "description": "Build a chord from a root note and chord type, returning MIDI notes, names, and frequencies.",
     "params": {"root": "string", "chord_type": "string", "octave": "int"}, "run": build_chord},
    {"name": "analyze_chord", "description": "Analyze a collection of MIDI notes and identify the chord (root, type, score).",
     "params": {"notes": "array[int]"}, "run": analyze_chord},
    {"name": "get_scale_notes", "description": "Get all notes in a scale across N octaves.",
     "params": {"key": "string", "scale_name": "string", "octaves": "int"}, "run": get_scale_notes},
    {"name": "diatonic_chords", "description": "Generate diatonic triads and sevenths for a key and scale.",
     "params": {"key": "string", "scale_name": "string"}, "run": diatonic_chords},
    {"name": "roman_numeral_analysis", "description": "Determine the Roman numeral for a chord within a key.",
     "params": {"key": "string", "scale_name": "string", "chord_root": "string", "chord_type": "string"}, "run": roman_numeral_analysis},
    {"name": "secondary_dominant", "description": "Find the secondary dominant (V/X) for a target scale degree.",
     "params": {"key": "string", "scale_name": "string", "target_degree": "int"}, "run": secondary_dominant},
    {"name": "chord_progression_analyzer", "description": "Analyze a chord progression for harmonic function, movement, and quality.",
     "params": {"progression": "array[object]"}, "run": chord_progression_analyzer},
    {"name": "neo_riemannian_transform", "description": "Apply a Neo-Riemannian transformation (P, R, L) to a chord.",
     "params": {"chord_root": "string", "chord_type": "string", "transform": "string"}, "run": neo_riemannian_transform},
    {"name": "interval_matrix", "description": "Compute the interval matrix (all pairwise intervals) for a set of notes.",
     "params": {"notes": "array[int]"}, "run": interval_matrix},
    {"name": "forte_set_class", "description": "Compute the Forte set class (prime form) for a collection of pitch classes.",
     "params": {"notes": "array[int]"}, "run": forte_set_class},
    {"name": "twelve_tone_row", "description": "Generate a random twelve-tone row (serialism) starting at a given pitch class.",
     "params": {"start_pc": "int"}, "run": twelve_tone_row},
    {"name": "tone_row_transformations", "description": "Apply retrograde, inversion, and retrograde-inversion to a tone row.",
     "params": {"row": "array[int]", "axis": "int"}, "run": tone_row_transformations},
    {"name": "polyrhythm_generator", "description": "Generate polyrhythmic patterns for multiple pulse counts.",
     "params": {"pulses": "array[int]", "steps": "int"}, "run": polyrhythm_generator},
    {"name": "cross_rhythm", "description": "Generate a cross-rhythm (e.g., 3 against 4) as boolean patterns.",
     "params": {"base": "int", "cross": "int", "steps": "int"}, "run": cross_rhythm},
    {"name": "harmonic_field", "description": "Generate the complete harmonic field: triads, sevenths, and extensions for every degree.",
     "params": {"key": "string", "scale_name": "string"}, "run": harmonic_field},
    {"name": "counterpoint_species1", "description": "Generate a first-species counterpoint line above a given cantus firmus.",
     "params": {"cantus": "array[int]"}, "run": counterpoint_species1},
    {"name": "circle_of_fifths", "description": "Return the circle of fifths with key signatures and relative minors.",
     "params": {}, "run": circle_of_fifths},
    {"name": "modulation_path", "description": "Suggest a modulation path between two keys via common (pivot) chords.",
     "params": {"from_key": "string", "to_key": "string"}, "run": modulation_path_tool},
    # Vinny Pro
    {"name": "generate_counter_melody", "description": "Generate a counter-melody that complements an existing melody with contrary motion.",
     "params": {"melody": "array[array[int]]", "key": "string", "scale_type": "string", "bars": "int"}, "run": generate_counter_melody},
    {"name": "generate_canon", "description": "Generate a canon from a theme: each voice enters after a delay.",
     "params": {"theme": "array[array[int]]", "voices": "int", "interval": "int", "key": "string"}, "run": generate_canon},
    {"name": "generate_fugue", "description": "Generate a basic fugue exposition from a subject.",
     "params": {"subject": "array[int]", "key": "string", "scale_type": "string", "voices": "int"}, "run": generate_fugue},
    {"name": "generate_chord_melody", "description": "Generate a melody that outlines a chord progression (chord-melody style).",
     "params": {"chords": "array[object]", "key": "string", "scale_type": "string"}, "run": generate_chord_melody},
    {"name": "generate_walking_bass", "description": "Generate a jazz walking bass line over a chord progression.",
     "params": {"chords": "array[object]", "key": "string", "bpm": "int"}, "run": generate_walking_bass},
    {"name": "generate_ostinato", "description": "Generate an ostinato pattern with rhythmic and melodic variations.",
     "params": {"pattern": "array[int]", "key": "string", "scale_type": "string", "bars": "int", "variations": "int"}, "run": generate_ostinato},
    {"name": "generate_pad_layer", "description": "Generate a sustained pad/synth layer holding chord tones across bars.",
     "params": {"key": "string", "scale_type": "string", "bars": "int", "chord_type": "string"}, "run": generate_pad_layer},
    {"name": "generate_arp_pattern", "description": "Generate an arpeggio pattern for a chord (up, down, updown, random).",
     "params": {"chord_root": "string", "chord_type": "string", "pattern": "string", "octaves": "int", "steps": "int"}, "run": generate_arp_pattern},
    {"name": "generate_drum_fill", "description": "Generate a drum fill pattern with increasing density.",
     "params": {"bars": "int", "steps_per_bar": "int", "intensity": "float"}, "run": generate_drum_fill},
    {"name": "generate_song_arrangement", "description": "Generate a full song arrangement with sections, energy levels, and instrument layers.",
     "params": {"genre": "string", "sections": "int"}, "run": generate_song_arrangement},
    {"name": "generate_modulation_progression", "description": "Generate a chord progression that modulates from one key to another.",
     "params": {"from_key": "string", "to_key": "string", "bars": "int"}, "run": generate_modulation_progression},
    {"name": "generate_genre_dna", "description": "Return the DNA of a genre: BPM, scales, chord types, instruments, and structure.",
     "params": {"genre": "string"}, "run": generate_genre_dna},
    {"name": "generate_melody_variation", "description": "Generate a variation of a melody: ornamentation, rhythmic displacement, or interval expansion.",
     "params": {"melody": "array[array[int]]", "variation_type": "string", "intensity": "float"}, "run": generate_melody_variation},
    {"name": "generate_harmonic_rhythm", "description": "Plan the harmonic rhythm: how many bars each chord lasts based on genre energy.",
     "params": {"chords": "array[object]", "bpm": "int"}, "run": generate_harmonic_rhythm},
    {"name": "generate_intelligent_orchestration", "description": "Suggest orchestration: which instruments play what, based on melody and genre.",
     "params": {"melody": "array[array[int]]", "genre": "string", "energy": "float"}, "run": generate_intelligent_orchestration},
]
