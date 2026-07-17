"""
Universal Downloader Tool
Download videos, audio, and files from virtually any website.
Supports 1000+ sites through yt-dlp integration.

Features:
- Video download (any quality, any format)
- Audio extraction (mp3, wav, flac, m4a, ogg, aac)
- Playlist downloads
- Subtitle download
- Metadata embedding
- Thumbnail embedding
- Progress tracking
- Parallel downloads
- Stream recording (HLS/DASH)
"""

import os
import re
import json
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from urllib.parse import urlparse

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


@dataclass
class DownloadResult:
    """Result of a download operation."""
    success: bool
    files: List[str] = field(default_factory=list)
    title: str = ""
    duration: float = 0.0
    format: str = ""
    file_size: int = 0
    thumbnail: str = ""
    metadata: Dict = field(default_factory=dict)
    error: str = ""


class UniversalDownloader(ToolBase):
    """
    Universal media and file downloader.
    Uses yt-dlp as the backend for maximum site support.
    """
    
    metadata = ToolMetadata(
        name="universal_downloader",
        version="2.0.0",
        description="Download videos, audio, and files from 1000+ websites. "
                   "Supports YouTube, Spotify, SoundCloud, Vimeo, and many more.",
        category="media",
        tags=["download", "video", "audio", "youtube", "media"],
        provides=["download", "media_extraction", "streaming"],
        permissions=["filesystem", "network"]
    )
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
        self.download_dir = Path("downloads")
        self.download_dir.mkdir(exist_ok=True)
        self._progress_callbacks: List[Callable] = []
        self._check_ytdlp()
    
    def _check_ytdlp(self):
        """Check if yt-dlp is installed."""
        self.ytdlp_path = shutil.which("yt-dlp") or shutil.which("youtube-dl")
        if self.ytdlp_path:
            log.info(f"Found downloader: {self.ytdlp_path}")
        else:
            log.warning("yt-dlp not found. Install with: pip install yt-dlp")
    
    # ─── Core Execute ───────────────────────────────────────────────────
    
    def execute(self, *args, **kwargs) -> Any:
        """
        Main execution method. Dispatches to specific actions.
        
        Usage:
            downloader.execute(url="https://youtube.com/...", format="mp4")
            downloader.execute(action="download_audio", url="...", format="mp3")
        """
        action = kwargs.get("action", "download")
        
        # Direct URL download
        if "url" in kwargs and action == "download":
            return self.download(**kwargs)
        
        # Action-based dispatch
        actions = {
            "download": self.download,
            "download_audio": self.download_audio,
            "get_info": self.get_info,
            "get_playlist_info": self.get_playlist_info,
            "download_playlist": self.download_playlist,
            "validate": self.validate_url,
            "list_formats": self.list_formats,
            "stream": self.stream_download,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    # ─── Download Methods ───────────────────────────────────────────────
    
    def download(self, url: str, output_dir: str = None, 
                 format: str = "best", quality: str = None,
                 subtitle_langs: List[str] = None,
                 embed_subs: bool = True,
                 add_metadata: bool = True,
                 write_thumbnail: bool = True,
                 filename_template: str = "%(title)s.%(ext)s",
                 **kwargs) -> DownloadResult:
        """
        Download video from URL.
        
        Args:
            url: Video URL
            output_dir: Download directory
            format: Video format (best, mp4, webm, etc.)
            quality: Quality preference (best, worst, or resolution like 720)
            subtitle_langs: List of subtitle languages to download
            embed_subs: Embed subtitles in video file
            add_metadata: Write metadata to file
            write_thumbnail: Save thumbnail
            filename_template: Output filename template
        """
        if not self.ytdlp_path:
            return DownloadResult(success=False, error="yt-dlp not installed")
        
        log.section("Universal Downloader")
        log.info(f"URL: {url}")
        log.info(f"Format: {format}")
        
        output_dir = Path(output_dir or self.download_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Build yt-dlp command
        cmd = [
            self.ytdlp_path,
            url,
            "-o", str(output_dir / filename_template),
        ]
        
        # Format selection
        if quality:
            if quality == "best":
                cmd.extend(["-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"])
            elif quality == "worst":
                cmd.extend(["-f", "worst"])
            elif quality.isdigit():
                cmd.extend(["-f", f"best[height<={quality}]"])
        
        if format and format != "best":
            cmd.extend(["--merge-output-format", format])
        
        # Metadata options
        if add_metadata:
            cmd.append("--add-metadata")
        if write_thumbnail:
            cmd.append("--write-thumbnail")
        if embed_subs:
            cmd.append("--embed-subs")
        
        # Subtitles
        if subtitle_langs:
            cmd.extend(["--sub-langs", ",".join(subtitle_langs)])
            cmd.append("--write-subs")
        
        # Progress
        cmd.extend(["--newline", "--progress"])
        
        # Additional options
        cmd.extend([
            "--no-warnings",
            "--ignore-errors",
        ])
        
        # Execute
        result = self._run_ytdlp(cmd)
        
        if result["success"]:
            log.success(f"Download complete: {result.get('title', 'Unknown')}")
            return DownloadResult(
                success=True,
                files=result.get("files", []),
                title=result.get("title", ""),
                duration=result.get("duration", 0),
                format=format,
                metadata=result.get("info", {})
            )
        else:
            log.error(f"Download failed: {result.get('error', 'Unknown error')}")
            return DownloadResult(success=False, error=result.get("error", ""))
    
    def download_audio(self, url: str, format: str = "mp3", 
                       quality: int = 320, output_dir: str = None,
                       embed_thumbnail: bool = True,
                       add_metadata: bool = True,
                       **kwargs) -> DownloadResult:
        """
        Download and extract audio from URL.
        
        Args:
            url: Source URL
            format: Audio format (mp3, wav, flac, m4a, ogg, aac, opus)
            quality: Audio quality (kbps for lossy, bit depth for lossless)
            embed_thumbnail: Embed cover art
            add_metadata: Add ID3 tags
        """
        if not self.ytdlp_path:
            return DownloadResult(success=False, error="yt-dlp not installed")
        
        log.section("Audio Download")
        log.info(f"URL: {url}")
        log.info(f"Format: {format}, Quality: {quality}")
        
        output_dir = Path(output_dir or self.download_dir / "audio")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            self.ytdlp_path,
            url,
            "-x",  # Extract audio
            "--audio-format", format,
            "--audio-quality", str(quality),
            "-o", str(output_dir / "%(title)s.%(ext)s"),
        ]
        
        if embed_thumbnail:
            cmd.append("--embed-thumbnail")
        if add_metadata:
            cmd.append("--add-metadata")
        
        cmd.extend([
            "--newline",
            "--progress",
            "--no-warnings",
        ])
        
        result = self._run_ytdlp(cmd)
        
        return DownloadResult(
            success=result["success"],
            files=result.get("files", []),
            title=result.get("title", ""),
            format=format,
            error=result.get("error", "")
        )
    
    def get_info(self, url: str, **kwargs) -> Dict:
        """Get media information without downloading."""
        if not self.ytdlp_path:
            return {"error": "yt-dlp not installed"}
        
        log.info(f"Fetching info: {url}")
        
        cmd = [
            self.ytdlp_path,
            "--dump-json",
            "--no-download",
            url
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                # Extract useful info
                summary = {
                    "title": info.get("title"),
                    "duration": info.get("duration"),
                    "duration_string": info.get("duration_string"),
                    "uploader": info.get("uploader"),
                    "upload_date": info.get("upload_date"),
                    "view_count": info.get("view_count"),
                    "like_count": info.get("like_count"),
                    "description": info.get("description", "")[:500],
                    "thumbnail": info.get("thumbnail"),
                    "formats_count": len(info.get("formats", [])),
                    "subtitles": list(info.get("subtitles", {}).keys()),
                    "chapters": info.get("chapters", []),
                    "webpage_url": info.get("webpage_url"),
                    "extractor": info.get("extractor"),
                }
                
                log.info(f"Title: {summary['title']}")
                log.info(f"Duration: {summary.get('duration_string', 'Unknown')}")
                log.info(f"Uploader: {summary.get('uploader')}")
                
                return summary
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_playlist_info(self, url: str, **kwargs) -> Dict:
        """Get playlist information."""
        if not self.ytdlp_path:
            return {"error": "yt-dlp not installed"}
        
        log.info(f"Fetching playlist info: {url}")
        
        cmd = [
            self.ytdlp_path,
            "--flat-playlist",
            "--dump-single-json",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                entries = info.get("entries", [])
                summary = {
                    "title": info.get("title"),
                    "uploader": info.get("uploader"),
                    "entry_count": len(entries),
                    "entries": [
                        {
                            "title": e.get("title"),
                            "duration": e.get("duration"),
                            "url": e.get("url")
                        }
                        for e in entries[:20]  # First 20
                    ]
                }
                
                log.info(f"Playlist: {summary['title']} ({summary['entry_count']} items)")
                return summary
            else:
                return {"error": result.stderr}
                
        except Exception as e:
            return {"error": str(e)}
    
    def download_playlist(self, url: str, output_dir: str = None,
                          item_range: str = None, parallel: bool = False,
                          **kwargs) -> List[DownloadResult]:
        """
        Download entire playlist.
        
        Args:
            url: Playlist URL
            output_dir: Output directory
            item_range: Range like "1-10" or "1,3,5"
            parallel: Download multiple items in parallel
        """
        output_dir = Path(output_dir or self.download_dir / "playlists")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        playlist_name = self.get_playlist_info(url).get("title", "playlist")
        playlist_dir = output_dir / self._sanitize_filename(playlist_name)
        playlist_dir.mkdir(exist_ok=True)
        
        log.section(f"Playlist Download: {playlist_name}")
        
        cmd = [
            self.ytdlp_path,
            url,
            "-o", str(playlist_dir / "%(playlist_index)s - %(title)s.%(ext)s"),
        ]
        
        if item_range:
            cmd.extend(["--playlist-items", item_range])
        
        if parallel:
            cmd.extend(["-N", "3"])  # 3 parallel downloads
        
        cmd.extend([
            "--add-metadata",
            "--write-thumbnail",
            "--newline",
            "--progress",
        ])
        
        result = self._run_ytdlp(cmd)
        
        return [DownloadResult(
            success=result["success"],
            files=result.get("files", []),
            error=result.get("error", "")
        )]
    
    def list_formats(self, url: str, **kwargs) -> List[Dict]:
        """List available formats for a URL."""
        if not self.ytdlp_path:
            return []
        
        cmd = [
            self.ytdlp_path,
            "--list-formats",
            url
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            formats = []
            # Parse format list output
            for line in result.stdout.split("\n"):
                if re.match(r"^\d+", line.strip()):
                    parts = line.split()
                    if len(parts) >= 4:
                        formats.append({
                            "format_id": parts[0],
                            "extension": parts[1],
                            "resolution": parts[2] if "x" in parts[2] else "audio",
                            "note": " ".join(parts[3:])
                        })
            
            return formats
            
        except Exception as e:
            log.error(f"Failed to list formats: {e}")
            return []
    
    def validate_url(self, url: str, **kwargs) -> Dict:
        """Validate if URL is supported and accessible."""
        log.info(f"Validating URL: {url}")
        
        if not url or not url.startswith(("http://", "https://")):
            return {"valid": False, "error": "Invalid URL format"}
        
        if not self.ytdlp_path:
            return {"valid": False, "error": "yt-dlp not installed"}
        
        # Quick check with yt-dlp
        cmd = [self.ytdlp_path, "--no-download", "--ignore-no-formats-error", url]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 or "Available formats" in result.stderr:
                return {
                    "valid": True,
                    "url": url,
                    "extractor": self._detect_extractor(result.stdout + result.stderr)
                }
            else:
                return {
                    "valid": False,
                    "url": url,
                    "error": "URL not supported or content unavailable"
                }
                
        except subprocess.TimeoutExpired:
            return {"valid": False, "error": "Validation timeout"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def stream_download(self, url: str, output_file: str = None,
                        duration: int = None, **kwargs) -> DownloadResult:
        """
        Download live stream or HLS/DASH stream.
        
        Args:
            url: Stream URL
            output_file: Output file path
            duration: Recording duration in seconds
        """
        log.section("Stream Download")
        log.info(f"URL: {url}")
        
        if not output_file:
            output_file = str(self.download_dir / f"stream_{int(__import__('time').time())}.mp4")
        
        cmd = [
            self.ytdlp_path,
            url,
            "-o", output_file,
        ]
        
        if duration:
            cmd.extend(["--download-duration", str(duration)])
        
        cmd.extend([
            "--live-from-start",
            "--hls-use-mpegts",
            "--newline",
        ])
        
        result = self._run_ytdlp(cmd)
        
        return DownloadResult(
            success=result["success"],
            files=[output_file] if result["success"] else [],
            error=result.get("error", "")
        )
    
    # ─── Internal Methods ───────────────────────────────────────────────
    
    def _run_ytdlp(self, cmd: List[str]) -> Dict:
        """Run yt-dlp command and parse output."""
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            
            output_lines = []
            files_downloaded = []
            title = ""
            
            for line in process.stdout:
                line = line.strip()
                output_lines.append(line)
                
                # Parse progress
                if "[download]" in line and "%" in line:
                    log.info(line)
                elif "[ExtractAudio]" in line:
                    log.info(f"Extracting audio: {line}")
                elif "Destination:" in line:
                    filepath = line.split("Destination:")[1].strip()
                    files_downloaded.append(filepath)
                elif line.startswith("[download]") and "." in line:
                    # Title line
                    title = line.replace("[download]", "").strip()
                
                # Check for destination
                if "Destination:" in line:
                    path = line.split("Destination:")[1].strip()
                    files_downloaded.append(path)
            
            process.wait()
            
            success = process.returncode == 0
            
            return {
                "success": success,
                "files": files_downloaded,
                "title": title,
                "output": "\n".join(output_lines),
                "error": "" if success else "Download failed"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e), "files": []}
    
    def _detect_extractor(self, output: str) -> str:
        """Detect which extractor yt-dlp is using."""
        extractors = {
            "youtube": "YouTube",
            "spotify": "Spotify",
            "soundcloud": "SoundCloud",
            "vimeo": "Vimeo",
            "tiktok": "TikTok",
            "twitter": "Twitter/X",
            "instagram": "Instagram",
            "facebook": "Facebook",
            "reddit": "Reddit",
        }
        
        output_lower = output.lower()
        for key, name in extractors.items():
            if key in output_lower:
                return name
        return "Unknown"
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize a string for use as filename."""
        return re.sub(r'[^\w\s-]', '', name).strip()[:100]
    
    def health_check(self) -> Dict:
        """Check downloader health."""
        return {
            "status": "healthy" if self.ytdlp_path else "degraded",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "ytdlp_installed": bool(self.ytdlp_path),
            "ytdlp_path": self.ytdlp_path,
            "download_dir": str(self.download_dir)
        }
    
    def initialize(self) -> bool:
        """Initialize the downloader."""
        if not self.ytdlp_path:
            log.warning("yt-dlp not found. Attempting to install...")
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "yt-dlp"], 
                             capture_output=True, timeout=120)
                self._check_ytdlp()
            except:
                pass
        
        self._initialized = True
        return bool(self.ytdlp_path)


# Auto-register tool
import sys
if __name__ != "__main__":
    pass  # Tool is registered by kernel discovery
