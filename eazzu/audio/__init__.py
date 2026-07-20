"""EAZZU Audio Suite — converted from infinite-loop-sound's src/lib/audio/.

24 modules covering synthesis, sequencing, mixing, MIDI, sampling, effects,
mastering, visualization, stem separation, voice synthesis, pitch/formant
processing, and the Vinny AI music assistant. All pure-Python, stdlib-only.
"""
from eazzu.audio.engine import (
    AudioEngine, note_to_freq, midi_to_freq, NOTE_NAMES, SCALES, WAVEFORMS,
)
from eazzu.audio.audio_tools import AudioTools
from eazzu.audio.sequencer import Sequencer, create_default_sequencer
from eazzu.audio.advanced_mixer import MixingConsole
from eazzu.audio.channel_rack import ChannelRack, create_default_channel_rack
from eazzu.audio.midi_tools import parse_midi, export_midi, transform_midi, midi_to_note_name, generate_midi
from eazzu.audio.midi_input import MIDIInput, midi_to_note_name as midi_input_note_name, midi_to_freq as midi_input_freq
from eazzu.audio.piano_roll import PianoRoll, PianoNote, NoteSlide
from eazzu.audio.modulation import ModulationEngine, DEFAULT_MODULATION
from eazzu.audio.auto_master import auto_master, auto_mix, MASTER_PRESETS, MasterPreset
from eazzu.audio.extended_fx import ExtendedFX, EXTENDED_FX_TYPES
from eazzu.audio.extended_fx2 import ExtendedFX2, EXTENDED_FX2_TYPES
from eazzu.audio.visualizer import Visualizer, VizConfig
from eazzu.audio.advanced_visualizer import AdvancedVisualizer, ADVANCED_VIZ_MODES
from eazzu.audio.export_engine import ExportEngine, ExportFormat, ExportOptions
from eazzu.audio.oneshot_sampler import OneShotSampler, OneShotPad
from eazzu.audio.sample_packs import SamplePackManager, Sample, SAMPLE_CATEGORIES
from eazzu.audio.stem_splitter import StemSplitter, StemType
from eazzu.audio.playlist import Playlist, PlaylistClip, PlaylistTrack
from eazzu.audio.recorder import AudioRecorder
from eazzu.audio.voice_synth import VoiceSynth, parse_lyrics, apply_variation
from eazzu.audio.pitch_formant import SoundPitcher, PitcherConfig
from eazzu.audio.vinny import Vinny
from eazzu.audio.vinny_extended import (
    generate_ai_melody, generate_chord_progression, generate_drum_pattern,
    generate_arpeggio, generate_bass_line, find_scales, harmonize,
    generate_euclidean_rhythm, optimize_voice_leading, generate_song_structure,
)
from eazzu.audio.advanced_music import (
    granular_synthesize, spectral_dft, spectral_freeze, harmonic_analysis,
    detect_pitch_autocorrelation, generate_counterpoint, generate_fugue,
    markov_melody, generate_scales_full, chord_voicing, write_wav,
    apply_distortion, apply_chorus, apply_compressor,
    generate_polyrhythm, swing_quantize,
)

__all__ = [
    "AudioEngine", "note_to_freq", "midi_to_freq", "NOTE_NAMES", "SCALES", "WAVEFORMS",
    "AudioTools", "Sequencer", "create_default_sequencer", "MixingConsole",
    "ChannelRack", "create_default_channel_rack",
    "parse_midi", "export_midi", "transform_midi", "midi_to_note_name", "generate_midi",
    "MIDIInput", "PianoRoll", "PianoNote", "NoteSlide",
    "ModulationEngine", "DEFAULT_MODULATION",
    "auto_master", "auto_mix", "MASTER_PRESETS", "MasterPreset",
    "ExtendedFX", "EXTENDED_FX_TYPES", "ExtendedFX2", "EXTENDED_FX2_TYPES",
    "Visualizer", "VizConfig", "AdvancedVisualizer", "ADVANCED_VIZ_MODES",
    "ExportEngine", "ExportFormat", "ExportOptions",
    "OneShotSampler", "OneShotPad", "SamplePackManager", "Sample", "SAMPLE_CATEGORIES",
    "StemSplitter", "StemType", "Playlist", "PlaylistClip", "PlaylistTrack",
    "AudioRecorder", "VoiceSynth", "parse_lyrics", "apply_variation",
    "SoundPitcher", "PitcherConfig", "Vinny",
    "generate_ai_melody", "generate_chord_progression", "generate_drum_pattern",
    "generate_arpeggio", "generate_bass_line", "find_scales", "harmonize",
    "generate_euclidean_rhythm", "optimize_voice_leading", "generate_song_structure",
    "granular_synthesize", "spectral_dft", "spectral_freeze", "harmonic_analysis",
    "detect_pitch_autocorrelation", "generate_counterpoint", "generate_fugue",
    "markov_melody", "generate_scales_full", "chord_voicing", "write_wav",
    "apply_distortion", "apply_chorus", "apply_compressor",
    "generate_polyrhythm", "swing_quantize",
]
