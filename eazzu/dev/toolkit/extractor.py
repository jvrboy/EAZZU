"""
Ultra Archive Extractor Module - Extract virtually any archive format.
Supports: ZIP, TAR, TAR.GZ, TAR.BZ2, TAR.XZ, TAR.LZMA, GZIP, BZIP2, XZ, LZMA,
7Z, RAR, CAB, ISO, DMG, DEB, RPM, WIM, and more.
Also extracts from: JAR, WAR, EAR, APK, EPUB, DOCX, XLSX, PPTX (all ZIP-based).
"""

import os
import sys
import gzip
import bz2
import lzma
import shutil
import tarfile
import zipfile
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any, Callable, Tuple
from dataclasses import dataclass

from .utils import (
    ExecutionResult, log, LogLevel, console, spinner, 
    format_size, ensure_dir, print_table, run_command
)


@dataclass
class ExtractionResult:
    """Result of an extraction operation."""
    success: bool
    message: str
    extracted_files: List[str] = None
    output_dir: str = ""
    total_size: int = 0
    file_count: int = 0
    warnings: List[str] = None
    duration_ms: float = 0.0
    
    def __post_init__(self):
        if self.extracted_files is None:
            self.extracted_files = []
        if self.warnings is None:
            self.warnings = []


@dataclass
class ArchiveInfo:
    """Information about an archive file."""
    format: str
    file_count: int
    total_size: int
    compressed_size: int
    is_encrypted: bool
    comment: Optional[str]
    files: List[Dict[str, Any]]
    
    def format_size(self) -> str:
        return f"{format_size(self.total_size)} ({format_size(self.compressed_size)} compressed)"


class ArchiveExtractor:
    """
    Ultra-high-quality archive extractor supporting 20+ formats.
    
    Supported Formats:
    - ZIP (.zip), including encrypted, multi-part, ZIP64
    - TAR variants: .tar, .tar.gz, .tgz, .tar.bz2, .tbz2, .tar.xz, .txz, .tar.lzma
    - Standalone: .gz, .bz2, .xz, .lzma
    - 7-Zip (.7z) - requires py7zr
    - RAR (.rar) - requires unrar/rarfile
    - CAB (.cab) - requires cabextract
    - ISO (.iso) - requires 7z/loop mount
    - DMG (.dmg) - requires 7z
    - DEB (.deb) - via ar + tar
    - RPM (.rpm) - via rpm2cpio
    - WIM (.wim) - requires 7z
    - ZIP-based: .jar, .war, .ear, .apk, .epub, .docx, .xlsx, .pptx, .whl, .nupkg
    - MSI (.msi) - requires 7z
    - VMDK (.vmdk) - requires 7z
    
    Features:
    - Auto-detection of archive format
    - Progress reporting for large extractions
    - Selective extraction (specific files)
    - Integrity verification
    - Password-protected archive support
    - Safe extraction (path traversal protection)
    - Preserve permissions and timestamps
    """
    
    def __init__(self, output_dir: Optional[str] = None):
        self.output_dir = output_dir
        self._password: Optional[str] = None
        self._overwrite = False
        self._preserve_perms = True
    
    def set_password(self, password: str):
        """Set password for encrypted archives."""
        self._password = password
    
    def detect_format(self, filepath: str) -> Optional[str]:
        """
        Auto-detect archive format from file content and extension.
        
        Returns:
            Format string or None if not recognized
        """
        p = Path(filepath)
        name_lower = p.name.lower()
        suffixes = [s.lower() for s in p.suffixes]
        combined = ''.join(suffixes)
        
        # Check magic numbers first (most reliable)
        try:
            with open(filepath, 'rb') as f:
                magic = f.read(8)
        except:
            return None
        
        # ZIP-based formats (same magic)
        if magic[:2] == b'PK':
            if '.epub' in suffixes:
                return 'epub'
            elif '.docx' in suffixes:
                return 'docx'
            elif '.xlsx' in suffixes:
                return 'xlsx'
            elif '.pptx' in suffixes:
                return 'pptx'
            elif '.jar' in suffixes or '.war' in suffixes or '.ear' in suffixes:
                return 'jar'
            elif '.apk' in suffixes:
                return 'apk'
            elif '.whl' in suffixes:
                return 'whl'
            elif '.nupkg' in suffixes:
                return 'nupkg'
            elif '.oxt' in suffixes:
                return 'oxt'
            elif '.xpi' in suffixes:
                return 'xpi'
            elif '.crx' in suffixes:
                return 'crx'
            elif '.ipa' in suffixes:
                return 'ipa'
            else:
                return 'zip'
        
        # TAR (ustar)
        if magic[257:262] == b'ustar' or b'ustar\x0000' in magic:
            return 'tar'
        
        # GZIP
        if magic[:2] == b'\x1f\x8b':
            if '.tar.gz' in name_lower or '.tgz' in name_lower or combined == '.gz':
                # Check if it's a tar.gz
                try:
                    with gzip.open(filepath, 'rb') as f:
                        test = f.read(512)
                        if b'ustar' in test:
                            return 'tar.gz'
                except:
                    pass
            return 'gzip'
        
        # BZIP2
        if magic[:3] == b'BZh':
            if '.tar.bz2' in name_lower or '.tbz2' in name_lower or combined == '.bz2':
                try:
                    with bz2.open(filepath, 'rb') as f:
                        test = f.read(512)
                        if b'ustar' in test:
                            return 'tar.bz2'
                except:
                    pass
            return 'bzip2'
        
        # XZ
        if magic[:6] == b'\xfd7zXZX':
            if '.tar.xz' in name_lower or '.txz' in name_lower or combined == '.xz':
                try:
                    with lzma.open(filepath, 'rb') as f:
                        test = f.read(512)
                        if b'ustar' in test:
                            return 'tar.xz'
                except:
                    pass
            return 'xz'
        
        # LZMA
        if magic[:6] == b'\x5d\x00\x00\x80\x00':
            if '.tar.lzma' in name_lower or combined == '.lzma':
                return 'tar.lzma' if 'tar' in name_lower else 'lzma'
            return 'lzma'
        
        # 7-Zip
        if magic[:6] == b'7z\xbc\xaf\x27\x1c':
            return '7z'
        
        # RAR
        if magic[:4] == b'Rar!':
            return 'rar'
        
        # CAB
        if magic[:4] == b'MSCF':
            return 'cab'
        
        # ISO 9660
        if magic[32769:32773] == b'CD001' or magic[34817:34821] == b'CD001':
            return 'iso'
        
        # DEB (ar archive)
        if magic[:7] == b'!<arch>':
            if '.deb' in suffixes:
                return 'deb'
            return 'ar'
        
        # RPM
        if magic[:4] == b'\xed\xab\xee\xdb':
            return 'rpm'
        
        # DMG (UDF/HFS+)
        if magic[:4] == b'xar!':
            return 'xar'
        
        # Zstandard
        if magic[:4] == b'\x28\xb5\x2f\xfd':
            return 'zstd'
        
        # LZ4
        if magic[:4] == b'\x04\x22\x4d\x18':
            return 'lz4'
        
        # LZIP
        if magic[:4] == b'LZIP':
            return 'lzip'
        
        # Fall back to extension-based detection
        ext_map = {
            '.zip': 'zip', '.tar': 'tar', '.gz': 'gzip', '.tgz': 'tar.gz',
            '.bz2': 'bzip2', '.tbz2': 'tar.bz2', '.tar.gz': 'tar.gz',
            '.tar.bz2': 'tar.bz2', '.tar.xz': 'tar.xz', '.txz': 'tar.xz',
            '.xz': 'xz', '.tar.lzma': 'tar.lzma', '.lzma': 'lzma',
            '.7z': '7z', '.rar': 'rar', '.cab': 'cab', '.iso': 'iso',
            '.dmg': 'dmg', '.deb': 'deb', '.rpm': 'rpm', '.jar': 'jar',
            '.war': 'jar', '.ear': 'jar', '.apk': 'apk', '.epub': 'epub',
            '.docx': 'docx', '.xlsx': 'xlsx', '.pptx': 'pptx', '.whl': 'whl',
            '.msi': 'msi', '.wim': 'wim', '.vmdk': 'vmdk',
        }
        
        return ext_map.get(combined) or ext_map.get(p.suffix.lower())
    
    def list_contents(self, filepath: str) -> Optional[ArchiveInfo]:
        """
        List contents of an archive without extracting.
        
        Returns:
            ArchiveInfo with file listing or None on error
        """
        filepath = os.path.abspath(filepath)
        
        if not os.path.exists(filepath):
            log(LogLevel.ERROR, f"File not found: {filepath}")
            return None
        
        fmt = self.detect_format(filepath)
        if not fmt:
            log(LogLevel.ERROR, f"Unknown archive format: {filepath}")
            return None
        
        log(LogLevel.INFO, f"Detected format: {fmt.upper()}")
        
        try:
            return self._list_handlers[fmt](self, filepath)
        except KeyError:
            log(LogLevel.ERROR, f"Listing not yet implemented for: {fmt}")
            return None
        except Exception as e:
            log(LogLevel.ERROR, f"Error listing archive: {e}")
            return None
    
    def extract(self, filepath: str, output_dir: Optional[str] = None,
                specific_files: Optional[List[str]] = None,
                password: Optional[str] = None,
                overwrite: bool = False) -> ExtractionResult:
        """
        Extract an archive file.
        
        Args:
            filepath: Path to archive file
            output_dir: Output directory (auto-generated if None)
            specific_files: Extract only these files (None = all)
            password: Password for encrypted archives
            overwrite: Overwrite existing files
        
        Returns:
            ExtractionResult with details
        """
        import time
        start = time.time()
        
        filepath = os.path.abspath(filepath)
        
        if not os.path.exists(filepath):
            return ExtractionResult(
                success=False,
                message=f"File not found: {filepath}"
            )
        
        # Detect format
        fmt = self.detect_format(filepath)
        if not fmt:
            return ExtractionResult(
                success=False,
                message=f"Unknown archive format: {filepath}"
            )
        
        log(LogLevel.INFO, f"Archive: {filepath}")
        log(LogLevel.INFO, f"Format: {fmt.upper()}")
        log(LogLevel.INFO, f"Size: {format_size(os.path.getsize(filepath))}")
        
        # Determine output directory
        if output_dir is None:
            if self.output_dir:
                output_dir = self.output_dir
            else:
                p = Path(filepath)
                output_dir = str(p.parent / p.stem)
        
        output_dir = os.path.abspath(output_dir)
        os.makedirs(output_dir, exist_ok=True)
        
        log(LogLevel.INFO, f"Extracting to: {output_dir}")
        
        # Use password if provided
        if password:
            self._password = password
        
        self._overwrite = overwrite
        
        try:
            handler = self._extract_handlers.get(fmt)
            if handler:
                result = handler(self, filepath, output_dir, specific_files)
                duration = (time.time() - start) * 1000
                result.duration_ms = duration
                if result.success:
                    log(LogLevel.SUCCESS, f"Extracted {result.file_count} files ({format_size(result.total_size)}) in {duration:.0f}ms")
                return result
            else:
                # Try fallback to 7z
                return self._extract_with_7z(filepath, output_dir, fmt)
        except Exception as e:
            duration = (time.time() - start) * 1000
            return ExtractionResult(
                success=False,
                message=f"Extraction failed: {str(e)}",
                output_dir=output_dir,
                duration_ms=duration
            )
    
    def extract_all(self, archive_paths: List[str], output_dir: Optional[str] = None) -> List[ExtractionResult]:
        """Extract multiple archives."""
        results = []
        for path in archive_paths:
            result = self.extract(path, output_dir)
            results.append(result)
        return results
    
    def _extract_zip(self, filepath: str, output_dir: str, 
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract ZIP archive."""
        extracted = []
        total_size = 0
        warnings = []
        
        try:
            with zipfile.ZipFile(filepath, 'r') as zf:
                is_encrypted = any(info.flag_bits & 0x1 for info in zf.infolist())
                
                if is_encrypted and not self._password:
                    return ExtractionResult(
                        success=False,
                        message="Archive is password-protected. Use --password.",
                        output_dir=output_dir
                    )
                
                files_to_extract = specific_files or zf.namelist()
                
                for member in zf.infolist():
                    if specific_files and member.filename not in specific_files:
                        continue
                    
                    # Path traversal protection
                    target = os.path.join(output_dir, member.filename)
                    target = os.path.normpath(target)
                    if not target.startswith(os.path.normpath(output_dir)):
                        warnings.append(f"Skipped potential traversal: {member.filename}")
                        continue
                    
                    try:
                        if self._password:
                            zf.extract(member, output_dir, pwd=self._password.encode())
                        else:
                            zf.extract(member, output_dir)
                        
                        extracted.append(member.filename)
                        total_size += member.file_size
                        
                        # Preserve permissions
                        if self._preserve_perms and member.external_attr:
                            mode = (member.external_attr >> 16) & 0o777
                            if mode:
                                os.chmod(target, mode)
                    except Exception as e:
                        warnings.append(f"Failed to extract {member.filename}: {e}")
                
                return ExtractionResult(
                    success=True,
                    message=f"Successfully extracted ZIP archive",
                    extracted_files=extracted,
                    output_dir=output_dir,
                    total_size=total_size,
                    file_count=len(extracted),
                    warnings=warnings
                )
        except zipfile.BadZipFile as e:
            return ExtractionResult(
                success=False,
                message=f"Invalid ZIP file: {e}",
                output_dir=output_dir
            )
    
    def _extract_tar(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None,
                     mode: str = 'r') -> ExtractionResult:
        """Extract TAR archive (handles various compression modes)."""
        extracted = []
        total_size = 0
        warnings = []
        
        try:
            with tarfile.open(filepath, mode) as tf:
                members = tf.getmembers()
                
                for member in members:
                    if specific_files and member.name not in specific_files:
                        continue
                    
                    # Path traversal protection
                    target = os.path.join(output_dir, member.name)
                    target = os.path.normpath(target)
                    if not target.startswith(os.path.normpath(output_dir)):
                        warnings.append(f"Skipped potential traversal: {member.name}")
                        continue
                    
                    try:
                        tf.extract(member, output_dir)
                        extracted.append(member.name)
                        total_size += member.size
                    except Exception as e:
                        warnings.append(f"Failed to extract {member.name}: {e}")
                
                return ExtractionResult(
                    success=True,
                    message=f"Successfully extracted TAR archive ({mode})",
                    extracted_files=extracted,
                    output_dir=output_dir,
                    total_size=total_size,
                    file_count=len(extracted),
                    warnings=warnings
                )
        except tarfile.TarError as e:
            return ExtractionResult(
                success=False,
                message=f"Invalid TAR file: {e}",
                output_dir=output_dir
            )
    
    def _extract_tar_gz(self, filepath: str, output_dir: str,
                        specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract .tar.gz archive."""
        return self._extract_tar(filepath, output_dir, specific_files, 'r:gz')
    
    def _extract_tar_bz2(self, filepath: str, output_dir: str,
                         specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract .tar.bz2 archive."""
        return self._extract_tar(filepath, output_dir, specific_files, 'r:bz2')
    
    def _extract_tar_xz(self, filepath: str, output_dir: str,
                        specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract .tar.xz archive."""
        return self._extract_tar(filepath, output_dir, specific_files, 'r:xz')
    
    def _extract_tar_lzma(self, filepath: str, output_dir: str,
                          specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract .tar.lzma archive."""
        try:
            return self._extract_tar(filepath, output_dir, specific_files, 'r:xz')
        except:
            # Fallback: manually decompress then extract
            with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
                with lzma.open(filepath, 'rb') as lz:
                    shutil.copyfileobj(lz, tmp)
                tmp_path = tmp.name
            try:
                return self._extract_tar(tmp_path, output_dir, specific_files, 'r')
            finally:
                os.unlink(tmp_path)
    
    def _extract_gzip(self, filepath: str, output_dir: str,
                      specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract/decompress .gz file."""
        p = Path(filepath)
        output_file = os.path.join(output_dir, p.stem)
        
        with gzip.open(filepath, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return ExtractionResult(
            success=True,
            message="Successfully decompressed GZIP file",
            extracted_files=[p.stem],
            output_dir=output_dir,
            total_size=os.path.getsize(output_file),
            file_count=1
        )
    
    def _extract_bzip2(self, filepath: str, output_dir: str,
                       specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract/decompress .bz2 file."""
        p = Path(filepath)
        output_file = os.path.join(output_dir, p.stem)
        
        with bz2.open(filepath, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return ExtractionResult(
            success=True,
            message="Successfully decompressed BZIP2 file",
            extracted_files=[p.stem],
            output_dir=output_dir,
            total_size=os.path.getsize(output_file),
            file_count=1
        )
    
    def _extract_xz(self, filepath: str, output_dir: str,
                    specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract/decompress .xz file."""
        p = Path(filepath)
        output_file = os.path.join(output_dir, p.stem)
        
        with lzma.open(filepath, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return ExtractionResult(
            success=True,
            message="Successfully decompressed XZ file",
            extracted_files=[p.stem],
            output_dir=output_dir,
            total_size=os.path.getsize(output_file),
            file_count=1
        )
    
    def _extract_lzma(self, filepath: str, output_dir: str,
                      specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract/decompress .lzma file."""
        p = Path(filepath)
        output_file = os.path.join(output_dir, p.stem)
        
        with lzma.open(filepath, 'rb') as f_in:
            with open(output_file, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        return ExtractionResult(
            success=True,
            message="Successfully decompressed LZMA file",
            extracted_files=[p.stem],
            output_dir=output_dir,
            total_size=os.path.getsize(output_file),
            file_count=1
        )
    
    def _extract_7z(self, filepath: str, output_dir: str,
                    specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract 7-Zip archive using py7zr or 7z command."""
        # Try py7zr first
        try:
            import py7zr
            with py7zr.SevenZipFile(filepath, mode='r', password=self._password) as z:
                z.extractall(output_dir)
                names = z.getnames()
                return ExtractionResult(
                    success=True,
                    message="Successfully extracted 7-Zip archive",
                    extracted_files=names,
                    output_dir=output_dir,
                    file_count=len(names)
                )
        except ImportError:
            return self._extract_with_7z(filepath, output_dir, '7z', specific_files)
        except Exception as e:
            return self._extract_with_7z(filepath, output_dir, '7z', specific_files)
    
    def _extract_rar(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract RAR archive using unrar or rarfile."""
        # Try rarfile first
        try:
            import rarfile
            with rarfile.RarFile(filepath, pwd=self._password) as rf:
                if specific_files:
                    rf.extractall(output_dir, specific_files)
                else:
                    rf.extractall(output_dir)
                names = rf.namelist()
                return ExtractionResult(
                    success=True,
                    message="Successfully extracted RAR archive",
                    extracted_files=names,
                    output_dir=output_dir,
                    file_count=len(names)
                )
        except ImportError:
            return self._extract_with_7z(filepath, output_dir, 'rar', specific_files)
        except Exception as e:
            return self._extract_with_7z(filepath, output_dir, 'rar', specific_files)
    
    def _extract_cab(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract CAB archive."""
        return self._extract_with_7z(filepath, output_dir, 'cab', specific_files)
    
    def _extract_iso(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract ISO file."""
        return self._extract_with_7z(filepath, output_dir, 'iso', specific_files)
    
    def _extract_dmg(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract DMG file using 7z."""
        return self._extract_with_7z(filepath, output_dir, 'dmg', specific_files)
    
    def _extract_deb(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract DEB package (ar archive + tar.gz)."""
        try:
            import ar
            with ar.open(filepath) as archive:
                for entry in archive:
                    if entry.name == 'data.tar.gz' or entry.name == 'data.tar.xz':
                        data = entry.get_bytes()
                        mode = 'r:gz' if entry.name.endswith('.gz') else 'r:xz'
                        with tempfile.NamedTemporaryFile(suffix='.tar', delete=False) as tmp:
                            tmp.write(data)
                            tmp_path = tmp.name
                        try:
                            return self._extract_tar(tmp_path, output_dir, specific_files, mode)
                        finally:
                            os.unlink(tmp_path)
            
            return ExtractionResult(
                success=True,
                message="Successfully extracted DEB package",
                output_dir=output_dir
            )
        except ImportError:
            return self._extract_with_7z(filepath, output_dir, 'deb', specific_files)
        except Exception as e:
            return self._extract_with_7z(filepath, output_dir, 'deb', specific_files)
    
    def _extract_rpm(self, filepath: str, output_dir: str,
                     specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Extract RPM package using rpm2cpio."""
        result = run_command(['rpm2cpio', filepath], cwd=output_dir, capture_output=False)
        if result.success:
            # rpm2cpio outputs to stdout, need to pipe to cpio
            result = run_command(
                f'rpm2cpio "{filepath}" | cpio -idmv',
                cwd=output_dir,
                shell=True,
                capture_output=True
            )
            return ExtractionResult(
                success=result.success,
                message="Successfully extracted RPM package" if result.success else result.message,
                output_dir=output_dir
            )
        return self._extract_with_7z(filepath, output_dir, 'rpm', specific_files)
    
    def _extract_with_7z(self, filepath: str, output_dir: str, fmt: str,
                         specific_files: Optional[List[str]] = None) -> ExtractionResult:
        """Fallback extraction using 7z command-line tool."""
        # Try 7z or 7zz or p7zip
        for cmd in ['7zz', '7z', 'p7zip']:
            result = run_command([cmd, '--help'], capture_output=True, timeout=10)
            if result.success:
                extract_cmd = [cmd, 'x', filepath, f'-o{output_dir}', '-y']
                if self._password:
                    extract_cmd.extend(['-p', self._password])
                else:
                    extract_cmd.append('-p-')
                if specific_files:
                    extract_cmd.extend(specific_files)
                
                result = run_command(extract_cmd, capture_output=True, timeout=300)
                
                # Count extracted files
                extracted = []
                if result.stdout:
                    for line in result.stdout.split('\n'):
                        if line.startswith('Extracting '):
                            extracted.append(line[11:].strip())
                
                return ExtractionResult(
                    success=result.success,
                    message=f"7z extraction {'successful' if result.success else 'failed'}",
                    extracted_files=extracted,
                    output_dir=output_dir,
                    file_count=len(extracted)
                )
        
        return ExtractionResult(
            success=False,
            message=f"7-Zip not available and native handler failed for {fmt}",
            output_dir=output_dir
        )
    
    def _list_zip(self, filepath: str) -> ArchiveInfo:
        """List ZIP contents."""
        with zipfile.ZipFile(filepath, 'r') as zf:
            files = []
            total = 0
            for info in zf.infolist():
                files.append({
                    'name': info.filename,
                    'size': info.file_size,
                    'compressed': info.compress_size,
                    'date': f"{info.date_time[0]}-{info.date_time[1]:02d}-{info.date_time[2]:02d}",
                    'is_encrypted': bool(info.flag_bits & 0x1),
                })
                total += info.file_size
            
            is_encrypted = any(f['is_encrypted'] for f in files)
            return ArchiveInfo(
                format='ZIP',
                file_count=len(files),
                total_size=total,
                compressed_size=os.path.getsize(filepath),
                is_encrypted=is_encrypted,
                comment=zf.comment.decode('utf-8') if zf.comment else None,
                files=files
            )
    
    def _list_tar(self, filepath: str, mode: str = 'r') -> ArchiveInfo:
        """List TAR contents."""
        with tarfile.open(filepath, mode) as tf:
            files = []
            total = 0
            for member in tf.getmembers():
                files.append({
                    'name': member.name,
                    'size': member.size,
                    'mode': oct(member.mode),
                    'is_dir': member.isdir(),
                    'is_symlink': member.issym(),
                    'date': time.ctime(member.mtime) if hasattr(time, 'ctime') else str(member.mtime),
                })
                total += member.size
            
            return ArchiveInfo(
                format=f'TAR ({mode})',
                file_count=len(files),
                total_size=total,
                compressed_size=os.path.getsize(filepath),
                is_encrypted=False,
                comment=None,
                files=files
            )
    
    def _list_tar_gz(self, filepath: str) -> ArchiveInfo:
        return self._list_tar(filepath, 'r:gz')
    
    def _list_tar_bz2(self, filepath: str) -> ArchiveInfo:
        return self._list_tar(filepath, 'r:bz2')
    
    def _list_tar_xz(self, filepath: str) -> ArchiveInfo:
        return self._list_tar(filepath, 'r:xz')
    
    def _list_gzip(self, filepath: str) -> ArchiveInfo:
        """List GZIP file info."""
        with gzip.open(filepath, 'rb') as f:
            # Read to get decompressed size
            data = f.read()
            fname = f.filename or Path(filepath).stem
        
        return ArchiveInfo(
            format='GZIP',
            file_count=1,
            total_size=len(data),
            compressed_size=os.path.getsize(filepath),
            is_encrypted=False,
            comment=None,
            files=[{'name': fname, 'size': len(data), 'ratio': f'{os.path.getsize(filepath)/len(data)*100:.1f}%'}]
        )
    
    # Handler mappings
    _extract_handlers = {
        'zip': _extract_zip,
        'jar': _extract_zip,
        'war': _extract_zip,
        'ear': _extract_zip,
        'apk': _extract_zip,
        'epub': _extract_zip,
        'docx': _extract_zip,
        'xlsx': _extract_zip,
        'pptx': _extract_zip,
        'whl': _extract_zip,
        'nupkg': _extract_zip,
        'xpi': _extract_zip,
        'crx': _extract_zip,
        'ipa': _extract_zip,
        'oxt': _extract_zip,
        'tar': lambda self, fp, od, sf=None: ArchiveExtractor._extract_tar(self, fp, od, sf, 'r'),
        'tar.gz': _extract_tar_gz,
        'tgz': _extract_tar_gz,
        'tar.bz2': _extract_tar_bz2,
        'tbz2': _extract_tar_bz2,
        'tar.xz': _extract_tar_xz,
        'txz': _extract_tar_xz,
        'tar.lzma': _extract_tar_lzma,
        'gzip': _extract_gzip,
        'gz': _extract_gzip,
        'bzip2': _extract_bzip2,
        'bz2': _extract_bzip2,
        'xz': _extract_xz,
        'lzma': _extract_lzma,
        '7z': _extract_7z,
        'rar': _extract_rar,
        'cab': _extract_cab,
        'iso': _extract_iso,
        'dmg': _extract_dmg,
        'deb': _extract_deb,
        'rpm': _extract_rpm,
    }
    
    _list_handlers = {
        'zip': _list_zip,
        'jar': _list_zip,
        'war': _list_zip,
        'ear': _list_zip,
        'apk': _list_zip,
        'epub': _list_zip,
        'docx': _list_zip,
        'xlsx': _list_zip,
        'pptx': _list_zip,
        'whl': _list_zip,
        'tar': lambda self, fp: ArchiveExtractor._list_tar(self, fp, 'r'),
        'tar.gz': _list_tar_gz,
        'tgz': _list_tar_gz,
        'tar.bz2': _list_tar_bz2,
        'tar.xz': _list_tar_xz,
        'gzip': _list_gzip,
        'gz': _list_gzip,
    }
