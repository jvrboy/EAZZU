"""Playlist / Song Arrangement Engine."""
from __future__ import annotations
import uuid
from typing import Any, Dict, List, Optional

class PlaylistClip:
    def __init__(self, track_id, name="", start_bar=0.0, length_bars=4.0, clip_type="pattern", color="#3b82f6"):
        self.id=str(uuid.uuid4()); self.track_id=track_id; self.name=name; self.start_bar=start_bar; self.length_bars=length_bars; self.type=clip_type; self.color=color
        self.volume=1.0; self.pan=0.0; self.muted=False; self.solo=False; self.pattern_id=None; self.audio_buffer=None
    def to_dict(self): return {"id":self.id,"trackId":self.track_id,"name":self.name,"startBar":self.start_bar,"lengthBars":self.length_bars,"type":self.type,"volume":self.volume,"muted":self.muted}

class PlaylistTrack:
    def __init__(self, name, ttype="pattern"): self.id=str(uuid.uuid4()); self.name=name; self.type=ttype; self.color="#3b82f6"; self.muted=False; self.solo=False; self.volume=1.0; self.pan=0.0
    def to_dict(self): return {k:v for k,v in vars(self).items()}

class Playlist:
    def __init__(self, bpm=120.0, bars=32): self.bpm=bpm; self.bars=bars; self.tracks=[PlaylistTrack("Track 1"),PlaylistTrack("Track 2"),PlaylistTrack("Track 3","audio")]; self.clips=[]; self.playing=False; self.current_bar=0.0
    def add_track(self, name, ttype="pattern"): t=PlaylistTrack(name,ttype); self.tracks.append(t); return t
    def add_clip(self, clip): self.clips.append(clip); return clip
    def get_clips_at_bar(self, bar): return [c for c in self.clips if c.start_bar<=bar<c.start_bar+c.length_bars and not c.muted]
    def get_state(self): return {"bpm":self.bpm,"bars":self.bars,"tracks":[t.to_dict() for t in self.tracks],"clips":[c.to_dict() for c in self.clips],"playing":self.playing}
