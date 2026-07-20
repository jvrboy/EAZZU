"""Audio Recording & Export — captures audio and exports as WAV."""
from __future__ import annotations
import struct, time
from typing import Any, Dict, List

class AudioRecorder:
    def __init__(self): self.recording=False; self._chunks=[]; self._start_time=0.0
    def start(self): self._chunks=[]; self.recording=True; self._start_time=time.time()
    def stop(self): self.recording=False; out=[]; [out.extend(c) for c in self._chunks]; return out
    def feed(self, samples): 
        if self.recording: self._chunks.append(list(samples))
    @staticmethod
    def audio_buffer_to_wav(samples, sample_rate=44100, channels=1):
        ds=len(samples)*2; hdr=bytearray(b"RIFF")+struct.pack("<I",36+ds)+b"WAVE"+b"fmt "+struct.pack("<I",16)+struct.pack("<H",1)+struct.pack("<H",channels)+struct.pack("<I",sample_rate)+struct.pack("<I",sample_rate*2)+struct.pack("<H",2)+struct.pack("<H",16)+b"data"+struct.pack("<I",ds)
        data=bytearray()
        for s in samples: data+=struct.pack("<h",int(max(-1,min(1,s))*32767))
        return bytes(hdr)+bytes(data)
    def get_state(self): return {"recording":self.recording,"elapsed":time.time()-self._start_time if self.recording else 0}
