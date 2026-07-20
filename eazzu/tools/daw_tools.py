"""DAW / music production tools.

Pure-Python helpers that model common DAW workflows: timeline editing,
stem separation, chord/key detection, MIDI humanization, mastering, and more.
Each tool returns a structured dict describing the planned/analyzed result.
"""

from __future__ import annotations

import math
import random

_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]


def _bpm_to_sec(bpm: float) -> float:
    return 60.0 / max(bpm, 1.0)

def _stems_for_genre(genre: str) -> list[str]:
    base = ["drums", "bass", "vocals", "other"]
    extra = {"electronic": ["synths", "fx"], "rock": ["guitars", "keys"], "orchestral": ["strings", "brass", "woodwinds"]}
    return base + extra.get(genre.lower(), [])

def _scale_notes(root: str, scale: str) -> list[str]:
    intervals = {"major": [0, 2, 4, 5, 7, 9, 11], "minor": [0, 2, 3, 5, 7, 8, 10],
                 "dorian": [0, 2, 3, 5, 7, 9, 10], "mixolydian": [0, 2, 4, 5, 7, 9, 10],
                 "pentatonic": [0, 3, 5, 7, 10]}.get(scale, [0, 2, 4, 5, 7, 9, 11])
    ri = _NOTES.index(root)
    return [_NOTES[(ri + i) % 12] for i in intervals]

def _freq_to_note(freq: float) -> str:
    midi = round(12 * math.log2(freq / 440.0) + 69)
    return f"{_NOTES[midi % 12]}{midi // 12 - 1}"

def _humanize_vel(vel: int, amount: float) -> int:
    return max(1, min(127, int(vel + random.uniform(-amount, amount) * 20)))

def _amb_channels(order: int) -> int:
    return {1: 4, 2: 9, 3: 16}.get(order, 16)

TOOLS: list[dict] = [
    {"name": "daw_timeline", "description": "Plan a DAW timeline arrangement from section list and BPM.",
     "params": {"sections": "list[dict]", "bpm": "float"},
     "run": lambda a: {
         "timeline": [{"name": s.get("name", f"Section {i+1}"), "bars": s.get("bars", 8),
                       "start_bar": sum(x.get("bars", 8) for x in a.get("sections", [])[:i]),
                       "seconds": s.get("bars", 8) * 4 * _bpm_to_sec(a.get("bpm", 120))}
                      for i, s in enumerate(a.get("sections", []))],
         "total_bars": sum(s.get("bars", 8) for s in a.get("sections", [])),
         "total_seconds": sum(s.get("bars", 8) for s in a.get("sections", [])) * 4 * _bpm_to_sec(a.get("bpm", 120))}},

    {"name": "daw_stem_separation", "description": "Plan stem separation for a track into component stems.",
     "params": {"track": "str", "genre": "str", "stems": "int"},
     "run": lambda a: {"stems": _stems_for_genre(a.get("genre", "pop"))[:a.get("stems", 4)],
                      "method": "spleeter/demucs", "quality": "high" if a.get("stems", 4) <= 4 else "medium"}},

    {"name": "daw_chord_suggest", "description": "Suggest chord progressions for a key and scale.",
     "params": {"key": "str", "scale": "str", "bars": "int"},
     "run": lambda a: {"progression": [{"degree": d, "chord": n, "bars": 1} for d, n in
                       zip(["I", "V", "vi", "IV"], _scale_notes(a.get("key", "C"), a.get("scale", "major"))[:4])],
                       "key": a.get("key", "C"), "scale": a.get("scale", "major")}},

    {"name": "daw_key_tempo_detect", "description": "Estimate musical key and tempo from spectral metadata.",
     "params": {"chroma": "list[float]", "energy": "list[float]"},
     "run": lambda a: {"key": _NOTES[max(enumerate(a.get("chroma", [1]*12)), key=lambda x: x[1])[0]],
                      "tempo_bpm": round(60.0 / (sum(a.get("energy", [0.5])) / max(len(a.get("energy", [0.5])), 1))),
                      "confidence": 0.87}},

    {"name": "daw_live_loop", "description": "Configure a live looping session with track count and loop length.",
     "params": {"tracks": "int", "bars": "int", "bpm": "float", "quantize": "str"},
     "run": lambda a: {"tracks": a.get("tracks", 4), "loop_bars": a.get("bars", 4),
                       "loop_seconds": a.get("bars", 4) * 4 * _bpm_to_sec(a.get("bpm", 120)),
                       "quantize": a.get("quantize", "1/16"), "overdub": True}},

    {"name": "daw_midi_humanize", "description": "Humanize MIDI note timing and velocity for expressive playback.",
     "params": {"notes": "list[dict]", "amount": "float"},
     "run": lambda a: {"notes": [{**n, "tick": n.get("tick", 0) + random.randint(-30, 30),
                       "velocity": _humanize_vel(n.get("velocity", 100), a.get("amount", 0.5))}
                      for n in a.get("notes", [])]}},

    {"name": "daw_modular_synth", "description": "Generate a modular synth patch description from module list.",
     "params": {"modules": "list[str]", "target": "str"},
     "run": lambda a: {"patch": [{"from": m, "to": a.get("modules", [m])[i+1] if i+1 < len(a.get("modules", [m])) else "output",
                       "signal": "cv" if "env" in m else "audio"} for i, m in enumerate(a.get("modules", []))],
                      "target_sound": a.get("target", "pad")}},

    {"name": "daw_sidechain", "description": "Configure sidechain compression between source and target.",
     "params": {"source": "str", "target": "str", "threshold_db": "float", "ratio": "float"},
     "run": lambda a: {"source": a.get("source", "kick"), "target": a.get("target", "bass"),
                       "threshold_db": a.get("threshold_db", -30.0), "ratio": a.get("ratio", 4.0),
                       "attack_ms": 5, "release_ms": 80}},

    {"name": "daw_pitch_correct", "description": "Plan pitch correction (auto-tune) settings for a vocal track.",
     "params": {"key": "str", "scale": "str", "strength": "float", "formant": "bool"},
     "run": lambda a: {"key": a.get("key", "C"), "scale": a.get("scale", "major"),
                       "scale_notes": _scale_notes(a.get("key", "C"), a.get("scale", "major")),
                       "strength": a.get("strength", 0.8), "formant_preserve": a.get("formant", True)}},

    {"name": "daw_time_stretch", "description": "Calculate time-stretch ratio and algorithm for audio length change.",
     "params": {"original_bpm": "float", "target_bpm": "float", "algorithm": "str"},
     "run": lambda a: {"ratio": a.get("target_bpm", 120) / max(a.get("original_bpm", 120), 1),
                       "algorithm": a.get("algorithm", "elastique"), "preserve_pitch": True}},

    {"name": "daw_mixing_assistant", "description": "Suggest mixing settings (EQ, levels, panning) for a set of tracks.",
     "params": {"tracks": "list[str]", "genre": "str"},
     "run": lambda a: {"mix": [{"track": t, "gain_db": -6.0 - i * 1.5, "pan": (i % 3 - 1) * 30,
                       "eq": {"low": 0, "mid": 0, "high": 0}} for i, t in enumerate(a.get("tracks", []))]}},

    {"name": "daw_mastering", "description": "Generate a mastering chain suggestion from target LUFS and genre.",
     "params": {"target_lufs": "float", "genre": "str", "peak_db": "float"},
     "run": lambda a: {"target_lufs": a.get("target_lufs", -14.0), "chain": ["eq", "multiband_comp", "limiter"],
                       "ceiling_db": a.get("peak_db", -1.0), "true_peak": True}},

    {"name": "daw_reference_match", "description": "Match a mix to a reference track's tonal balance and loudness.",
     "params": {"reference": "str", "target_lufs": "float"},
     "run": lambda a: {"reference": a.get("reference", "ref.wav"),
                       "eq_adjustments": {"60hz": 1.5, "200hz": 0.0, "2khz": -1.0, "10khz": 2.0},
                       "target_lufs": a.get("target_lufs", -14.0)}},

    {"name": "daw_sample_search", "description": "Search a local sample library by BPM, key, and genre tags.",
     "params": {"bpm": "float", "key": "str", "genre": "str", "limit": "int"},
     "run": lambda a: {"results": [{"name": f"sample_{i}.wav", "bpm": a.get("bpm", 120),
                       "key": a.get("key", "C"), "match": round(0.9 - i * 0.05, 2)} for i in range(a.get("limit", 5))]}},

    {"name": "daw_drum_groove", "description": "Generate a drum groove pattern for a given genre and swing.",
     "params": {"genre": "str", "bars": "int", "swing": "float"},
     "run": lambda a: {"pattern": {"kick": [1,0,0,0,1,0,0,0] * a.get("bars", 1),
                       "snare": [0,0,0,0,1,0,0,0] * a.get("bars", 1), "hat": [1,0,1,0,1,0,1,0] * a.get("bars", 1)},
                       "swing": a.get("swing", 0.0), "genre": a.get("genre", "house")}},

    {"name": "daw_freeze_track", "description": "Plan track freezing to save CPU by rendering instrument tracks to audio.",
     "params": {"tracks": "list[str]", "plugin_cpu": "dict"},
     "run": lambda a: {"freeze": [t for t in a.get("tracks", []) if a.get("plugin_cpu", {}).get(t, 0) > 15],
                       "estimated_cpu_saved_pct": sum(a.get("plugin_cpu", {}).get(t, 0) for t in a.get("tracks", [])) // 2}},

    {"name": "daw_comping", "description": "Select best takes from multiple recordings to form a composite track.",
     "params": {"takes": "list[dict]", "criteria": "str"},
     "run": lambda a: {"selected": [{"take": t.get("id", i), "start": t.get("start", 0), "end": t.get("end", 0)}
                       for i, t in enumerate(sorted(a.get("takes", []), key=lambda x: x.get("score", 0), reverse=True)[:3])]}},

    {"name": "daw_video_scoring", "description": "Plan a scoring session: map musical cues to video timecodes.",
     "params": {"cues": "list[dict]", "bpm": "float"},
     "run": lambda a: {"cues": [{"timecode": c.get("tc", "00:00:00"), "bar": i + 1, "action": c.get("action", "hit")}
                       for i, c in enumerate(a.get("cues", []))], "bpm": a.get("bpm", 120)}},

    {"name": "daw_spatial_audio", "description": "Configure spatial/3D audio rendering settings (Ambisonic or binaural).",
     "params": {"format": "str", "order": "int", "head_tracking": "bool"},
     "run": lambda a: {"format": a.get("format", "ambisonic"), "order": a.get("order", 3),
                       "channels": _amb_channels(a.get("order", 3)), "head_tracking": a.get("head_tracking", False)}},

    {"name": "daw_collaboration", "description": "Set up a real-time collaboration session with track sharing.",
     "params": {"users": "list[str]", "project": "str", "bitrate": "int"},
     "run": lambda a: {"session_id": f"sess-{abs(hash(a.get('project', 'default'))):x}",
                       "users": a.get("users", []), "audio_bitrate_kbps": a.get("bitrate", 256), "sync_mode": "realtime"}},

    {"name": "daw_controller_map", "description": "Map MIDI controller CCs to DAW parameters.",
     "params": {"controller": "str", "mappings": "dict"},
     "run": lambda a: {"controller": a.get("controller", "MIDI Keyboard"),
                       "mappings": a.get("mappings", {"cc1": "volume", "cc2": "pan", "cc3": "filter"})}},

    {"name": "daw_latency_report", "description": "Report round-trip latency from buffer size and sample rate.",
     "params": {"buffer_size": "int", "sample_rate": "int", "plugins": "list[dict]"},
     "run": lambda a: {"buffer_ms": (a.get("buffer_size", 256) / a.get("sample_rate", 44100)) * 1000 * 2,
                       "plugin_latency_ms": sum(p.get("latency_ms", 0) for p in a.get("plugins", [])),
                       "total_ms": (a.get("buffer_size", 256) / a.get("sample_rate", 44100)) * 1000 * 2
                       + sum(p.get("latency_ms", 0) for p in a.get("plugins", []))}},

    {"name": "daw_sample_convert", "description": "Convert sample format and rate settings.",
     "params": {"src_format": "str", "dst_format": "str", "src_rate": "int", "dst_rate": "int"},
     "run": lambda a: {"src": {"format": a.get("src_format", "wav"), "rate": a.get("src_rate", 44100)},
                       "dst": {"format": a.get("dst_format", "flac"), "rate": a.get("dst_rate", 48000)},
                       "quality": "resample_hq"}},

    {"name": "daw_loop_detect", "description": "Detect loop points in an audio file from onset data.",
     "params": {"onsets": "list[float]", "bpm": "float", "tolerance": "float"},
     "run": lambda a: {"loop_start_sec": (a.get("onsets", [0]) or [0])[0],
                       "loop_end_sec": (a.get("onsets", [0]) or [0])[-1] if a.get("onsets") else 0,
                       "loop_bars": round(((a.get("onsets", [0, 2]) or [0, 2])[-1] - (a.get("onsets", [0, 2]) or [0, 2])[0]) * a.get("bpm", 120) / 240),
                       "seamless": True}},

    {"name": "daw_session_template", "description": "Create a session template from genre and track count.",
     "params": {"genre": "str", "tracks": "int", "bpm": "float"},
     "run": lambda a: {"template_name": f"{a.get('genre', 'pop')}_template",
                       "tracks": [{"name": f"Track {i+1}", "type": "audio" if i % 2 == 0 else "midi"} for i in range(a.get("tracks", 8))],
                       "bpm": a.get("bpm", 120)}},

    {"name": "daw_voice_to_instrument", "description": "Convert vocal input to MIDI instrument notes.",
     "params": {"pitches": "list[float]", "instrument": "str"},
     "run": lambda a: {"midi_notes": [_freq_to_note(p) for p in a.get("pitches", [440.0])],
                       "instrument": a.get("instrument", "saw_lead"), "conversion": "pitch_to_midi"}},

    {"name": "daw_beat_slice", "description": "Slice a beat loop into individual hits at detected transients.",
     "params": {"transients": "list[float]", "slices": "int"},
     "run": lambda a: {"slices": [{"index": i, "start_sec": (a.get("transients", [0]) or [0])[i]
                       if i < len(a.get("transients", [0]) or [0]) else 0.0} for i in range(a.get("slices", 8))],
                       "warp_mode": "beats"}},

    {"name": "daw_granular", "description": "Configure granular synthesis parameters from a source sample.",
     "params": {"grain_size_ms": "float", "density": "float", "pitch_shift": "float"},
     "run": lambda a: {"grain_size_ms": a.get("grain_size_ms", 50.0), "density": a.get("density", 10.0),
                       "pitch_shift_semitones": a.get("pitch_shift", 0.0), "window": "hann", "max_polyphony": 64}},

    {"name": "daw_spectral_edit", "description": "Plan a spectral edit operation on a frequency range.",
     "params": {"freq_low": "float", "freq_high": "float", "operation": "str", "gain_db": "float"},
     "run": lambda a: {"freq_range": [a.get("freq_low", 0), a.get("freq_high", 20000)],
                       "operation": a.get("operation", "reduce"), "gain_db": a.get("gain_db", -12.0), "fft_size": 4096}},

    {"name": "daw_noise_reduction", "description": "Configure noise reduction from a noise profile.",
     "params": {"noise_profile": "dict", "strength": "float", "smoothing": "int"},
     "run": lambda a: {"strength": a.get("strength", 0.7), "smoothing_frames": a.get("smoothing", 5),
                       "fft_size": 2048, "noise_floor_db": a.get("noise_profile", {}).get("floor_db", -60)}},
]