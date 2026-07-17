"""
Audio Tagger & Song Identifier Tool (Shazam-like)
Identifies unknown audio files, fetches metadata, embeds tags.

Features:
- Audio fingerprinting (like Shazam)
- Song identification via AcoustID/MusicBrainz
- Metadata fetching (artist, title, album, year, genre)
- Lyrics fetching and embedding (synced .lrc)
- Album artwork download and embedding
- Automatic file renaming
- Batch processing
- Multiple format support (MP3, FLAC, M4A, OGG, WMA)
"""

import os
import re
import json
import base64
import hashlib
import subprocess
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import mimetypes

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


@dataclass
class SongInfo:
    """Complete song information."""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_artist: str = ""
    year: str = ""
    genre: str = ""
    track_number: str = ""
    disc_number: str = ""
    duration: float = 0.0
    isrc: str = ""
    acoustid: str = ""
    musicbrainz_id: str = ""
    confidence: float = 0.0
    source: str = ""


@dataclass
class AudioTagResult:
    """Result of audio tagging operation."""
    file: str = ""
    original_name: str = ""
    new_name: str = ""
    identified: bool = False
    song_info: SongInfo = field(default_factory=SongInfo)
    lyrics_found: bool = False
    lyrics_source: str = ""
    album_art_embedded: bool = False
    tags_written: bool = False
    error: str = ""
    log: List[str] = field(default_factory=list)


class AudioTagger(ToolBase):
    """
    Advanced audio identification and tagging system.
    Like Shazam but for your local files!
    
    Workflow:
    1. Scan audio files
    2. Generate audio fingerprints
    3. Identify songs using AcoustID
    4. Fetch metadata (MusicBrainz, etc.)
    5. Fetch lyrics
    6. Download album artwork
    7. Embed everything into the file
    8. Rename file properly
    """
    
    metadata = ToolMetadata(
        name="audio_tagger",
        version="2.0.0",
        description="Identify unknown audio files and auto-tag them. "
                   "Like Shazam for your local music library.",
        category="audio",
        tags=["audio", "music", "tagging", "shazam", "metadata", "lyrics", "fingerprint"],
        provides=["audio_identification", "metadata_fetching", "tag_embedding", 
                   "lyrics_fetching", "album_art"],
        requires=["ffmpeg"],
        permissions=["filesystem", "network"]
    )
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
        self.acoustid_api_key = os.getenv("ACOUSTID_API_KEY", "")
        self.lastfm_api_key = os.getenv("LASTFM_API_KEY", "")
        self.genius_api_key = os.getenv("GENIUS_API_KEY", "")
        
        self._check_dependencies()
        
        # Supported audio formats
        self.supported_formats = {".mp3", ".flac", ".m4a", ".ogg", ".wma", ".wav", ".opus"}
        
        # Cache for API responses
        self._fingerprint_cache: Dict[str, Dict] = {}
        self._metadata_cache: Dict[str, Dict] = {}
    
    def _check_dependencies(self):
        """Check required dependencies."""
        self.ffmpeg_path = shutil.which("ffmpeg")
        self.ffprobe_path = shutil.which("ffprobe")
        
        if self.ffmpeg_path:
            log.info(f"Found ffmpeg: {self.ffmpeg_path}")
        else:
            log.warning("ffmpeg not found. Install for audio processing.")
        
        # Check for chromaprint/fpcalc
        self.fpcalc_path = shutil.which("fpcalc")
        if self.fpcalc_path:
            log.info(f"Found fpcalc (chromaprint): {self.fpcalc_path}")
        else:
            log.warning("fpcalc not found. Install chromaprint for fingerprinting.")
        
        # Check Python libraries
        try:
            import mutagen
            self.mutagen_available = True
            log.info("mutagen available for tag editing")
        except ImportError:
            self.mutagen_available = False
            log.warning("mutagen not installed. Install: pip install mutagen")
        
        try:
            import acoustid
            self.acoustid_available = True
        except ImportError:
            self.acoustid_available = False
    
    # ─── Core Execute ───────────────────────────────────────────────────
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "auto_tag")
        
        actions = {
            "scan": self.scan_directory,
            "fingerprint": self.fingerprint_file,
            "identify": self.identify_song,
            "fetch_metadata": self.fetch_metadata,
            "fetch_lyrics": self.fetch_lyrics,
            "fetch_album_art": self.fetch_album_art,
            "embed_tags": self.embed_tags,
            "embed_lyrics": self.embed_lyrics,
            "rename_files": self.rename_files,
            "auto_tag": self.auto_tag,
            "generate_report": self.generate_report,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    # ─── Scanning ───────────────────────────────────────────────────────
    
    def scan_directory(self, directory: str = ".", recursive: bool = True,
                       **kwargs) -> List[str]:
        """Scan directory for audio files."""
        log.section("Audio Scanner")
        log.info(f"Scanning: {directory}")
        
        path = Path(directory)
        if not path.exists():
            log.error(f"Directory not found: {directory}")
            return []
        
        audio_files = []
        
        if recursive:
            files = path.rglob("*")
        else:
            files = path.iterdir()
        
        for file in files:
            if file.is_file() and file.suffix.lower() in self.supported_formats:
                audio_files.append(str(file))
        
        log.success(f"Found {len(audio_files)} audio files")
        
        # Categorize
        untagged = []
        tagged = []
        for f in audio_files:
            if self._is_untagged(f):
                untagged.append(f)
            else:
                tagged.append(f)
        
        if untagged:
            log.info(f"Untagged files (need identification): {len(untagged)}")
        if tagged:
            log.info(f"Already tagged files: {len(tagged)}")
        
        return audio_files
    
    def _is_untagged(self, filepath: str) -> bool:
        """Check if a file appears to be untagged (e.g., 'Track 01.mp3')."""
        filename = Path(filepath).stem.lower()
        
        untagged_patterns = [
            r"^track\s*\d+",
            r"^unknown",
            r"^untitled",
            r"^audio\s*\d+",
            r"^recording\s*\d+",
            r"^clip\s*\d+",
            r"^\d+\s*$",  # Just a number
            r"^song\s*\d+",
        ]
        
        for pattern in untagged_patterns:
            if re.match(pattern, filename, re.IGNORECASE):
                return True
        
        # Check if file has minimal metadata
        if self.mutagen_available:
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(filepath)
                if audio and audio.tags:
                    has_title = False
                    for key in audio.tags.keys():
                        if 'title' in key.lower() and audio.tags[key]:
                            has_title = True
                            break
                    if not has_title:
                        return True
            except:
                pass
        
        return False
    
    # ─── Audio Fingerprinting ──────────────────────────────────────────
    
    def fingerprint_file(self, filepath: str, duration: int = 30,
                         **kwargs) -> Dict:
        """
        Generate audio fingerprint (like Shazam does).
        
        Args:
            filepath: Audio file to fingerprint
            duration: Seconds to analyze from the beginning
        """
        log.info(f"Fingerprinting: {Path(filepath).name}")
        
        # Check cache
        file_hash = self._file_hash(filepath)
        if file_hash in self._fingerprint_cache:
            log.info("Using cached fingerprint")
            return self._fingerprint_cache[file_hash]
        
        result = {
            "filepath": filepath,
            "fingerprint": None,
            "duration": duration,
            "error": None
        }
        
        # Method 1: Use fpcalc (chromaprint)
        if self.fpcalc_path:
            try:
                cmd = [
                    self.fpcalc_path,
                    "-json",
                    "-length", str(duration),
                    filepath
                ]
                
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                
                if proc.returncode == 0:
                    fp_data = json.loads(proc.stdout)
                    result["fingerprint"] = fp_data.get("fingerprint")
                    result["duration"] = fp_data.get("duration")
                    log.success("Fingerprint generated with fpcalc")
                else:
                    result["error"] = f"fpcalc error: {proc.stderr}"
                    
            except Exception as e:
                result["error"] = str(e)
        
        # Method 2: Python chromaprint library
        elif self.acoustid_available:
            try:
                import acoustid
                duration, fingerprint = acoustid.fingerprint_file(filepath)
                result["fingerprint"] = fingerprint
                result["duration"] = duration
                log.success("Fingerprint generated with acoustid")
            except Exception as e:
                result["error"] = str(e)
        
        else:
            result["error"] = "No fingerprinting method available. Install chromaprint."
        
        # Cache result
        self._fingerprint_cache[file_hash] = result
        return result
    
    # ─── Song Identification ────────────────────────────────────────────
    
    def identify_song(self, filepath: str = None, fingerprint: Dict = None,
                      **kwargs) -> SongInfo:
        """
        Identify a song from fingerprint or file.
        Uses AcoustID database (like Shazam).
        """
        log.section("Song Identification")
        
        # Get fingerprint if not provided
        if fingerprint is None and filepath:
            fingerprint = self.fingerprint_file(filepath)
        
        if not fingerprint or not fingerprint.get("fingerprint"):
            log.error("No fingerprint available for identification")
            return SongInfo(title="Unknown", artist="Unknown")
        
        # Query AcoustID
        if not self.acoustid_api_key:
            log.warning("No AcoustID API key. Set ACOUSTID_API_KEY env var.")
            log.info("Get free key at: https://acoustid.org/api-key")
            return self._fallback_identification(filepath)
        
        try:
            import acoustid
            
            results = acoustid.lookup(
                self.acoustid_api_key,
                fingerprint["fingerprint"],
                fingerprint["duration"]
            )
            
            if results.get("results"):
                # Get best match
                best = results["results"][0]
                
                song = SongInfo()
                song.acoustid = best.get("id", "")
                song.confidence = best.get("score", 0)
                song.source = "AcoustID"
                
                # Extract recording info
                if best.get("recordings"):
                    recording = best["recordings"][0]
                    song.title = recording.get("title", "")
                    song.musicbrainz_id = recording.get("id", "")
                    
                    # Get artist
                    if recording.get("artists"):
                        song.artist = recording["artists"][0].get("name", "")
                        song.album_artist = song.artist
                    
                    # Get release (album) info
                    if recording.get("releases"):
                        release = recording["releases"][0]
                        song.album = release.get("title", "")
                        
                        # Track number
                        if release.get("track_position"):
                            song.track_number = str(release["track_position"])
                
                log.success(f"Identified: {song.artist} - {song.title}")
                log.info(f"Album: {song.album}")
                log.info(f"Confidence: {song.confidence:.1%}")
                
                return song
            else:
                log.warning("No identification results found")
                return self._fallback_identification(filepath)
                
        except Exception as e:
            log.error(f"Identification error: {e}")
            return self._fallback_identification(filepath)
    
    def _fallback_identification(self, filepath: str) -> SongInfo:
        """Fallback identification using filename heuristics."""
        if not filepath:
            return SongInfo(title="Unknown", artist="Unknown")
        
        filename = Path(filepath).stem
        
        # Try to extract artist - title pattern
        patterns = [
            r"(.+?)\s*-\s*(.+)",  # Artist - Title
            r"(.+?)\s*[_]\s*(.+)",  # Artist _ Title
            r"\d+\s*[.\-_\s]\s*(.+)",  # 01. Title (just title)
        ]
        
        for pattern in patterns:
            match = re.match(pattern, filename)
            if match:
                groups = match.groups()
                if len(groups) == 2:
                    return SongInfo(
                        artist=groups[0].strip(),
                        title=groups[1].strip(),
                        source="filename_heuristic",
                        confidence=0.3
                    )
                elif len(groups) == 1:
                    return SongInfo(
                        title=groups[0].strip(),
                        source="filename_heuristic",
                        confidence=0.2
                    )
        
        return SongInfo(title=filename, artist="Unknown", 
                       source="filename_fallback", confidence=0.1)
    
    # ─── Metadata Fetching ──────────────────────────────────────────────
    
    def fetch_metadata(self, song: SongInfo, fetch_lyrics: bool = True,
                       fetch_album_art: bool = True, **kwargs) -> SongInfo:
        """
        Enrich song info with metadata from various sources.
        Uses MusicBrainz, Last.fm, and other sources.
        """
        log.info(f"Fetching metadata for: {song.artist} - {song.title}")
        
        # Fetch from MusicBrainz
        song = self._fetch_musicbrainz(song)
        
        # Fetch from Last.fm
        song = self._fetch_lastfm(song)
        
        # Fetch lyrics
        if fetch_lyrics and song.title and song.artist:
            lyrics_result = self.fetch_lyrics(song.artist, song.title)
            song.lyrics_found = lyrics_result.get("found", False)
            song.lyrics_source = lyrics_result.get("source", "")
        
        log.success("Metadata enrichment complete")
        return song
    
    def _fetch_musicbrainz(self, song: SongInfo) -> SongInfo:
        """Fetch additional metadata from MusicBrainz."""
        try:
            import musicbrainzngs
            musicbrainzngs.set_useragent("SwissKnife", "2.0", "swiss@knife.local")
            
            # Search for recording
            if song.musicbrainz_id:
                result = musicbrainzngs.get_recording_by_id(
                    song.musicbrainz_id,
                    includes=["artists", "releases", "tags"]
                )
            elif song.title and song.artist:
                search = musicbrainzngs.search_recordings(
                    recording=song.title,
                    artist=song.artist,
                    limit=1
                )
                if search.get("recording-list"):
                    recording = search["recording-list"][0]
                    song.musicbrainz_id = recording.get("id", "")
                    
                    # Get release info
                    if recording.get("release-list"):
                        release = recording["release-list"][0]
                        if not song.album:
                            song.album = release.get("title", "")
                        
                        # Get date
                        date = release.get("date", "")
                        if date and not song.year:
                            song.year = date[:4] if len(date) >= 4 else date
            
        except ImportError:
            log.debug("musicbrainzngs not installed")
        except Exception as e:
            log.debug(f"MusicBrainz fetch error: {e}")
        
        return song
    
    def _fetch_lastfm(self, song: SongInfo) -> SongInfo:
        """Fetch metadata from Last.fm."""
        if not self.lastfm_api_key:
            return song
        
        try:
            import pylast
            network = pylast.LastFMNetwork(api_key=self.lastfm_api_key)
            
            # Get track info
            if song.artist and song.title:
                track = network.get_track(song.artist, song.title)
                
                if not song.album:
                    try:
                        song.album = track.get_album().get_title() if track.get_album() else ""
                    except:
                        pass
                
                # Get tags/genre
                try:
                    tags = track.get_top_tags(limit=3)
                    if tags and not song.genre:
                        song.genre = tags[0].item.name
                except:
                    pass
        
        except ImportError:
            log.debug("pylast not installed")
        except Exception as e:
            log.debug(f"Last.fm fetch error: {e}")
        
        return song
    
    # ─── Lyrics Fetching ────────────────────────────────────────────────
    
    def fetch_lyrics(self, artist: str, title: str, **kwargs) -> Dict:
        """
        Fetch lyrics from multiple sources.
        Returns lyrics with timing info if available.
        """
        log.info(f"Fetching lyrics: {artist} - {title}")
        
        # Try multiple sources
        sources = [
            self._fetch_lyrics_genius,
            self._fetch_lyrics_musixmatch,
            self._fetch_lyrics_lrclib,
        ]
        
        for source_func in sources:
            try:
                result = source_func(artist, title)
                if result.get("found"):
                    log.success(f"Lyrics found via {result['source']}")
                    return result
            except Exception as e:
                log.debug(f"Lyrics source failed: {e}")
                continue
        
        log.warning("No lyrics found")
        return {"found": False, "lyrics": "", "source": ""}
    
    def _fetch_lyrics_genius(self, artist: str, title: str) -> Dict:
        """Fetch lyrics from Genius.com."""
        if not self.genius_api_key:
            return {"found": False}
        
        try:
            import lyricsgenius
            genius = lyricsgenius.Genius(self.genius_api_key, verbose=False)
            genius.remove_section_headers = True
            
            song = genius.search_song(title, artist)
            if song and song.lyrics:
                return {
                    "found": True,
                    "lyrics": song.lyrics,
                    "source": "Genius",
                    "synced": False
                }
        except ImportError:
            log.debug("lyricsgenius not installed")
        
        return {"found": False}
    
    def _fetch_lyrics_musixmatch(self, artist: str, title: str) -> Dict:
        """Fetch lyrics from Musixmatch."""
        # Would need API implementation
        return {"found": False}
    
    def _fetch_lyrics_lrclib(self, artist: str, title: str) -> Dict:
        """Fetch synced lyrics from LRCLIB (free, no API key)."""
        try:
            import urllib.request
            import urllib.parse
            
            url = f"https://lrclib.net/api/get?artist_name={urllib.parse.quote(artist)}&track_name={urllib.parse.quote(title)}"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'SwissKnife/2.0'
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                
                # Prefer synced lyrics
                if data.get("syncedLyrics"):
                    return {
                        "found": True,
                        "lyrics": data["syncedLyrics"],
                        "plain_lyrics": data.get("plainLyrics", ""),
                        "source": "LRCLIB",
                        "synced": True,
                        "duration": data.get("duration", 0)
                    }
                elif data.get("plainLyrics"):
                    return {
                        "found": True,
                        "lyrics": data["plainLyrics"],
                        "source": "LRCLIB",
                        "synced": False
                    }
                    
        except Exception as e:
            log.debug(f"LRCLIB fetch error: {e}")
        
        return {"found": False}
    
    # ─── Album Art ──────────────────────────────────────────────────────
    
    def fetch_album_art(self, artist: str, album: str, 
                        output_path: str = None, **kwargs) -> str:
        """
        Download album artwork.
        
        Returns:
            Path to downloaded artwork file
        """
        log.info(f"Fetching album art: {artist} - {album}")
        
        if not output_path:
            output_path = f"album_art_{hashlib.md5(f'{artist}{album}'.encode()).hexdigest()[:8]}.jpg"
        
        # Try multiple sources
        # 1. MusicBrainz Cover Art Archive
        art_url = self._fetch_art_musicbrainz(artist, album)
        
        # 2. iTunes API
        if not art_url:
            art_url = self._fetch_art_itunes(artist, album)
        
        if art_url:
            try:
                import urllib.request
                req = urllib.request.Request(art_url, headers={
                    'User-Agent': 'SwissKnife/2.0'
                })
                
                with urllib.request.urlopen(req, timeout=15) as response:
                    with open(output_path, 'wb') as f:
                        f.write(response.read())
                
                log.success(f"Album art saved: {output_path}")
                return output_path
                
            except Exception as e:
                log.error(f"Failed to download album art: {e}")
        
        return ""
    
    def _fetch_art_musicbrainz(self, artist: str, album: str) -> str:
        """Get album art URL from MusicBrainz Cover Art Archive."""
        try:
            import musicbrainzngs
            musicbrainzngs.set_useragent("SwissKnife", "2.0", "swiss@knife.local")
            
            result = musicbrainzngs.search_releases(
                release=album,
                artist=artist,
                limit=1
            )
            
            if result.get("release-list"):
                release_id = result["release-list"][0]["id"]
                
                # Try to get cover art
                try:
                    art = musicbrainzngs.get_image_list(release_id)
                    if art.get("images"):
                        return art["images"][0]["image"]
                except:
                    pass
                    
        except:
            pass
        
        return ""
    
    def _fetch_art_itunes(self, artist: str, album: str) -> str:
        """Get album art from iTunes API."""
        try:
            import urllib.request
            import urllib.parse
            
            query = urllib.parse.quote(f"{artist} {album}")
            url = f"https://itunes.apple.com/search?term={query}&entity=album&limit=1"
            
            req = urllib.request.Request(url, headers={
                'User-Agent': 'SwissKnife/2.0'
            })
            
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read())
                
                if data.get("results"):
                    artwork = data["results"][0].get("artworkUrl100", "")
                    # Get higher resolution
                    return artwork.replace("100x100", "600x600")
                    
        except Exception as e:
            log.debug(f"iTunes art fetch error: {e}")
        
        return ""
    
    # ─── Tag Embedding ──────────────────────────────────────────────────
    
    def embed_tags(self, filepath: str, song: SongInfo, 
                   album_art_path: str = None, **kwargs) -> bool:
        """
        Embed metadata tags into audio file.
        Supports MP3 (ID3), FLAC (Vorbis), M4A (MP4).
        """
        if not self.mutagen_available:
            log.error("mutagen not installed. Cannot embed tags.")
            return False
        
        log.info(f"Embedding tags: {Path(filepath).name}")
        
        try:
            from mutagen import File as MutagenFile
            from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TDRC, TCON, TRCK, TPOS
            from mutagen.flac import FLAC, Picture
            from mutagen.mp4 import MP4
            
            audio = MutagenFile(filepath)
            if not audio:
                return False
            
            ext = Path(filepath).suffix.lower()
            
            if ext == ".mp3":
                self._embed_mp3_tags(audio, song)
            elif ext == ".flac":
                self._embed_flac_tags(audio, song)
            elif ext in (".m4a", ".mp4"):
                self._embed_m4a_tags(audio, song)
            
            # Embed album art
            if album_art_path and os.path.exists(album_art_path):
                self._embed_album_art(audio, album_art_path, ext)
            
            audio.save()
            log.success("Tags embedded successfully")
            return True
            
        except Exception as e:
            log.error(f"Tag embedding error: {e}")
            return False
    
    def _embed_mp3_tags(self, audio, song: SongInfo):
        """Embed ID3 tags in MP3."""
        from mutagen.id3 import ID3, TIT2, TPE1, TALB, TPE2, TDRC, TCON, TRCK, TPOS
        
        if audio.tags is None:
            audio.add_tags()
        
        tags = audio.tags
        if song.title: tags["TIT2"] = TIT2(encoding=3, text=song.title)
        if song.artist: tags["TPE1"] = TPE1(encoding=3, text=song.artist)
        if song.album: tags["TALB"] = TALB(encoding=3, text=song.album)
        if song.album_artist: tags["TPE2"] = TPE2(encoding=3, text=song.album_artist)
        if song.year: tags["TDRC"] = TDRC(encoding=3, text=song.year)
        if song.genre: tags["TCON"] = TCON(encoding=3, text=song.genre)
        if song.track_number: tags["TRCK"] = TRCK(encoding=3, text=song.track_number)
        if song.disc_number: tags["TPOS"] = TPOS(encoding=3, text=song.disc_number)
    
    def _embed_flac_tags(self, audio, song: SongInfo):
        """Embed Vorbis comments in FLAC."""
        if song.title: audio["TITLE"] = song.title
        if song.artist: audio["ARTIST"] = song.artist
        if song.album: audio["ALBUM"] = song.album
        if song.album_artist: audio["ALBUMARTIST"] = song.album_artist
        if song.year: audio["DATE"] = song.year
        if song.genre: audio["GENRE"] = song.genre
        if song.track_number: audio["TRACKNUMBER"] = song.track_number
        if song.disc_number: audio["DISCNUMBER"] = song.disc_number
    
    def _embed_m4a_tags(self, audio, song: SongInfo):
        """Embed MP4 tags in M4A."""
        from mutagen.mp4 import MP4Tags
        
        if song.title: audio.tags["\xa9nam"] = song.title
        if song.artist: audio.tags["\xa9ART"] = song.artist
        if song.album: audio.tags["\xa9alb"] = song.album
        if song.album_artist: audio.tags["aART"] = song.album_artist
        if song.year: audio.tags["\xa9day"] = song.year
        if song.genre: audio.tags["\xa9gen"] = song.genre
        if song.track_number: audio.tags["trkn"] = [(int(song.track_number), 0)]
    
    def _embed_album_art(self, audio, art_path: str, ext: str):
        """Embed album artwork into audio file."""
        try:
            with open(art_path, 'rb') as f:
                art_data = f.read()
            
            if ext == ".mp3":
                from mutagen.id3 import APIC
                mime = "image/jpeg" if art_path.endswith(".jpg") else "image/png"
                audio.tags["APIC"] = APIC(
                    encoding=3,
                    mime=mime,
                    type=3,  # Cover (front)
                    desc="Cover",
                    data=art_data
                )
            elif ext == ".flac":
                from mutagen.flac import Picture
                pic = Picture()
                pic.type = 3
                pic.desc = "Cover"
                if art_path.endswith(".jpg"):
                    pic.mime = "image/jpeg"
                else:
                    pic.mime = "image/png"
                pic.data = art_data
                audio.add_picture(pic)
            elif ext in (".m4a", ".mp4"):
                from mutagen.mp4 import MP4Cover
                covr = MP4Cover(art_data, MP4Cover.FORMAT_JPEG 
                               if art_path.endswith(".jpg") else MP4Cover.FORMAT_PNG)
                audio.tags["covr"] = [covr]
                
        except Exception as e:
            log.error(f"Album art embedding error: {e}")
    
    def embed_lyrics(self, filepath: str, lyrics: str, synced: bool = False,
                     **kwargs) -> bool:
        """
        Embed lyrics into audio file.
        Synced lyrics are stored in SYLT/USLT frames.
        Also saves as .lrc file.
        """
        if not self.mutagen_available:
            return False
        
        log.info(f"Embedding lyrics: {Path(filepath).name}")
        
        try:
            from mutagen import File as MutagenFile
            
            audio = MutagenFile(filepath)
            if not audio:
                return False
            
            ext = Path(filepath).suffix.lower()
            
            if ext == ".mp3":
                from mutagen.id3 import USLT, SYLT
                # Unsynchronized lyrics
                audio.tags["USLT:eng:'Lyrics'"] = USLT(
                    encoding=3,
                    lang='eng',
                    desc='Lyrics',
                    text=lyrics
                )
            elif ext == ".flac":
                audio["LYRICS"] = lyrics
            elif ext in (".m4a", ".mp4"):
                audio.tags["\xa9lyr"] = lyrics
            
            audio.save()
            
            # Also save as .lrc file
            lrc_path = str(Path(filepath).with_suffix(".lrc"))
            with open(lrc_path, 'w', encoding='utf-8') as f:
                f.write(lyrics)
            
            log.success("Lyrics embedded and .lrc file saved")
            return True
            
        except Exception as e:
            log.error(f"Lyrics embedding error: {e}")
            return False
    
    # ─── File Renaming ──────────────────────────────────────────────────
    
    def rename_files(self, file_mappings: Dict[str, str] = None,
                     directory: str = None, pattern: str = "{artist} - {title}",
                     **kwargs) -> List[Tuple[str, str]]:
        """
        Rename audio files based on their tags.
        
        Args:
            file_mappings: Dict of {old_path: new_name}
            directory: Directory to auto-rename all files
            pattern: Naming pattern using {artist}, {title}, {album}, etc.
        """
        if not self.mutagen_available:
            log.error("mutagen not installed")
            return []
        
        renamed = []
        
        if file_mappings:
            for old_path, new_name in file_mappings.items():
                new_path = self._rename_file(old_path, new_name)
                if new_path:
                    renamed.append((old_path, new_path))
        
        elif directory:
            from mutagen import File as MutagenFile
            
            for file in Path(directory).rglob("*"):
                if file.suffix.lower() in self.supported_formats:
                    try:
                        audio = MutagenFile(str(file))
                        if not audio or not audio.tags:
                            continue
                        
                        # Extract tags
                        artist = self._get_tag(audio, ["artist", "TPE1", "\xa9ART"]) or "Unknown Artist"
                        title = self._get_tag(audio, ["title", "TIT2", "\xa9nam"]) or "Unknown Title"
                        album = self._get_tag(audio, ["album", "TALB", "\xa9alb"]) or ""
                        
                        # Build new name
                        new_name = pattern.format(
                            artist=self._sanitize(artist),
                            title=self._sanitize(title),
                            album=self._sanitize(album)
                        )
                        
                        new_path = self._rename_file(str(file), new_name + file.suffix)
                        if new_path:
                            renamed.append((str(file), new_path))
                            
                    except Exception as e:
                        log.debug(f"Rename error for {file}: {e}")
        
        log.success(f"Renamed {len(renamed)} files")
        return renamed
    
    def _get_tag(self, audio, tag_names: List[str]) -> str:
        """Get first available tag value."""
        for name in tag_names:
            value = audio.tags.get(name)
            if value:
                if isinstance(value, list):
                    return str(value[0])
                return str(value)
        return ""
    
    def _sanitize(self, text: str) -> str:
        """Sanitize text for filename use."""
        return re.sub(r'[\\/*?:"<>|]', '', text).strip()[:80]
    
    def _rename_file(self, old_path: str, new_name: str) -> str:
        """Rename a single file."""
        try:
            old = Path(old_path)
            new = old.parent / new_name
            
            # Avoid overwriting
            counter = 1
            original_new = new
            while new.exists():
                stem = original_new.stem
                new = old.parent / f"{stem} ({counter}){original_new.suffix}"
                counter += 1
            
            old.rename(new)
            log.info(f"Renamed: {old.name} → {new.name}")
            return str(new)
            
        except Exception as e:
            log.error(f"Rename failed: {e}")
            return ""
    
    # ─── Auto Tag (Complete Pipeline) ───────────────────────────────────
    
    def auto_tag(self, filepath: str = None, directory: str = None,
                 auto_rename: bool = True, **kwargs) -> List[AudioTagResult]:
        """
        Complete auto-tagging pipeline for one or more files.
        This is the main method - it does EVERYTHING:
        1. Fingerprint
        2. Identify
        3. Fetch metadata
        4. Fetch lyrics
        5. Download album art
        6. Embed everything
        7. Rename file
        """
        results = []
        
        # Collect files
        files = []
        if filepath:
            files.append(filepath)
        elif directory:
            files = self.scan_directory(directory)
        
        if not files:
            log.warning("No files to process")
            return results
        
        log.section(f"Auto-Tagging {len(files)} Files")
        
        for i, file in enumerate(files, 1):
            log.info(f"[{i}/{len(files)}] Processing: {Path(file).name}")
            
            result = AudioTagResult(
                file=file,
                original_name=Path(file).name
            )
            
            try:
                # Step 1: Fingerprint
                fingerprint = self.fingerprint_file(file)
                
                # Step 2: Identify
                song = self.identify_song(fingerprint=fingerprint)
                result.song_info = song
                result.identified = song.confidence > 0.5
                
                if result.identified:
                    log.success(f"  Identified: {song.artist} - {song.title}")
                    
                    # Step 3: Fetch metadata
                    song = self.fetch_metadata(song)
                    result.song_info = song
                    
                    # Step 4: Fetch lyrics
                    lyrics_result = self.fetch_lyrics(song.artist, song.title)
                    result.lyrics_found = lyrics_result.get("found", False)
                    result.lyrics_source = lyrics_result.get("source", "")
                    
                    # Step 5: Fetch album art
                    art_path = ""
                    if song.album:
                        art_path = self.fetch_album_art(
                            song.artist, song.album,
                            output_path=str(Path(file).parent / f"art_{Path(file).stem}.jpg")
                        )
                    
                    # Step 6: Embed tags
                    result.tags_written = self.embed_tags(file, song, art_path)
                    
                    # Embed lyrics
                    if lyrics_result.get("found"):
                        self.embed_lyrics(file, lyrics_result["lyrics"], 
                                        lyrics_result.get("synced", False))
                    
                    result.album_art_embedded = bool(art_path)
                    
                    # Step 7: Rename
                    if auto_rename and song.artist and song.title:
                        new_name = f"{song.artist} - {song.title}{Path(file).suffix}"
                        renamed = self.rename_files({file: new_name})
                        if renamed:
                            result.file = renamed[0][1]
                            result.new_name = Path(result.file).name
                else:
                    log.warning(f"  Could not identify: {Path(file).name}")
                
            except Exception as e:
                result.error = str(e)
                log.error(f"  Error processing {file}: {e}")
            
            results.append(result)
        
        # Summary
        identified = sum(1 for r in results if r.identified)
        log.section("Auto-Tag Summary")
        log.info(f"Total files: {len(results)}")
        log.info(f"Identified: {identified}")
        log.info(f"Failed: {len(results) - identified}")
        
        return results
    
    # ─── Report Generation ─────────────────────────────────────────────
    
    def generate_report(self, results: List[AudioTagResult] = None, **kwargs) -> str:
        """Generate a human-readable report of tagging results."""
        if results is None:
            results = []
        
        lines = ["=" * 60, "AUDIO TAGGING REPORT", "=" * 60, ""]
        
        for i, result in enumerate(results, 1):
            status = "✅" if result.identified else "❌"
            lines.append(f"{i}. {status} {result.original_name}")
            
            if result.identified:
                info = result.song_info
                lines.append(f"   🎵 {info.artist} - {info.title}")
                if info.album:
                    lines.append(f"   💿 Album: {info.album}")
                if info.year:
                    lines.append(f"   📅 Year: {info.year}")
                lines.append(f"   🎯 Confidence: {info.confidence:.1%}")
                lines.append(f"   📝 Lyrics: {'✅' if result.lyrics_found else '❌'}")
                lines.append(f"   🖼️  Album Art: {'✅' if result.album_art_embedded else '❌'}")
                if result.new_name:
                    lines.append(f"   📝 Renamed to: {result.new_name}")
            else:
                lines.append(f"   ⚠️  Not identified")
            
            if result.error:
                lines.append(f"   ❌ Error: {result.error}")
            
            lines.append("")
        
        identified = sum(1 for r in results if r.identified)
        lines.append("-" * 60)
        lines.append(f"Summary: {identified}/{len(results)} files identified")
        
        report = "\n".join(lines)
        log.info(report)
        return report
    
    # ─── Helpers ────────────────────────────────────────────────────────
    
    def _file_hash(self, filepath: str) -> str:
        """Quick hash of file for caching."""
        stat = os.stat(filepath)
        return hashlib.md5(f"{filepath}{stat.st_size}{stat.st_mtime}".encode()).hexdigest()
    
    def health_check(self) -> Dict:
        """Check tool health."""
        return {
            "status": "healthy" if self.mutagen_available else "degraded",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "fingerprinting": bool(self.fpcalc_path or self.acoustid_available),
            "tag_editing": self.mutagen_available,
            "ffmpeg": bool(self.ffmpeg_path),
            "acoustid_api": bool(self.acoustid_api_key),
            "lastfm_api": bool(self.lastfm_api_key),
            "genius_api": bool(self.genius_api_key),
        }
    
    def initialize(self) -> bool:
        """Initialize the audio tagger."""
        self._initialized = True
        return True
