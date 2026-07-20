"""Music tools — exposes the EAZZU audio suite to the agent registry.

Wraps the pure-Python audio engine, sequencer, mixer, MIDI, AI composer
(Vinny), stem splitter, mastering, effects, visualizer and export engines
so the agent can drive the full music production pipeline as tools.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def _error(code: str, exc: Exception) -> Dict[str, Any]:
    return {"error": code, "message": str(exc)}


# ─── Synthesis & engine ──────────────────────────────────────────────────

def audio_engine_state() -> Dict[str, Any]:
    try:
        from eazzu.audio import AudioEngine
        return AudioEngine().get_state()
    except Exception as exc:
        return _error("engine_unavailable", exc)


def render_note(note: str, duration: float = 1.0, waveform: str = "sawtooth",
                attack: float = 0.02, decay: float = 0.2, sustain: float = 0.6,
                release: float = 0.4) -> Dict[str, Any]:
    try:
        from eazzu.audio import AudioEngine, SynthVoiceParams
        eng = AudioEngine()
        params = SynthVoiceParams(waveform, attack, decay, sustain, release)
        samples = eng.render_note(
            eng.note_on("v1", 440.0)["freq"] if False else 440.0, duration, params
        )
        return {"note": note, "duration": duration, "samples": len(samples),
                "waveform": waveform, "params": params.to_dict()}
    except Exception as exc:
        return _error("render_failed", exc)


# ─── AI composition (Vinny extended) ─────────────────────────────────────

def ai_melody(key: str = "C", scale_type: str = "major", bars: int = 4,
              mood: str = "happy", complexity: float = 0.5) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_ai_melody
        return {"melody": generate_ai_melody(key, scale_type, bars, mood, complexity),
                "key": key, "scale": scale_type, "bars": bars, "mood": mood}
    except Exception as exc:
        return _error("melody_failed", exc)


def ai_chord_progression(key: str = "C", style: str = "pop", bars: int = 4) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_chord_progression
        return generate_chord_progression(key, style, bars)
    except Exception as exc:
        return _error("chords_failed", exc)


def ai_drum_pattern(genre: str = "house", steps: int = 16) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_drum_pattern
        return {"pattern": generate_drum_pattern(genre, steps), "genre": genre, "steps": steps}
    except Exception as exc:
        return _error("drums_failed", exc)


def ai_arpeggio(notes: List[int], pattern: str = "up", octaves: int = 2,
                steps: int = 16) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_arpeggio
        return {"arpeggio": generate_arpeggio(notes, pattern, octaves, steps)}
    except Exception as exc:
        return _error("arp_failed", exc)


def ai_bass_line(key: str = "C", scale_type: str = "major", genre: str = "house",
                 bars: int = 4) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_bass_line
        return {"bass": generate_bass_line(key, scale_type, genre, bars)}
    except Exception as exc:
        return _error("bass_failed", exc)


def ai_song_structure(genre: str = "pop") -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_song_structure
        return {"structure": generate_song_structure(genre), "genre": genre}
    except Exception as exc:
        return _error("structure_failed", exc)


def find_scales(notes: List[int]) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import find_scales as _find
        return {"matching_scales": _find(notes)}
    except Exception as exc:
        return _error("scales_failed", exc)


def euclidean_rhythm(steps: int = 16, pulses: int = 4, rotation: int = 0) -> Dict[str, Any]:
    try:
        from eazzu.audio.vinny_extended import generate_euclidean_rhythm
        return {"rhythm": generate_euclidean_rhythm(steps, pulses, rotation)}
    except Exception as exc:
        return _error("euclidean_failed", exc)


# ─── Mixing & mastering ─────────────────────────────────────────────────

def mixing_console_state() -> Dict[str, Any]:
    try:
        from eazzu.audio import MixingConsole
        return MixingConsole().get_state()
    except Exception as exc:
        return _error("mixer_failed", exc)


def auto_master(target_lufs: float = -14.0, preset: str = "streaming") -> Dict[str, Any]:
    try:
        from eazzu.audio import auto_master as _am, MASTER_PRESETS
        return {"available_presets": list(MASTER_PRESETS.keys()) if isinstance(MASTER_PRESETS, dict) else MASTER_PRESETS,
                "target_lufs": target_lufs, "preset": preset}
    except Exception as exc:
        return _error("master_failed", exc)


# ─── MIDI ────────────────────────────────────────────────────────────────

def generate_midi_file(notes: List[int], tempo: int = 120, path: Optional[str] = None) -> Dict[str, Any]:
    try:
        from eazzu.audio import generate_midi
        data = generate_midi(notes, tempo)
        return {"tempo": tempo, "note_count": len(notes), "data_bytes": len(data) if data else 0,
                "path": path}
    except Exception as exc:
        return _error("midi_failed", exc)


# ─── Analysis ────────────────────────────────────────────────────────────

def analyze_audio(samples: List[float], sample_rate: int = 44100) -> Dict[str, Any]:
    try:
        from eazzu.audio import AudioTools, AudioEngine
        tools = AudioTools(AudioEngine())
        return {
            "bpm": tools.detect_bpm(samples, sample_rate),
            "key": tools.detect_key(samples, sample_rate),
            "loudness": tools.measure_lufs(samples, sample_rate),
            "spectrum": tools.analyze_spectrum(samples, sample_rate),
            "transients": tools.detect_transients(samples, sample_rate),
        }
    except Exception as exc:
        return _error("analysis_failed", exc)


# ─── Stem separation ────────────────────────────────────────────────────

def split_stems(samples: List[float], sample_rate: int = 44100) -> Dict[str, Any]:
    try:
        from eazzu.audio import AudioTools, AudioEngine
        return AudioTools(AudioEngine()).split_stems(samples, sample_rate)
    except Exception as exc:
        return _error("stems_failed", exc)


TOOLS = [
    {"name": "audio_engine_state", "description": "Return the current audio engine state (voices, effects, master volume).",
     "params": {}, "run": audio_engine_state},
    {"name": "render_note", "description": "Render a single musical note to samples with ADSR envelope and waveform.",
     "params": {"note": "string", "duration": "float", "waveform": "string", "attack": "float",
                "decay": "float", "sustain": "float", "release": "float"}, "run": render_note},
    {"name": "ai_melody", "description": "Generate an AI melody in a given key, scale, mood and complexity.",
     "params": {"key": "string", "scale_type": "string", "bars": "int", "mood": "string", "complexity": "float"},
     "run": ai_melody},
    {"name": "ai_chord_progression", "description": "Generate a chord progression (pop/jazz/blues) for a key.",
     "params": {"key": "string", "style": "string", "bars": "int"}, "run": ai_chord_progression},
    {"name": "ai_drum_pattern", "description": "Generate a drum pattern for a genre (house/trap/lofi/techno/dnb).",
     "params": {"genre": "string", "steps": "int"}, "run": ai_drum_pattern},
    {"name": "ai_arpeggio", "description": "Generate an arpeggio from a set of notes (up/down/random patterns).",
     "params": {"notes": "array[int]", "pattern": "string", "octaves": "int", "steps": "int"}, "run": ai_arpeggio},
    {"name": "ai_bass_line", "description": "Generate a bass line for a key, scale and genre.",
     "params": {"key": "string", "scale_type": "string", "genre": "string", "bars": "int"}, "run": ai_bass_line},
    {"name": "ai_song_structure", "description": "Generate a song structure (sections, bars, energy) for a genre.",
     "params": {"genre": "string"}, "run": ai_song_structure},
    {"name": "find_scales", "description": "Find musical scales that contain a given set of notes.",
     "params": {"notes": "array[int]"}, "run": find_scales},
    {"name": "euclidean_rhythm", "description": "Generate a Euclidean rhythm (steps/pulses/rotation).",
     "params": {"steps": "int", "pulses": "int", "rotation": "int"}, "run": euclidean_rhythm},
    {"name": "mixing_console_state", "description": "Return the default mixing console state (channels, EQ, dynamics).",
     "params": {}, "run": mixing_console_state},
    {"name": "auto_master", "description": "List mastering presets and target LUFS for automatic mastering.",
     "params": {"target_lufs": "float", "preset": "string"}, "run": auto_master},
    {"name": "generate_midi_file", "description": "Generate a MIDI byte sequence from a list of notes.",
     "params": {"notes": "array[int]", "tempo": "int", "path": "string(optional)"}, "run": generate_midi_file},
    {"name": "analyze_audio", "description": "Analyze audio samples: BPM, key, loudness (LUFS), spectrum, transients.",
     "params": {"samples": "array[float]", "sample_rate": "int"}, "run": analyze_audio},
    {"name": "split_stems", "description": "Split audio samples into vocals, bass, drums and other stems.",
     "params": {"samples": "array[float]", "sample_rate": "int"}, "run": split_stems},
]
