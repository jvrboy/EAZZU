"""
Smart Organizer Tool
Intelligent file and media organization with AI-assisted categorization.

Features:
- Smart media organization (movies, TV shows, music, photos)
- Duplicate detection across multiple locations
- Auto-categorization using file content analysis
- Naming convention enforcement
- Library management (Plex/Kodi compatible)
- Schedule-based organization
- Conflict resolution
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from collections import defaultdict

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


class Organizer(ToolBase):
    """Smart file and media organizer."""
    
    metadata = ToolMetadata(
        name="organizer",
        version="2.0.0",
        description="Intelligently organize files and media libraries.",
        category="filesystem",
        tags=["organize", "media", "library", "smart"],
        provides=["smart_organization", "media_library", "naming"],
        permissions=["filesystem"]
    )
    
    # Media type patterns
    VIDEO_EXTENSIONS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.mpg', '.mpeg', '.ts'}
    AUDIO_EXTENSIONS = {'.mp3', '.wav', '.flac', '.m4a', '.ogg', '.wma', '.aac', '.opus'}
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.raw', '.cr2', '.nef'}
    DOC_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.epub'}
    ARCHIVE_EXTENSIONS = {'.zip', '.rar', '.7z', '.tar', '.gz', '.bz2'}
    
    # Movie/TV detection patterns
    TV_PATTERNS = [
        r'[Ss]?(\d+)[EeXx](\d+)',           # S01E02, 1x02
        r'[Ss]eason\s*(\d+).*?[Ee]pisode\s*(\d+)',  # Season 1 Episode 2
        r'(\d{1,2})\s*[xX]\s*(\d{1,2})',     # 1x02
    ]
    
    MOVIE_YEAR_PATTERN = r'(.*?)[.\s\[(]\s*(\d{4})\s*[.\])]'
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "organize_media")
        
        actions = {
            "organize_media": self.organize_media,
            "organize_tv_shows": self.organize_tv_shows,
            "organize_movies": self.organize_movies,
            "organize_music": self.organize_music,
            "organize_photos": self.organize_photos,
            "smart_sort": self.smart_sort,
            "detect_media_type": self.detect_media_type,
            "enforce_naming": self.enforce_naming,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    def detect_media_type(self, filepath: str, **kwargs) -> Dict:
        """
        Detect the type of media file and extract metadata from filename.
        
        Returns:
            Dict with type, title, season, episode, year, etc.
        """
        path = Path(filepath)
        filename = path.stem
        ext = path.suffix.lower()
        
        result = {
            "file": filepath,
            "extension": ext,
            "media_type": "unknown",
            "title": "",
            "year": None,
            "season": None,
            "episode": None,
            "confidence": 0,
        }
        
        # Determine media category
        if ext in self.VIDEO_EXTENSIONS:
            result["media_type"] = "video"
            
            # Check for TV show pattern
            for pattern in self.TV_PATTERNS:
                match = re.search(pattern, filename, re.IGNORECASE)
                if match:
                    result["media_type"] = "tv_show"
                    result["season"] = int(match.group(1))
                    result["episode"] = int(match.group(2))
                    
                    # Extract title (everything before season marker)
                    title_part = filename[:match.start()]
                    result["title"] = self._clean_title(title_part)
                    result["confidence"] = 0.9
                    return result
            
            # Check for movie pattern (year)
            match = re.search(self.MOVIE_YEAR_PATTERN, filename)
            if match:
                result["media_type"] = "movie"
                result["title"] = self._clean_title(match.group(1))
                result["year"] = int(match.group(2))
                result["confidence"] = 0.85
                return result
            
            # Generic video
            result["title"] = self._clean_title(filename)
            result["confidence"] = 0.5
            
        elif ext in self.AUDIO_EXTENSIONS:
            result["media_type"] = "audio"
            result["title"] = self._clean_title(filename)
            result["confidence"] = 0.7
            
        elif ext in self.IMAGE_EXTENSIONS:
            result["media_type"] = "image"
            result["title"] = self._clean_title(filename)
            result["confidence"] = 0.7
            
        elif ext in self.DOC_EXTENSIONS:
            result["media_type"] = "document"
            result["title"] = self._clean_title(filename)
            result["confidence"] = 0.6
            
        elif ext in self.ARCHIVE_EXTENSIONS:
            result["media_type"] = "archive"
            result["title"] = self._clean_title(filename)
            result["confidence"] = 0.8
        
        return result
    
    def organize_media(self, source_dir: str, output_dir: str = None,
                       **kwargs) -> Dict:
        """
        Automatically organize mixed media files.
        
        Sorts into: Movies/, TV Shows/, Music/, Photos/, Documents/, Other/
        """
        log.section("Smart Media Organization")
        
        src = Path(source_dir)
        if not src.exists():
            return {"error": "Source not found"}
        
        dst = Path(output_dir) if output_dir else src.parent / f"{src.name}_organized"
        dst.mkdir(parents=True, exist_ok=True)
        
        stats = defaultdict(list)
        
        # Scan all files
        files = [f for f in src.rglob("*") if f.is_file()]
        log.info(f"Scanning {len(files)} files...")
        
        for file in files:
            try:
                info = self.detect_media_type(str(file))
                media_type = info["media_type"]
                
                if media_type == "tv_show":
                    target = self._organize_tv_file(file, dst, info)
                elif media_type == "movie":
                    target = self._organize_movie_file(file, dst, info)
                elif media_type == "audio":
                    target = self._organize_audio_file(file, dst, info)
                elif media_type == "image":
                    target = self._organize_image_file(file, dst, info)
                elif media_type == "document":
                    target = dst / "Documents" / file.name
                elif media_type == "archive":
                    target = dst / "Archives" / file.name
                elif media_type == "video":
                    target = dst / "Videos" / file.name
                else:
                    target = dst / "Other" / file.name
                
                # Create directories and move
                target.parent.mkdir(parents=True, exist_ok=True)
                
                if not target.exists():
                    shutil.move(str(file), str(target))
                    stats[media_type].append(str(file.name))
                else:
                    # Handle duplicate
                    target = self._handle_duplicate(file, target)
                    if target:
                        shutil.move(str(file), str(target))
                        stats[media_type].append(str(file.name))
                
            except Exception as e:
                log.error(f"Error organizing {file}: {e}")
        
        # Summary
        log.section("Organization Complete")
        for media_type, files in sorted(stats.items()):
            log.info(f"  {media_type}: {len(files)} files")
        
        return {
            "total_files": sum(len(v) for v in stats.values()),
            "by_type": {k: len(v) for k, v in stats.items()},
            "output_dir": str(dst),
        }
    
    def organize_tv_shows(self, source_dir: str, output_dir: str = None,
                          **kwargs) -> Dict:
        """Organize TV show files into Show/Season X/ structure."""
        log.section("TV Show Organization")
        
        src = Path(source_dir)
        dst = Path(output_dir) if output_dir else src.parent / "TV Shows"
        dst.mkdir(parents=True, exist_ok=True)
        
        shows = defaultdict(lambda: defaultdict(list))
        
        # Detect and group
        for file in src.rglob("*"):
            if file.is_file() and file.suffix.lower() in self.VIDEO_EXTENSIONS:
                info = self.detect_media_type(str(file))
                if info["media_type"] == "tv_show":
                    shows[info["title"]][info["season"]].append(file)
        
        # Organize
        moved = 0
        for show_name, seasons in sorted(shows.items()):
            for season_num, episodes in sorted(seasons.items()):
                season_dir = dst / show_name / f"Season {season_num:02d}"
                season_dir.mkdir(parents=True, exist_ok=True)
                
                for ep_file in sorted(episodes):
                    ep_info = self.detect_media_type(str(ep_file))
                    ep_num = ep_info.get("episode", 0)
                    
                    # Rename to standard format
                    new_name = f"{show_name} - S{season_num:02d}E{ep_num:02d}{ep_file.suffix}"
                    target = season_dir / self._sanitize_filename(new_name)
                    
                    if not target.exists():
                        shutil.move(str(ep_file), str(target))
                        moved += 1
        
        log.success(f"Organized {moved} episodes into {len(shows)} shows")
        return {"shows": len(shows), "episodes_moved": moved}
    
    def organize_movies(self, source_dir: str, output_dir: str = None,
                        **kwargs) -> Dict:
        """Organize movie files into Movie (Year)/ structure."""
        log.section("Movie Organization")
        
        src = Path(source_dir)
        dst = Path(output_dir) if output_dir else src.parent / "Movies"
        dst.mkdir(parents=True, exist_ok=True)
        
        moved = 0
        
        for file in src.rglob("*"):
            if file.is_file() and file.suffix.lower() in self.VIDEO_EXTENSIONS:
                info = self.detect_media_type(str(file))
                if info["media_type"] == "movie":
                    movie_name = info["title"]
                    year = info.get("year", "")
                    
                    if year:
                        folder_name = f"{movie_name} ({year})"
                    else:
                        folder_name = movie_name
                    
                    movie_dir = dst / self._sanitize_filename(folder_name)
                    movie_dir.mkdir(parents=True, exist_ok=True)
                    
                    target = movie_dir / f"{self._sanitize_filename(movie_name)}{file.suffix}"
                    
                    if not target.exists():
                        shutil.move(str(file), str(target))
                        moved += 1
        
        log.success(f"Organized {moved} movies")
        return {"movies_moved": moved}
    
    def organize_music(self, source_dir: str, output_dir: str = None,
                       by_artist: bool = True, **kwargs) -> Dict:
        """Organize music files."""
        log.section("Music Organization")
        
        src = Path(source_dir)
        dst = Path(output_dir) if output_dir else src.parent / "Music"
        dst.mkdir(parents=True, exist_ok=True)
        
        moved = 0
        
        for file in src.rglob("*"):
            if file.is_file() and file.suffix.lower() in self.AUDIO_EXTENSIONS:
                # Try to read metadata
                artist = "Unknown Artist"
                album = "Unknown Album"
                
                try:
                    from mutagen import File as MutagenFile
                    audio = MutagenFile(str(file))
                    if audio and audio.tags:
                        for key in ['artist', 'TPE1', '\xa9ART']:
                            val = audio.tags.get(key)
                            if val:
                                artist = str(val[0]) if isinstance(val, list) else str(val)
                                break
                        for key in ['album', 'TALB', '\xa9alb']:
                            val = audio.tags.get(key)
                            if val:
                                album = str(val[0]) if isinstance(val, list) else str(val)
                                break
                except:
                    pass
                
                if by_artist:
                    target_dir = dst / self._sanitize_filename(artist) / self._sanitize_filename(album)
                else:
                    target_dir = dst / self._sanitize_filename(album)
                
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / file.name
                
                if not target.exists():
                    shutil.move(str(file), str(target))
                    moved += 1
        
        log.success(f"Organized {moved} music files")
        return {"files_moved": moved}
    
    def organize_photos(self, source_dir: str, output_dir: str = None,
                        by_date: bool = True, **kwargs) -> Dict:
        """Organize photos by date."""
        log.section("Photo Organization")
        
        src = Path(source_dir)
        dst = Path(output_dir) if output_dir else src.parent / "Photos"
        dst.mkdir(parents=True, exist_ok=True)
        
        moved = 0
        
        for file in src.rglob("*"):
            if file.is_file() and file.suffix.lower() in self.IMAGE_EXTENSIONS:
                # Try to get date from EXIF
                date = None
                try:
                    from PIL import Image
                    from PIL.ExifTags import TAGS
                    
                    img = Image.open(file)
                    exif = img._getexif()
                    if exif:
                        for tag_id, value in exif.items():
                            tag = TAGS.get(tag_id, tag_id)
                            if tag == 'DateTimeOriginal':
                                date = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                                break
                            elif tag == 'DateTime':
                                date = datetime.strptime(value, '%Y:%m:%d %H:%M:%S')
                except:
                    pass
                
                if not date:
                    # Use file modification time
                    date = datetime.fromtimestamp(file.stat().st_mtime)
                
                if by_date:
                    target_dir = dst / f"{date.year}" / f"{date.year}-{date.month:02d}"
                else:
                    target_dir = dst
                
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / file.name
                
                if not target.exists():
                    shutil.move(str(file), str(target))
                    moved += 1
        
        log.success(f"Organized {moved} photos")
        return {"photos_moved": moved}
    
    def smart_sort(self, directory: str, **kwargs) -> Dict:
        """Intelligent sorting that auto-detects and applies best organization."""
        log.section("Smart Sort")
        
        src = Path(directory)
        
        # Analyze contents
        counts = defaultdict(int)
        for file in src.rglob("*"):
            if file.is_file():
                info = self.detect_media_type(str(file))
                counts[info["media_type"]] += 1
        
        # Determine best organization strategy
        dominant = max(counts, key=counts.get) if counts else "unknown"
        log.info(f"Dominant media type: {dominant} ({counts[dominant]} files)")
        
        if dominant == "tv_show":
            return self.organize_tv_shows(directory, **kwargs)
        elif dominant == "movie":
            return self.organize_movies(directory, **kwargs)
        elif dominant == "audio":
            return self.organize_music(directory, **kwargs)
        elif dominant == "image":
            return self.organize_photos(directory, **kwargs)
        else:
            return self.organize_media(directory, **kwargs)
    
    def enforce_naming(self, directory: str, convention: str = "standard",
                       **kwargs) -> List[str]:
        """Rename files to match naming convention."""
        renamed = []
        
        for file in Path(directory).rglob("*"):
            if file.is_file():
                info = self.detect_media_type(str(file))
                
                if info["media_type"] == "tv_show" and info["title"]:
                    new_name = (f"{info['title']} - "
                               f"S{info['season']:02d}E{info['episode']:02d}"
                               f"{file.suffix}")
                elif info["media_type"] == "movie" and info["title"]:
                    year = f" ({info['year']})" if info["year"] else ""
                    new_name = f"{info['title']}{year}{file.suffix}"
                else:
                    continue
                
                new_name = self._sanitize_filename(new_name)
                target = file.parent / new_name
                
                if target != file and not target.exists():
                    file.rename(target)
                    renamed.append(f"{file.name} → {new_name}")
        
        log.info(f"Renamed {len(renamed)} files")
        return renamed
    
    # ─── Helpers ────────────────────────────────────────────────────────
    
    def _clean_title(self, title: str) -> str:
        """Clean and normalize title from filename."""
        # Replace dots, underscores with spaces
        title = title.replace('.', ' ').replace('_', ' ').replace('-', ' ')
        
        # Remove common tags
        tags_to_remove = [
            r'\b(720p|1080p|2160p|4K|HD|SD|UHD|HDTV|WEB-DL|BluRay|BRRip|DVDRip|WEBRip)\b',
            r'\b(x264|x265|HEVC|H264|H265|AVC)\b',
            r"\b(EXTENDED|UNRATED|REMASTERED|DIRECTORS? CUT)\b",
            r'\b(YIFY|RARBG|SPARKS|DRONES|SKIDROW)\b',
            r'\[.*?\]',
            r'\(.*?\)',
        ]
        
        for pattern in tags_to_remove:
            title = re.sub(pattern, '', title, flags=re.IGNORECASE)
        
        # Clean up
        title = re.sub(r'\s+', ' ', title).strip()
        title = title.title()
        
        return title
    
    def _sanitize_filename(self, name: str) -> str:
        """Sanitize for filesystem."""
        return re.sub(r'[\\/*?:"<>|]', '', name).strip()[:120]
    
    def _organize_tv_file(self, file: Path, dst: Path, info: Dict) -> Path:
        """Get target path for TV file."""
        show = self._sanitize_filename(info["title"])
        season = info.get("season", 0)
        return dst / "TV Shows" / show / f"Season {season:02d}" / file.name
    
    def _organize_movie_file(self, file: Path, dst: Path, info: Dict) -> Path:
        """Get target path for movie file."""
        title = self._sanitize_filename(info["title"])
        year = info.get("year", "")
        folder = f"{title} ({year})" if year else title
        return dst / "Movies" / folder / f"{title}{file.suffix}"
    
    def _organize_audio_file(self, file: Path, dst: Path, info: Dict) -> Path:
        """Get target path for audio file."""
        return dst / "Music" / file.name
    
    def _organize_image_file(self, file: Path, dst: Path, info: Dict) -> Path:
        """Get target path for image file."""
        return dst / "Photos" / file.name
    
    def _handle_duplicate(self, source: Path, target: Path) -> Optional[Path]:
        """Handle duplicate file. Returns new target or None."""
        # Compare sizes
        if source.stat().st_size == target.stat().st_size:
            log.debug(f"Exact duplicate, skipping: {source.name}")
            return None
        
        # Rename with suffix
        counter = 1
        stem = target.stem
        suffix = target.suffix
        parent = target.parent
        
        while target.exists():
            target = parent / f"{stem}_{counter}{suffix}"
            counter += 1
        
        return target
    
    def health_check(self) -> Dict:
        return {
            "status": "healthy",
            "name": self.metadata.name,
            "version": self.metadata.version,
        }
