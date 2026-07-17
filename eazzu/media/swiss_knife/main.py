#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════╗
║                    🇨🇭 SWISS KNIFE v2.0                          ║
║                                                                  ║
║  Universal Tool Platform - Download, Tag, Convert, Organize,    ║
║  Analyze, and Automate everything. Powered by AI Brain.          ║
╚══════════════════════════════════════════════════════════════════╝

Usage:
    python main.py [command] [options]

Commands:
    download <url>              Download video/audio from URL
    tag <directory>             Auto-identify and tag music files
    vision <image>              Analyze image with AI vision
    convert <file>              Convert media format
    organize <directory>        Smart file organization
    pipeline "<description>"    Create and run workflow pipeline
    brain "<question>"          Ask the AI brain
    status                      Show system status
    interactive                 Interactive mode

Examples:
    python main.py download https://youtube.com/watch?v=... --format mp3
    python main.py tag ~/Music --auto-rename
    python main.py vision photo.jpg
    python main.py convert video.avi --format mp4
    python main.py organize ~/Downloads --smart
    python main.py pipeline "Download playlist and convert to mp3"
    python main.py brain "How do I download audio from YouTube?"
"""

import os
import sys
import json
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.kernel import MicroKernel, ToolBase, ToolMetadata
from core.memory import MemorySystem
from core.brain import BrainSystem
from core.pipeline import PipelinePlanner, PipelineExecutor
from core.vision import VisionSystem
from utils.logger import log, SwissLogger
from utils.config import config


class SwissKnife:
    """
    Swiss Knife - The Ultimate Multi-Tool Platform.
    
    Architecture:
        ┌─────────────────────────────────────────┐
        │              CLI / API                   │
        └──────────────┬──────────────────────────┘
                       ▼
        ┌─────────────────────────────────────────┐
        │         Brain System (AI)               │
        │  • Reasoning • Planning • Memory        │
        └──────────────┬──────────────────────────┘
                       ▼
        ┌─────────────────────────────────────────┐
        │      Micro-Kernel (Plugin System)       │
        │  • Tool Registry • Hooks • Messages     │
        └──────┬──────┬──────┬──────┬──────┬─────┘
               ▼      ▼      ▼      ▼      ▼      ▼
           ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐ ┌────┐
           │DL  │ │Tag │ │Vis │ │Conv│ │File│ │Sys │
           │    │ │    │ │    │ │    │ │    │ │    │
           └────┘ └────┘ └────┘ └────┘ └────┘ └────┘
    """
    
    def __init__(self):
        log.section("SWISS KNIFE v2.0")
        
        # Initialize core systems
        self.memory = MemorySystem()
        self.brain = BrainSystem(memory=self.memory)
        self.kernel = MicroKernel()
        self.planner = PipelinePlanner(kernel=self.kernel)
        self.executor = PipelineExecutor(kernel=self.kernel)
        self.vision = VisionSystem()
        
        # Register core services
        self.kernel.register_service("memory", self.memory)
        self.kernel.register_service("brain", self.brain)
        self.kernel.register_service("vision", self.vision)
        self.kernel.register_service("planner", self.planner)
        
        # Discover and register tools
        self._load_tools()
        
        # Tell brain about available tools
        self.brain.set_available_tools(list(self.kernel._tools.keys()))
        
        # Start kernel
        self.kernel.start()
        
        log.success("Swiss Knife ready!")
    
    def _load_tools(self):
        """Load and register all tools."""
        tools_dir = Path(__file__).parent / "tools"
        
        if tools_dir.exists():
            count = self.kernel.discover_tools(str(tools_dir))
            log.info(f"Loaded {count} tools")
        
        # Also try direct imports
        try:
            from tools.downloader import UniversalDownloader
            if not self.kernel.has_tool("universal_downloader"):
                self.kernel.register_tool(UniversalDownloader)
        except Exception as e:
            log.debug(f"Direct downloader import: {e}")
        
        try:
            from tools.audio_tagger import AudioTagger
            if not self.kernel.has_tool("audio_tagger"):
                self.kernel.register_tool(AudioTagger)
        except Exception as e:
            log.debug(f"Direct audio_tagger import: {e}")
        
        try:
            from tools.vision_tool import VisionTool
            if not self.kernel.has_tool("vision"):
                self.kernel.register_tool(VisionTool)
        except Exception as e:
            log.debug(f"Direct vision import: {e}")
        
        try:
            from tools.file_manager import FileManager
            if not self.kernel.has_tool("file_manager"):
                self.kernel.register_tool(FileManager)
        except Exception as e:
            log.debug(f"Direct file_manager import: {e}")
        
        try:
            from tools.converter import Converter
            if not self.kernel.has_tool("converter"):
                self.kernel.register_tool(Converter)
        except Exception as e:
            log.debug(f"Direct converter import: {e}")
        
        try:
            from tools.system_tool import SystemTool
            if not self.kernel.has_tool("system"):
                self.kernel.register_tool(SystemTool)
        except Exception as e:
            log.debug(f"Direct system import: {e}")
        
        try:
            from tools.web_scraper import WebScraper
            if not self.kernel.has_tool("web_scraper"):
                self.kernel.register_tool(WebScraper)
        except Exception as e:
            log.debug(f"Direct web_scraper import: {e}")
        
        try:
            from tools.organizer import Organizer
            if not self.kernel.has_tool("organizer"):
                self.kernel.register_tool(Organizer)
        except Exception as e:
            log.debug(f"Direct organizer import: {e}")
    
    # ─── Commands ───────────────────────────────────────────────────────
    
    def cmd_download(self, url: str, format: str = "best", 
                     audio_only: bool = False, output: str = None,
                     **kwargs):
        """Download from URL."""
        log.section("Download")
        
        if not self.kernel.has_tool("universal_downloader"):
            log.error("Downloader tool not available")
            return
        
        tool = self.kernel.get_tool("universal_downloader")
        
        if audio_only:
            result = tool.download_audio(url, format=format, output_dir=output)
        else:
            result = tool.download(url, format=format, output_dir=output)
        
        if result.success:
            log.success(f"Downloaded: {result.title}")
            for f in result.files:
                log.info(f"  📁 {f}")
        else:
            log.error(f"Failed: {result.error}")
    
    def cmd_tag(self, directory: str = ".", auto_rename: bool = True,
                **kwargs):
        """Auto-tag audio files."""
        log.section("Audio Tagger")
        
        if not self.kernel.has_tool("audio_tagger"):
            log.error("Audio tagger not available")
            return
        
        tool = self.kernel.get_tool("audio_tagger")
        results = tool.auto_tag(directory=directory, auto_rename=auto_rename)
        
        # Print report
        report = tool.generate_report(results)
        print(report)
    
    def cmd_vision(self, image: str, action: str = "describe", **kwargs):
        """Analyze image."""
        log.section("Vision")
        
        if not self.kernel.has_tool("vision"):
            log.error("Vision tool not available")
            return
        
        tool = self.kernel.get_tool("vision")
        
        if action == "describe":
            result = tool.describe_image(image)
            print(f"\n🖼️  Description:\n{result}")
        elif action == "read_text":
            result = tool.read_text(image)
            print(f"\n📝 Text:\n{result}")
        elif action == "analyze":
            result = tool.analyze_image(image)
            print(result.summarize())
        else:
            result = tool.describe_image(image)
            print(result)
    
    def cmd_convert(self, input_file: str, output: str = None, 
                    format: str = None, preset: str = None, **kwargs):
        """Convert media file."""
        log.section("Converter")
        
        if not self.kernel.has_tool("converter"):
            log.error("Converter not available")
            return
        
        tool = self.kernel.get_tool("converter")
        result = tool.convert(input_file, output=output, format=format, preset=preset)
        
        if result and os.path.exists(result):
            log.success(f"Converted: {result}")
        else:
            log.error("Conversion failed")
    
    def cmd_organize(self, directory: str = ".", mode: str = "smart",
                     **kwargs):
        """Organize files."""
        log.section("Organizer")
        
        if not self.kernel.has_tool("organizer"):
            log.error("Organizer not available")
            return
        
        tool = self.kernel.get_tool("organizer")
        
        if mode == "smart":
            result = tool.smart_sort(directory)
        elif mode == "media":
            result = tool.organize_media(directory)
        elif mode == "tv":
            result = tool.organize_tv_shows(directory)
        elif mode == "movies":
            result = tool.organize_movies(directory)
        elif mode == "music":
            result = tool.organize_music(directory)
        elif mode == "photos":
            result = tool.organize_photos(directory)
        else:
            result = tool.organize_media(directory)
        
        print(json.dumps(result, indent=2, default=str))
    
    def cmd_pipeline(self, description: str, **kwargs):
        """Create and execute a pipeline."""
        log.section("Pipeline")
        
        # Use brain to understand the request
        thought = self.brain.think(description)
        print(f"\n🧠 Brain Analysis:\n{thought.conclusion}")
        
        # Auto-plan
        pipeline = self.planner.auto_plan(description)
        
        print(f"\n📋 Pipeline Plan:")
        print(pipeline.visualize())
        
        # Execute
        result = self.executor.execute(pipeline, kernel=self.kernel)
        
        if result.status.value == "completed":
            log.success("Pipeline completed!")
        else:
            log.error("Pipeline had issues")
    
    def cmd_brain(self, query: str, **kwargs):
        """Ask the brain."""
        log.section("Brain")
        
        # Quick response
        quick = self.brain.quick_think(query)
        print(f"\n💭 Quick: {quick}")
        
        # Deep reasoning
        chain = self.brain.think(query, depth="deep")
        print(f"\n🧠 Deep Analysis:\n{chain.summarize()}")
    
    def cmd_status(self, **kwargs):
        """Show system status."""
        log.section("System Status")
        
        # Kernel status
        status = self.kernel.status()
        print("\n🔧 Kernel:")
        print(f"  Running: {status['running']}")
        print(f"  Tools: {status['tools_registered']}")
        print(f"  Categories: {', '.join(status['categories'])}")
        print(f"  Registered: {', '.join(status['tools'])}")
        
        # Brain status
        brain_status = self.brain.status()
        print("\n🧠 Brain:")
        print(f"  Modules: {brain_status['cognitive_modules']}")
        print(f"  Thoughts: {brain_status['total_thoughts']}")
        print(f"  Reasoning chains: {brain_status['reasoning_chains']}")
        
        # Memory status
        mem_stats = self.memory.get_stats()
        print("\n💾 Memory:")
        print(f"  Total stored: {mem_stats['total_stored']}")
        print(f"  Long-term: {mem_stats['long_term']}")
        print(f"  Episodic: {mem_stats['episodic']}")
        print(f"  Working: {mem_stats['working_memory']}")
        
        # Tool health
        print("\n🔨 Tool Health:")
        for name, tool in self.kernel._tools.items():
            health = tool.health_check()
            icon = "✅" if health["status"] == "healthy" else "⚠️"
            print(f"  {icon} {name}: {health['status']}")
    
    def cmd_interactive(self, **kwargs):
        """Interactive mode."""
        log.section("Interactive Mode")
        print("Type 'help' for commands, 'quit' to exit.\n")
        
        while True:
            try:
                user_input = input("swiss> ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ("quit", "exit", "q"):
                    break
                
                if user_input.lower() == "help":
                    self._print_help()
                    continue
                
                if user_input.lower() == "status":
                    self.cmd_status()
                    continue
                
                if user_input.lower().startswith("download "):
                    url = user_input[9:].strip()
                    self.cmd_download(url)
                    continue
                
                if user_input.lower().startswith("tag "):
                    directory = user_input[4:].strip()
                    self.cmd_tag(directory)
                    continue
                
                # Default: use brain
                print(self.brain.quick_think(user_input))
                
            except KeyboardInterrupt:
                print("\nUse 'quit' to exit")
            except EOFError:
                break
        
        print("\nGoodbye! 👋")
    
    def _print_help(self):
        """Print interactive help."""
        print("""
Available commands:
  download <url>        Download from URL
  tag <directory>       Tag audio files
  vision <image>        Analyze image
  convert <file>        Convert media
  organize <dir>        Organize files
  pipeline <desc>       Create workflow
  brain <question>      Ask AI
  status                System status
  help                  This help
  quit                  Exit

Or just type anything to chat with the brain!
        """)
    
    def shutdown(self):
        """Cleanup and shutdown."""
        self.kernel.stop()
        log.section("Swiss Knife Shutdown")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Swiss Knife - Universal Multi-Tool Platform",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s download https://youtube.com/watch?v=... --format mp3
  %(prog)s tag ~/Music --auto-rename
  %(prog)s vision photo.jpg --action describe
  %(prog)s convert video.avi --format mp4
  %(prog)s organize ~/Downloads --mode smart
  %(prog)s pipeline "Download playlist and convert to mp3"
  %(prog)s brain "How do I batch convert videos?"
  %(prog)s status
  %(prog)s interactive
        """
    )
    
    parser.add_argument("command", choices=[
        "download", "tag", "vision", "convert", "organize",
        "pipeline", "brain", "status", "interactive"
    ], help="Command to execute")
    
    parser.add_argument("args", nargs="*", help="Command arguments")
    
    # Download options
    parser.add_argument("--format", "-f", default="best", 
                       help="Output format (mp4, mp3, etc.)")
    parser.add_argument("--audio-only", "-a", action="store_true",
                       help="Download audio only")
    parser.add_argument("--output", "-o", help="Output directory")
    
    # Tag options
    parser.add_argument("--auto-rename", action="store_true", default=True,
                       help="Auto-rename tagged files")
    
    # Vision options
    parser.add_argument("--action", default="describe",
                       choices=["describe", "read_text", "analyze", "detect_objects"],
                       help="Vision action")
    
    # Convert options
    parser.add_argument("--preset", help="Conversion preset")
    
    # Organize options
    parser.add_argument("--mode", default="smart",
                       choices=["smart", "media", "tv", "movies", "music", "photos"],
                       help="Organization mode")
    
    # General
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    parser.add_argument("--config", help="Config file path")
    
    args = parser.parse_args()
    
    # Set log level
    if args.verbose:
        log.logger.setLevel(__import__('logging').DEBUG)
    
    # Initialize Swiss Knife
    app = SwissKnife()
    
    try:
        # Dispatch command
        if args.command == "download":
            url = args.args[0] if args.args else ""
            app.cmd_download(url, format=args.format, audio_only=args.audio_only, 
                           output=args.output)
        
        elif args.command == "tag":
            directory = args.args[0] if args.args else "."
            app.cmd_tag(directory, auto_rename=args.auto_rename)
        
        elif args.command == "vision":
            image = args.args[0] if args.args else ""
            app.cmd_vision(image, action=args.action)
        
        elif args.command == "convert":
            input_file = args.args[0] if args.args else ""
            app.cmd_convert(input_file, format=args.format, preset=args.preset)
        
        elif args.command == "organize":
            directory = args.args[0] if args.args else "."
            app.cmd_organize(directory, mode=args.mode)
        
        elif args.command == "pipeline":
            description = " ".join(args.args) if args.args else ""
            app.cmd_pipeline(description)
        
        elif args.command == "brain":
            query = " ".join(args.args) if args.args else ""
            app.cmd_brain(query)
        
        elif args.command == "status":
            app.cmd_status()
        
        elif args.command == "interactive":
            app.cmd_interactive()
    
    except KeyboardInterrupt:
        log.info("\nInterrupted by user")
    except Exception as e:
        log.error(f"Error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
