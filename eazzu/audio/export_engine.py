"""Export Engine — multi-format audio export."""
from __future__ import annotations
import struct
from typing import Any, Dict, List, Optional

FORMAT_LABELS = {"wav-16":"WAV 16-bit PCM","wav-24":"WAV 24-bit PCM","wav-32":"WAV 32-bit float","mp3-128":"MP3 128 kbps","mp3-192":"MP3 192 kbps","mp3-256":"MP3 256 kbps","mp3-320":"MP3 320 kbps","flac":"FLAC lossless","ogg":"OGG Vorbis","aiff":"AIFF","pcm-raw":"Raw PCM","m4a":"M4A/AAC"}
EXTENSIONS = {"wav-16":"wav","wav-24":"wav","wav-32":"wav","mp3-128":"mp3","mp3-192":"mp3","mp3-256":"mp3","mp3-320":"mp3","flac":"flac","ogg":"ogg","aiff":"aiff","pcm-raw":"pcm","m4a":"m4a"}
MIME_TYPES = {"wav-16":"audio/wav","wav-24":"audio/wav","wav-32":"audio/wav","mp3-128":"audio/mpeg","mp3-192":"audio/mpeg","mp3-256":"audio/mpeg","mp3-320":"audio/mpeg","flac":"audio/flac","ogg":"audio/ogg","aiff":"audio/aiff","pcm-raw":"application/octet-stream","m4a":"audio/mp4"}

class ExportOptions:
    def __init__(self, format="wav-16", sample_rate=44100, channels=2, normalize=False, normalize_target=-1.0, fade_in=0.0, fade_out=0.0, dither=False, bit_depth=16): self.format=format; self.sample_rate=sample_rate; self.channels=channels; self.normalize=normalize; self.normalize_target=normalize_target; self.fade_in=fade_in; self.fade_out=fade_out; self.dither=dither; self.bit_depth=bit_depth
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class ExportEngine:
    def _encode_wav(self, samples, opts):
        nc=opts.channels; bd=opts.bit_depth; bps=bd//8; ba=nc*bps; ds=len(samples)*bps
        hdr=bytearray(b"RIFF")+struct.pack("<I",36+ds)+b"WAVE"+b"fmt "+struct.pack("<I",16)+struct.pack("<H",1)+struct.pack("<H",nc)+struct.pack("<I",opts.sample_rate)+struct.pack("<I",opts.sample_rate*ba)+struct.pack("<H",ba)+struct.pack("<H",bd)+b"data"+struct.pack("<I",ds)
        data=bytearray()
        for s in samples:
            s=max(-1.0,min(1.0,s)); data+=struct.pack("<h",int(s*32767)) if bd==16 else struct.pack("<f",s)
        return bytes(hdr)+bytes(data)
    def export(self, samples, opts=None):
        if opts is None: opts=ExportOptions()
        wav=self._encode_wav(samples,opts)
        return {"data":wav,"format":opts.format,"size":len(wav),"duration":len(samples)/opts.sample_rate,"sampleRate":opts.sample_rate,"channels":opts.channels,"extension":EXTENSIONS.get(opts.format,"wav"),"mimeType":MIME_TYPES.get(opts.format,"audio/wav")}
