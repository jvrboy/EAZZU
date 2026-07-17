"""
File Manager Tool
Advanced file operations, organization, and management.

Features:
- Smart file organization (by type, date, size, extension)
- Duplicate file detection and removal
- Bulk rename with patterns
- File search with content indexing
- Directory synchronization
- File watching and auto-actions
- Archive creation and extraction
- Secure file deletion
"""

import os
import shutil
import hashlib
import zipfile
import tarfile
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
import fnmatch

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from utils.logger import log


class FileManager(ToolBase):
    """Advanced file management tool."""
    
    metadata = ToolMetadata(
        name="file_manager",
        version="2.0.0",
        description="Organize, search, and manage files intelligently.",
        category="filesystem",
        tags=["files", "organize", "search", "cleanup", "batch"],
        provides=["file_operations", "organization", "cleanup"],
        permissions=["filesystem"]
    )
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
        self.category_map = {
            # Images
            ".jpg": "Images", ".jpeg": "Images", ".png": "Images", ".gif": "Images",
            ".bmp": "Images", ".svg": "Images", ".webp": "Images", ".ico": "Images",
            ".heic": "Images", ".raw": "Images", ".cr2": "Images", ".nef": "Images",
            ".psd": "Images", ".ai": "Images", ".eps": "Images",
            
            # Videos
            ".mp4": "Videos", ".avi": "Videos", ".mkv": "Videos", ".mov": "Videos",
            ".wmv": "Videos", ".flv": "Videos", ".webm": "Videos", ".m4v": "Videos",
            ".mpg": "Videos", ".mpeg": "Videos", ".3gp": "Videos", ".ts": "Videos",
            
            # Audio
            ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio", ".m4a": "Audio",
            ".ogg": "Audio", ".wma": "Audio", ".aac": "Audio", ".opus": "Audio",
            ".wma": "Audio",
            
            # Documents
            ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents",
            ".xls": "Documents", ".xlsx": "Documents", ".ppt": "Documents",
            ".pptx": "Documents", ".txt": "Documents", ".rtf": "Documents",
            ".odt": "Documents", ".ods": "Documents", ".odp": "Documents",
            ".pages": "Documents", ".numbers": "Documents", ".key": "Documents",
            ".epub": "Documents", ".mobi": "Documents", ".azw": "Documents",
            
            # Archives
            ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
            ".tar": "Archives", ".gz": "Archives", ".bz2": "Archives",
            ".xz": "Archives", ".tgz": "Archives", ".dmg": "Archives",
            ".iso": "Archives",
            
            # Code
            ".py": "Code", ".js": "Code", ".html": "Code", ".css": "Code",
            ".java": "Code", ".cpp": "Code", ".c": "Code", ".h": "Code",
            ".go": "Code", ".rs": "Code", ".rb": "Code", ".php": "Code",
            ".swift": "Code", ".kt": "Code", ".ts": "Code", ".jsx": "Code",
            ".tsx": "Code", ".json": "Code", ".xml": "Code", ".yaml": "Code",
            ".yml": "Code", ".sql": "Code", ".sh": "Code", ".bat": "Code",
            
            # Executables
            ".exe": "Programs", ".msi": "Programs", ".dmg": "Programs",
            ".pkg": "Programs", ".deb": "Programs", ".rpm": "Programs",
            
            # Fonts
            ".ttf": "Fonts", ".otf": "Fonts", ".woff": "Fonts", ".woff2": "Fonts",
            
            # 3D/Design
            ".obj": "3D", ".fbx": "3D", ".stl": "3D", ".blend": "3D",
            ".skp": "3D", ".dwg": "3D", ".dxf": "3D",
        }
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "scan")
        
        actions = {
            "scan": self.scan,
            "analyze": self.analyze_directory,
            "organize_by_type": self.organize_by_type,
            "organize_by_date": self.organize_by_date,
            "organize_by_size": self.organize_by_size,
            "find_duplicates": self.find_duplicates,
            "remove_duplicates": self.remove_duplicates,
            "batch_rename": self.batch_rename,
            "search": self.search_files,
            "cleanup": self.cleanup,
            "sync": self.sync_directories,
            "create_archive": self.create_archive,
            "extract_archive": self.extract_archive,
            "get_info": self.get_file_info,
            "secure_delete": self.secure_delete,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    def scan(self, directory: str = ".", pattern: str = "*", 
             recursive: bool = True, **kwargs) -> List[str]:
        """Scan directory for files."""
        log.info(f"Scanning: {directory}")
        
        path = Path(directory)
        if not path.exists():
            return []
        
        files = []
        if recursive:
            for f in path.rglob(pattern):
                if f.is_file():
                    files.append(str(f))
        else:
            for f in path.glob(pattern):
                if f.is_file():
                    files.append(str(f))
        
        log.info(f"Found {len(files)} files")
        return files
    
    def analyze_directory(self, directory: str = ".", **kwargs) -> Dict:
        """Analyze directory structure and provide statistics."""
        log.section("Directory Analysis")
        
        path = Path(directory)
        if not path.exists():
            return {"error": "Directory not found"}
        
        stats = {
            "total_files": 0,
            "total_dirs": 0,
            "total_size": 0,
            "by_extension": defaultdict(lambda: {"count": 0, "size": 0}),
            "by_category": defaultdict(lambda: {"count": 0, "size": 0}),
            "by_date": defaultdict(lambda: {"count": 0, "size": 0}),
            "largest_files": [],
            "oldest_files": [],
            "newest_files": [],
        }
        
        all_files = []
        
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    size = item.stat().st_size
                    mtime = datetime.fromtimestamp(item.stat().st_mtime)
                    ext = item.suffix.lower()
                    category = self.category_map.get(ext, "Other")
                    
                    stats["total_files"] += 1
                    stats["total_size"] += size
                    
                    stats["by_extension"][ext]["count"] += 1
                    stats["by_extension"][ext]["size"] += size
                    
                    stats["by_category"][category]["count"] += 1
                    stats["by_category"][category]["size"] += size
                    
                    date_key = mtime.strftime("%Y-%m")
                    stats["by_date"][date_key]["count"] += 1
                    stats["by_date"][date_key]["size"] += size
                    
                    all_files.append({
                        "path": str(item),
                        "size": size,
                        "modified": mtime,
                        "extension": ext,
                        "category": category
                    })
                    
                except (OSError, PermissionError):
                    continue
            elif item.is_dir():
                stats["total_dirs"] += 1
        
        # Sort for top lists
        all_files.sort(key=lambda x: x["size"], reverse=True)
        stats["largest_files"] = all_files[:10]
        
        all_files.sort(key=lambda x: x["modified"])
        stats["oldest_files"] = all_files[:10]
        stats["newest_files"] = all_files[-10:][::-1]
        
        # Convert defaultdicts
        stats["by_extension"] = dict(stats["by_extension"])
        stats["by_category"] = dict(stats["by_category"])
        stats["by_date"] = dict(stats["by_date"])
        
        # Summary
        log.info(f"Files: {stats['total_files']:,}")
        log.info(f"Directories: {stats['total_dirs']:,}")
        log.info(f"Total size: {self._human_size(stats['total_size'])}")
        
        for cat, data in sorted(stats["by_category"].items(), 
                               key=lambda x: x[1]["size"], reverse=True)[:5]:
            log.info(f"  {cat}: {data['count']} files ({self._human_size(data['size'])})")
        
        return stats
    
    def organize_by_type(self, directory: str = ".", 
                         output_dir: str = None,
                         copy: bool = False,
                         **kwargs) -> Dict:
        """Organize files into folders by type/category."""
        log.section("Organize by Type")
        
        src = Path(directory)
        dst = Path(output_dir) if output_dir else src
        
        if not src.exists():
            return {"error": "Source not found"}
        
        dst.mkdir(parents=True, exist_ok=True)
        
        moved = defaultdict(list)
        
        for file in src.iterdir():
            if file.is_file():
                ext = file.suffix.lower()
                category = self.category_map.get(ext, "Other")
                
                target_dir = dst / category
                target_dir.mkdir(exist_ok=True)
                
                target = target_dir / file.name
                
                # Handle duplicates
                if target.exists():
                    stem = file.stem
                    suffix = file.suffix
                    counter = 1
                    while target.exists():
                        target = target_dir / f"{stem}_{counter}{suffix}"
                        counter += 1
                
                try:
                    if copy:
                        shutil.copy2(file, target)
                    else:
                        shutil.move(str(file), str(target))
                    moved[category].append(file.name)
                except Exception as e:
                    log.error(f"Failed to move {file.name}: {e}")
        
        # Summary
        total = sum(len(v) for v in moved.values())
        log.success(f"Organized {total} files into {len(moved)} categories")
        
        return {
            "total_moved": total,
            "by_category": {k: len(v) for k, v in moved.items()},
            "details": dict(moved)
        }
    
    def organize_by_date(self, directory: str = ".",
                         output_dir: str = None,
                         date_format: str = "%Y/%Y-%m",
                         **kwargs) -> Dict:
        """Organize files by modification date."""
        log.section("Organize by Date")
        
        src = Path(directory)
        dst = Path(output_dir) if output_dir else src
        dst.mkdir(parents=True, exist_ok=True)
        
        moved = []
        
        for file in src.rglob("*"):
            if file.is_file() and file.parent == src:  # Only top-level
                mtime = datetime.fromtimestamp(file.stat().st_mtime)
                date_folder = dst / mtime.strftime(date_format)
                date_folder.mkdir(parents=True, exist_ok=True)
                
                target = date_folder / file.name
                try:
                    shutil.move(str(file), str(target))
                    moved.append(str(file.name))
                except Exception as e:
                    log.error(f"Failed: {e}")
        
        log.success(f"Organized {len(moved)} files by date")
        return {"moved": len(moved)}
    
    def organize_by_size(self, directory: str = ".", **kwargs) -> Dict:
        """Organize files into size categories."""
        src = Path(directory)
        
        categories = {
            "Small (< 1MB)": (0, 1024 * 1024),
            "Medium (1-100MB)": (1024 * 1024, 100 * 1024 * 1024),
            "Large (100MB-1GB)": (100 * 1024 * 1024, 1024 * 1024 * 1024),
            "Huge (> 1GB)": (1024 * 1024 * 1024, float('inf'))
        }
        
        moved = defaultdict(list)
        
        for file in src.iterdir():
            if file.is_file():
                size = file.stat().st_size
                
                for cat, (min_size, max_size) in categories.items():
                    if min_size <= size < max_size:
                        target_dir = src / cat
                        target_dir.mkdir(exist_ok=True)
                        try:
                            shutil.move(str(file), str(target_dir / file.name))
                            moved[cat].append(file.name)
                        except Exception as e:
                            log.error(f"Failed: {e}")
                        break
        
        return {k: len(v) for k, v in moved.items()}
    
    def find_duplicates(self, directory: str = ".", 
                        method: str = "hash",
                        **kwargs) -> Dict[str, List[str]]:
        """
        Find duplicate files.
        
        Args:
            directory: Directory to scan
            method: 'hash' (content), 'name', or 'size'
        """
        log.section("Duplicate File Detection")
        
        path = Path(directory)
        if not path.exists():
            return {}
        
        duplicates = defaultdict(list)
        
        if method == "hash":
            # Hash-based: most accurate
            file_hashes = defaultdict(list)
            
            for file in path.rglob("*"):
                if file.is_file():
                    try:
                        file_hash = self._hash_file(str(file))
                        file_hashes[file_hash].append(str(file))
                    except:
                        continue
            
            for file_hash, files in file_hashes.items():
                if len(files) > 1:
                    duplicates[file_hash] = files
        
        elif method == "name":
            # Name-based
            name_map = defaultdict(list)
            for file in path.rglob("*"):
                if file.is_file():
                    name_map[file.name].append(str(file))
            
            for name, files in name_map.items():
                if len(files) > 1:
                    duplicates[name] = files
        
        elif method == "size":
            # Size-based
            size_map = defaultdict(list)
            for file in path.rglob("*"):
                if file.is_file():
                    size_map[file.stat().st_size].append(str(file))
            
            for size, files in size_map.items():
                if len(files) > 1:
                    duplicates[str(size)] = files
        
        total_dups = sum(len(v) - 1 for v in duplicates.values())
        log.info(f"Found {len(duplicates)} duplicate groups ({total_dups} duplicate files)")
        
        return dict(duplicates)
    
    def _hash_file(self, filepath: str, block_size: int = 65536) -> str:
        """Calculate MD5 hash of file."""
        hasher = hashlib.md5()
        with open(filepath, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                hasher.update(block)
        return hasher.hexdigest()
    
    def remove_duplicates(self, directory: str = ".", 
                          keep: str = "first",  # first, newest, largest
                          **kwargs) -> Dict:
        """Remove duplicate files, keeping one."""
        duplicates = self.find_duplicates(directory, method="hash")
        
        removed = []
        kept = []
        
        for key, files in duplicates.items():
            if len(files) <= 1:
                continue
            
            # Decide which to keep
            if keep == "newest":
                files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
            elif keep == "largest":
                files.sort(key=lambda f: os.path.getsize(f), reverse=True)
            
            keep_file = files[0]
            kept.append(keep_file)
            
            for dup in files[1:]:
                try:
                    os.remove(dup)
                    removed.append(dup)
                    log.info(f"Removed duplicate: {dup}")
                except Exception as e:
                    log.error(f"Failed to remove {dup}: {e}")
        
        log.success(f"Removed {len(removed)} duplicates, kept {len(kept)}")
        return {"removed": removed, "kept": kept}
    
    def batch_rename(self, directory: str = ".", 
                     pattern: str = "{name}_{index}{ext}",
                     filter: str = "*",
                     **kwargs) -> List[Tuple[str, str]]:
        """
        Batch rename files with pattern.
        
        Patterns:
            {name} - original name
            {ext} - extension
            {index} - sequential number
            {date} - modification date
            {size} - file size
        """
        path = Path(directory)
        files = sorted([f for f in path.glob(filter) if f.is_file()])
        
        renamed = []
        
        for i, file in enumerate(files, 1):
            mtime = datetime.fromtimestamp(file.stat().st_mtime)
            
            new_name = pattern.format(
                name=file.stem,
                ext=file.suffix,
                index=f"{i:03d}",
                date=mtime.strftime("%Y%m%d"),
                size=file.stat().st_size
            )
            
            new_path = path / new_name
            
            if new_path.exists():
                new_path = path / f"{file.stem}_{i}{file.suffix}"
            
            try:
                file.rename(new_path)
                renamed.append((str(file), str(new_path)))
            except Exception as e:
                log.error(f"Rename failed: {e}")
        
        log.success(f"Renamed {len(renamed)} files")
        return renamed
    
    def search_files(self, directory: str = ".", 
                     query: str = "",
                     by_content: bool = False,
                     file_type: str = None,
                     min_size: int = None,
                     max_size: int = None,
                     **kwargs) -> List[str]:
        """Search files by name, content, or properties."""
        log.info(f"Searching: '{query}' in {directory}")
        
        path = Path(directory)
        results = []
        
        for file in path.rglob("*"):
            if not file.is_file():
                continue
            
            # Filter by type
            if file_type and not fnmatch.fnmatch(file.name, file_type):
                continue
            
            # Filter by size
            size = file.stat().st_size
            if min_size and size < min_size:
                continue
            if max_size and size > max_size:
                continue
            
            # Search by name
            if query.lower() in file.name.lower():
                results.append(str(file))
                continue
            
            # Search by content (for text files)
            if by_content and file.suffix.lower() in ['.txt', '.py', '.js', '.html', 
                                                       '.css', '.json', '.xml', '.md']:
                try:
                    with open(file, 'r', encoding='utf-8', errors='ignore') as f:
                        if query.lower() in f.read().lower():
                            results.append(str(file))
                except:
                    pass
        
        log.info(f"Found {len(results)} matches")
        return results
    
    def cleanup(self, directory: str = ".", 
                empty_dirs: bool = True,
                temp_files: bool = True,
                **kwargs) -> Dict:
        """Clean up directory - remove empty dirs and temp files."""
        log.section("Directory Cleanup")
        
        path = Path(directory)
        removed_dirs = 0
        removed_files = 0
        
        # Remove temp files
        if temp_files:
            temp_patterns = ['*.tmp', '*.temp', '~$*', '.DS_Store', 'Thumbs.db']
            for pattern in temp_patterns:
                for file in path.rglob(pattern):
                    try:
                        file.unlink()
                        removed_files += 1
                    except:
                        pass
        
        # Remove empty directories
        if empty_dirs:
            for dirpath in sorted(path.rglob("*"), key=lambda x: len(x.parts), reverse=True):
                if dirpath.is_dir() and dirpath != path:
                    try:
                        if not any(dirpath.iterdir()):
                            dirpath.rmdir()
                            removed_dirs += 1
                    except:
                        pass
        
        log.success(f"Removed {removed_files} temp files, {removed_dirs} empty dirs")
        return {"removed_files": removed_files, "removed_dirs": removed_dirs}
    
    def sync_directories(self, source: str, destination: str,
                         delete: bool = False,
                         **kwargs) -> Dict:
        """Synchronize two directories."""
        log.section(f"Sync: {source} → {destination}")
        
        src = Path(source)
        dst = Path(destination)
        dst.mkdir(parents=True, exist_ok=True)
        
        copied = 0
        updated = 0
        removed = 0
        
        for src_file in src.rglob("*"):
            if src_file.is_file():
                rel_path = src_file.relative_to(src)
                dst_file = dst / rel_path
                dst_file.parent.mkdir(parents=True, exist_ok=True)
                
                if not dst_file.exists():
                    shutil.copy2(src_file, dst_file)
                    copied += 1
                elif src_file.stat().st_mtime > dst_file.stat().st_mtime:
                    shutil.copy2(src_file, dst_file)
                    updated += 1
        
        if delete:
            for dst_file in dst.rglob("*"):
                if dst_file.is_file():
                    rel_path = dst_file.relative_to(dst)
                    src_file = src / rel_path
                    if not src_file.exists():
                        dst_file.unlink()
                        removed += 1
        
        log.success(f"Synced: {copied} copied, {updated} updated, {removed} removed")
        return {"copied": copied, "updated": updated, "removed": removed}
    
    def create_archive(self, source: str, output: str,
                       format: str = "zip",  # zip, tar, tar.gz
                       **kwargs) -> str:
        """Create archive from directory or file."""
        log.info(f"Creating archive: {output}")
        
        if format == "zip":
            with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED) as zf:
                src = Path(source)
                if src.is_dir():
                    for file in src.rglob("*"):
                        if file.is_file():
                            zf.write(file, file.relative_to(src))
                else:
                    zf.write(src, src.name)
        
        elif format in ("tar", "tar.gz", "tgz"):
            mode = "w:gz" if format in ("tar.gz", "tgz") else "w"
            with tarfile.open(output, mode) as tf:
                src = Path(source)
                if src.is_dir():
                    for file in src.rglob("*"):
                        tf.add(file, file.relative_to(src))
                else:
                    tf.add(src, src.name)
        
        size = os.path.getsize(output)
        log.success(f"Archive created: {output} ({self._human_size(size)})")
        return output
    
    def extract_archive(self, archive: str, output_dir: str = None,
                        **kwargs) -> List[str]:
        """Extract archive."""
        log.info(f"Extracting: {archive}")
        
        if not output_dir:
            output_dir = str(Path(archive).stem)
        
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        extracted = []
        
        if archive.endswith('.zip'):
            with zipfile.ZipFile(archive, 'r') as zf:
                zf.extractall(output_dir)
                extracted = zf.namelist()
        
        elif archive.endswith(('.tar', '.tar.gz', '.tgz', '.tar.bz2')):
            with tarfile.open(archive, 'r:*') as tf:
                tf.extractall(output_dir)
                extracted = tf.getnames()
        
        log.success(f"Extracted {len(extracted)} items to {output_dir}")
        return extracted
    
    def get_file_info(self, filepath: str, **kwargs) -> Dict:
        """Get detailed file information."""
        path = Path(filepath)
        
        if not path.exists():
            return {"error": "File not found"}
        
        stat = path.stat()
        
        return {
            "name": path.name,
            "path": str(path.absolute()),
            "size": stat.st_size,
            "size_human": self._human_size(stat.st_size),
            "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
            "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "accessed": datetime.fromtimestamp(stat.st_atime).isoformat(),
            "extension": path.suffix,
            "category": self.category_map.get(path.suffix.lower(), "Other"),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
            "is_symlink": path.is_symlink(),
        }
    
    def secure_delete(self, filepath: str, passes: int = 3, **kwargs) -> bool:
        """Securely delete file by overwriting."""
        log.info(f"Securely deleting: {filepath}")
        
        try:
            size = os.path.getsize(filepath)
            
            with open(filepath, 'r+b') as f:
                for pass_num in range(passes):
                    f.seek(0)
                    # Write random data
                    import random
                    f.write(bytes(random.randint(0, 255) for _ in range(size)))
                    f.flush()
                    os.fsync(f.fileno())
                    log.debug(f"Pass {pass_num + 1}/{passes}")
            
            os.remove(filepath)
            log.success(f"Securely deleted: {filepath}")
            return True
            
        except Exception as e:
            log.error(f"Secure delete failed: {e}")
            return False
    
    def _human_size(self, size_bytes: int) -> str:
        """Convert bytes to human readable."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def health_check(self) -> Dict:
        return {
            "status": "healthy",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "categories": len(set(self.category_map.values())),
            "supported_extensions": len(self.category_map)
        }
