"""
Media Converter Tool
Convert between various media formats.

Features:
- Video format conversion (mp4, avi, mkv, mov, webm, etc.)
- Audio format conversion (mp3, wav, flac, aac, ogg, etc.)
- Image format conversion (jpg, png, gif, webp, bmp, etc.)
- Quality/bitrate control
- Batch conversion
- Preset configurations
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


@dataclass
class ConversionPreset:
    """Preset configuration for conversions."""
    name: str
    video_codec: str = ""
    audio_codec: str = ""
    video_bitrate: str = ""
    audio_bitrate: str = ""
    resolution: str = ""
    fps: int = 0
    audio_sample_rate: int = 44100
    extra_args: List[str] = None
    
    def __post_init__(self):
        if self.extra_args is None:
            self.extra_args = []


class Converter(ToolBase):
    """Universal media converter using ffmpeg."""
    
    metadata = ToolMetadata(
        name="converter",
        version="2.0.0",
        description="Convert media files between formats. Video, audio, and image conversion.",
        category="media",
        tags=["convert", "ffmpeg", "video", "audio", "image", "transcode"],
        provides=["media_conversion", "transcoding"],
        requires=["ffmpeg"],
        permissions=["filesystem"]
    )
    
    # Presets
    PRESETS = {
        "mp4_h264": ConversionPreset(
            name="MP4 H.264",
            video_codec="libx264",
            audio_codec="aac",
            video_bitrate="4M",
            audio_bitrate="192k",
            extra_args=["-movflags", "+faststart", "-pix_fmt", "yuv420p"]
        ),
        "mp4_h265": ConversionPreset(
            name="MP4 H.265/HEVC",
            video_codec="libx265",
            audio_codec="aac",
            video_bitrate="2M",
            audio_bitrate="192k",
            extra_args=["-tag:v", "hvc1", "-pix_fmt", "yuv420p"]
        ),
        "web": ConversionPreset(
            name="Web Optimized",
            video_codec="libx264",
            audio_codec="aac",
            video_bitrate="2M",
            audio_bitrate="128k",
            resolution="1280x720",
            extra_args=["-movflags", "+faststart"]
        ),
        "mobile": ConversionPreset(
            name="Mobile",
            video_codec="libx264",
            audio_codec="aac",
            video_bitrate="1M",
            audio_bitrate="96k",
            resolution="854x480",
            fps=30
        ),
        "audio_high": ConversionPreset(
            name="High Quality Audio",
            audio_codec="flac",
            audio_sample_rate=48000,
        ),
        "audio_mp3": ConversionPreset(
            name="MP3",
            audio_codec="libmp3lame",
            audio_bitrate="320k",
            audio_sample_rate=44100,
        ),
        "audio_aac": ConversionPreset(
            name="AAC",
            audio_codec="aac",
            audio_bitrate="256k",
        ),
        "gif": ConversionPreset(
            name="GIF",
            video_codec="gif",
            resolution="480:-1",
            fps=15,
            extra_args=["-vf", "split[s0][s1];[s0]palettegen=max_colors=128[p];[s1][p]paletteuse"]
        ),
    }
    
    # Format groups
    VIDEO_FORMATS = {".mp4", ".avi", ".mkv", ".mov", ".wmv", ".flv", ".webm", ".m4v", ".mpg", ".mpeg"}
    AUDIO_FORMATS = {".mp3", ".wav", ".flac", ".aac", ".ogg", ".opus", ".m4a", ".wma"}
    IMAGE_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff", ".ico"}
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
        self.ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe_path = shutil.which("ffprobe") or "ffprobe"
        
        if shutil.which("ffmpeg"):
            log.info(f"Converter ready: {self.ffmpeg_path}")
        else:
            log.warning("ffmpeg not found. Converter limited.")
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "convert")
        
        actions = {
            "convert": self.convert,
            "convert_video": self.convert_video,
            "convert_audio": self.convert_audio,
            "convert_image": self.convert_image,
            "batch_convert": self.batch_convert,
            "detect_format": self.detect_format,
            "get_info": self.get_media_info,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    def convert(self, input: str, output: str = None, 
                format: str = None, preset: str = None,
                **kwargs) -> str:
        """
        Universal conversion - auto-detects media type.
        
        Args:
            input: Input file path
            output: Output file path (auto-generated if not provided)
            format: Output format extension (e.g., 'mp4', 'mp3', 'png')
            preset: Named preset to use
        """
        if not output and not format:
            raise ValueError("Either output path or format must be specified")
        
        input_path = Path(input)
        
        if not output:
            output = str(input_path.with_suffix(f".{format}"))
        
        # Determine type and route
        ext = input_path.suffix.lower()
        
        if ext in self.VIDEO_FORMATS:
            return self.convert_video(input, output, preset=preset, **kwargs)
        elif ext in self.AUDIO_FORMATS:
            return self.convert_audio(input, output, preset=preset, **kwargs)
        elif ext in self.IMAGE_FORMATS:
            return self.convert_image(input, output, **kwargs)
        else:
            # Try ffmpeg anyway
            return self._run_ffmpeg(input, output, [], **kwargs)
    
    def convert_video(self, input: str, output: str = None,
                      video_codec: str = None, audio_codec: str = None,
                      video_bitrate: str = None, audio_bitrate: str = None,
                      resolution: str = None, fps: int = None,
                      preset: str = None, **kwargs) -> str:
        """Convert video with full control."""
        
        input_path = Path(input)
        if not output:
            output = str(input_path.with_suffix(".mp4"))
        
        # Build ffmpeg command
        cmd = [self.ffmpeg_path, "-y", "-i", input]
        
        # Apply preset if specified
        if preset and preset in self.PRESETS:
            p = self.PRESETS[preset]
            if p.video_codec: cmd.extend(["-c:v", p.video_codec])
            if p.audio_codec: cmd.extend(["-c:a", p.audio_codec])
            if p.video_bitrate: cmd.extend(["-b:v", p.video_bitrate])
            if p.audio_bitrate: cmd.extend(["-b:a", p.audio_bitrate])
            if p.resolution: cmd.extend(["-s", p.resolution])
            if p.fps: cmd.extend(["-r", str(p.fps)])
            cmd.extend(p.extra_args)
        else:
            # Manual parameters
            if video_codec: cmd.extend(["-c:v", video_codec])
            else: cmd.extend(["-c:v", "libx264"])
            
            if audio_codec: cmd.extend(["-c:a", audio_codec])
            else: cmd.extend(["-c:a", "aac"])
            
            if video_bitrate: cmd.extend(["-b:v", video_bitrate])
            if audio_bitrate: cmd.extend(["-b:a", audio_bitrate])
            if resolution: cmd.extend(["-s", resolution])
            if fps: cmd.extend(["-r", str(fps)])
        
        cmd.append(output)
        
        return self._run_ffmpeg(input, output, cmd[3:-1], **kwargs)
    
    def convert_audio(self, input: str, output: str = None,
                      codec: str = None, bitrate: str = None,
                      sample_rate: int = None,
                      preset: str = None, **kwargs) -> str:
        """Convert audio format."""
        
        input_path = Path(input)
        if not output:
            # Default to mp3
            output = str(input_path.with_suffix(".mp3"))
        
        cmd = [self.ffmpeg_path, "-y", "-i", input]
        
        # Apply preset
        if preset and preset in self.PRESETS:
            p = self.PRESETS[preset]
            if p.audio_codec: cmd.extend(["-c:a", p.audio_codec])
            if p.audio_bitrate: cmd.extend(["-b:a", p.audio_bitrate])
            if p.audio_sample_rate: cmd.extend(["-ar", str(p.audio_sample_rate)])
            cmd.extend(p.extra_args)
        else:
            if codec: cmd.extend(["-c:a", codec])
            if bitrate: cmd.extend(["-b:a", bitrate])
            if sample_rate: cmd.extend(["-ar", str(sample_rate)])
        
        # No video for audio output
        out_ext = Path(output).suffix.lower()
        if out_ext in self.AUDIO_FORMATS:
            cmd.extend(["-vn"])
        
        cmd.append(output)
        
        return self._run_ffmpeg(input, output, cmd[3:-1], **kwargs)
    
    def convert_image(self, input: str, output: str = None,
                      quality: int = 90, resize: str = None,
                      **kwargs) -> str:
        """Convert image format."""
        
        input_path = Path(input)
        if not output:
            output = str(input_path.with_suffix(".png"))
        
        cmd = [self.ffmpeg_path, "-y", "-i", input]
        
        if resize:
            cmd.extend(["-vf", f"scale={resize}"])
        
        # Quality for lossy formats
        out_ext = Path(output).suffix.lower()
        if out_ext in ('.jpg', '.jpeg'):
            cmd.extend(["-q:v", str(max(1, min(31, int((100 - quality) / 3))))])
        elif out_ext == '.webp':
            cmd.extend(["-q:v", str(quality)])
        
        cmd.extend(["-frames:v", "1"])
        cmd.append(output)
        
        return self._run_ffmpeg(input, output, cmd[3:-1], **kwargs)
    
    def batch_convert(self, directory: str = ".", 
                      output_format: str = "mp4",
                      pattern: str = "*",
                      preset: str = None,
                      **kwargs) -> List[str]:
        """Convert all matching files in a directory."""
        log.section(f"Batch Convert to {output_format}")
        
        path = Path(directory)
        files = list(path.glob(pattern))
        
        converted = []
        for i, file in enumerate(files, 1):
            if file.is_file():
                try:
                    output = str(file.with_suffix(f".{output_format}"))
                    result = self.convert(
                        str(file), output, 
                        preset=preset, **kwargs
                    )
                    converted.append(result)
                    log.info(f"[{i}/{len(files)}] ✓ {file.name}")
                except Exception as e:
                    log.error(f"Failed to convert {file.name}: {e}")
        
        log.success(f"Converted {len(converted)} files")
        return converted
    
    def detect_format(self, filepath: str, **kwargs) -> Dict:
        """Detect media format and properties."""
        cmd = [
            self.ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            filepath
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(result.stdout)
            
            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            info = {
                "filename": format_info.get("filename"),
                "format_name": format_info.get("format_name"),
                "duration": float(format_info.get("duration", 0)),
                "size": int(format_info.get("size", 0)),
                "bitrate": int(format_info.get("bit_rate", 0)),
                "streams": []
            }
            
            for stream in streams:
                s_info = {
                    "type": stream.get("codec_type"),
                    "codec": stream.get("codec_name"),
                    "codec_long": stream.get("codec_long_name"),
                }
                
                if stream.get("codec_type") == "video":
                    s_info.update({
                        "width": stream.get("width"),
                        "height": stream.get("height"),
                        "fps": eval(stream.get("r_frame_rate", "0/1")),
                        "pix_format": stream.get("pix_fmt"),
                    })
                elif stream.get("codec_type") == "audio":
                    s_info.update({
                        "sample_rate": stream.get("sample_rate"),
                        "channels": stream.get("channels"),
                        "channel_layout": stream.get("channel_layout"),
                    })
                
                info["streams"].append(s_info)
            
            return info
            
        except Exception as e:
            return {"error": str(e)}
    
    def get_media_info(self, filepath: str, **kwargs) -> Dict:
        """Get detailed media information."""
        return self.detect_format(filepath)
    
    def _run_ffmpeg(self, input: str, output: str, 
                    args: List[str], **kwargs) -> str:
        """Execute ffmpeg with arguments."""
        
        cmd = [self.ffmpeg_path, "-y", "-i", input]
        cmd.extend(args)
        cmd.append(output)
        
        log.info(f"Converting: {Path(input).name} → {Path(output).name}")
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            for line in process.stdout:
                line = line.strip()
                if "time=" in line:
                    log.info(line)
            
            process.wait()
            
            if process.returncode == 0:
                out_size = os.path.getsize(output)
                log.success(f"Converted: {Path(output).name} ({self._human_size(out_size)})")
                return output
            else:
                raise RuntimeError(f"Conversion failed with code {process.returncode}")
                
        except Exception as e:
            log.error(f"Conversion error: {e}")
            raise
    
    def _human_size(self, size: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def list_presets(self) -> List[Dict]:
        """List available presets."""
        return [{"name": k, "description": v.name} for k, v in self.PRESETS.items()]
    
    def health_check(self) -> Dict:
        return {
            "status": "healthy" if shutil.which("ffmpeg") else "degraded",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "ffmpeg": bool(shutil.which("ffmpeg")),
            "presets": len(self.PRESETS)
        }
