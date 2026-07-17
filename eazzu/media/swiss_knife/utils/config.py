"""
Configuration Management for Swiss Knife
Centralized config with environment variable support.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class DownloadConfig:
    """Downloader configuration."""
    default_quality: str = "best"
    audio_format: str = "mp3"
    video_format: str = "mp4"
    download_dir: str = "downloads"
    max_concurrent: int = 3
    subtitle_langs: list = field(default_factory=lambda: ["en"])
    embed_subs: bool = True
    extract_audio: bool = False
    write_thumbnail: bool = True
    write_info_json: bool = False
    add_metadata: bool = True


@dataclass
class AudioConfig:
    """Audio processing configuration."""
    fingerprint_duration: int = 10
    recognition_api: str = "acoustid"
    acoustid_api_key: str = ""
    lastfm_api_key: str = ""
    lyrics_providers: list = field(default_factory=lambda: ["genius", "musixmatch", "azlyrics"])
    embed_lyrics: bool = True
    embed_album_art: bool = True
    fetch_album_info: bool = True
    auto_rename: bool = True
    naming_pattern: str = "{artist} - {title}"


@dataclass
class BrainConfig:
    """Brain/AI configuration."""
    model: str = "gpt-4"
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096
    context_window: int = 10
    memory_enabled: bool = True
    reasoning_depth: str = "deep"  # shallow, normal, deep
    personality: str = "helpful, analytical, creative"


@dataclass
class VisionConfig:
    """Vision system configuration."""
    ocr_engine: str = "easyocr"
    object_detection: bool = True
    face_detection: bool = False
    scene_recognition: bool = True
    image_captioning: bool = True
    supported_formats: list = field(default_factory=lambda: [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"])


@dataclass
class PipelineConfig:
    """Pipeline configuration."""
    auto_plan: bool = True
    max_retries: int = 3
    parallel_execution: bool = True
    checkpoint_interval: int = 5
    rollback_on_error: bool = True


@dataclass
class SwissConfig:
    """Main configuration container."""
    app_name: str = "Swiss Knife"
    version: str = "2.0.0"
    debug: bool = False
    log_level: str = "INFO"
    
    download: DownloadConfig = field(default_factory=DownloadConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    brain: BrainConfig = field(default_factory=BrainConfig)
    vision: VisionConfig = field(default_factory=VisionConfig)
    pipeline: PipelineConfig = field(default_factory=PipelineConfig)
    
    # Plugin settings
    plugin_dirs: list = field(default_factory=lambda: ["plugins"])
    auto_load_plugins: bool = True
    
    # System
    temp_dir: str = "temp"
    cache_dir: str = "cache"
    max_cache_size_mb: int = 500
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def save(self, path: str = "config.yaml"):
        """Save configuration to YAML file."""
        config_dict = self.to_dict()
        with open(path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False)
    
    @classmethod
    def load(cls, path: str = "config.yaml") -> "SwissConfig":
        """Load configuration from YAML file."""
        if not os.path.exists(path):
            config = cls()
            config.save(path)
            return config
        
        with open(path, 'r') as f:
            data = yaml.safe_load(f)
        
        # Build nested dataclasses from dict
        download = DownloadConfig(**data.get('download', {}))
        audio = AudioConfig(**data.get('audio', {}))
        brain = BrainConfig(**data.get('brain', {}))
        vision = VisionConfig(**data.get('vision', {}))
        pipeline = PipelineConfig(**data.get('pipeline', {}))
        
        return cls(
            app_name=data.get('app_name', 'Swiss Knife'),
            version=data.get('version', '2.0.0'),
            debug=data.get('debug', False),
            log_level=data.get('log_level', 'INFO'),
            download=download,
            audio=audio,
            brain=brain,
            vision=vision,
            pipeline=pipeline,
            plugin_dirs=data.get('plugin_dirs', ['plugins']),
            auto_load_plugins=data.get('auto_load_plugins', True),
            temp_dir=data.get('temp_dir', 'temp'),
            cache_dir=data.get('cache_dir', 'cache'),
            max_cache_size_mb=data.get('max_cache_size_mb', 500),
        )
    
    def get_env_overrides(self):
        """Apply environment variable overrides."""
        prefix = "SWISS_"
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # SWISS_DOWNLOAD_DEFAULT_QUALITY -> download.default_quality
                parts = key[len(prefix):].lower().split('_')
                # Simple mapping for top-level keys
                if len(parts) >= 2 and hasattr(self, parts[0]):
                    section = getattr(self, parts[0])
                    attr = '_'.join(parts[1:])
                    if hasattr(section, attr):
                        current = getattr(section, attr)
                        if isinstance(current, bool):
                            setattr(section, attr, value.lower() in ('true', '1', 'yes'))
                        elif isinstance(current, int):
                            setattr(section, attr, int(value))
                        elif isinstance(current, list):
                            setattr(section, attr, value.split(','))
                        else:
                            setattr(section, attr, value)


# Global config instance - will be initialized with env overrides
config = SwissConfig()
config.get_env_overrides()
