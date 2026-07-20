"""MIDI Input — hardware keyboard input handler."""
from __future__ import annotations
from typing import Callable, List, Optional

NOTE_NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"]

def midi_to_note_name(note): return f"{NOTE_NAMES[note%12]}{note//12-1}"
def midi_to_freq(note): return 440.0*(2.0**((note-69)/12))

class MIDIInput:
    def __init__(self): self.connected=False; self.inputs=[]; self.on_note_on=None; self.on_note_off=None; self.on_cc=None; self.on_pitch_bend=None; self.on_aftertouch=None
    def init(self, on_note_on=None, on_note_off=None, on_cc=None, on_pitch_bend=None, on_aftertouch=None):
        self.on_note_on=on_note_on; self.on_note_off=on_note_off; self.on_cc=on_cc; self.on_pitch_bend=on_pitch_bend; self.on_aftertouch=on_aftertouch; self.connected=True; return True
    def handle_message(self, status, data1, data2):
        cmd=status&0xf0; ch=status&0x0f
        if cmd==0x90 and data2>0:
            if self.on_note_on: self.on_note_on(data1,data2,ch)
        elif cmd==0x80 or (cmd==0x90 and data2==0):
            if self.on_note_off: self.on_note_off(data1,data2,ch)
        elif cmd==0xb0:
            if self.on_cc: self.on_cc(data1,data2,ch)
        elif cmd==0xe0:
            if self.on_pitch_bend: self.on_pitch_bend((data2<<7)+data1-8192,ch)
        elif cmd==0xa0:
            if self.on_aftertouch: self.on_aftertouch(data1,data2,ch)
    def get_input_names(self): return list(self.inputs)
    def is_supported(self): return True
    def disconnect(self): self.connected=False; self.inputs=[]
