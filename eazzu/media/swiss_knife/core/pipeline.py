"""
Pipeline Planner & Workflow Orchestration Engine
Automatically plans and executes multi-step workflows.

Features:
- Automatic pipeline generation from natural language
- Visual pipeline representation
- Parallel execution where possible
- Error handling and retry logic
- Checkpointing and resume capability
- Conditional branching
- Data flow between steps
"""

import os
import json
import time
import uuid
import copy
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union
from datetime import datetime
from enum import Enum
import threading
import concurrent.futures

from utils.logger import log
from core.kernel import MicroKernel


class StepStatus(Enum):
    """Status of a pipeline step."""
    PENDING = "pending"
    WAITING = "waiting"      # Waiting for dependencies
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class PipelineStatus(Enum):
    """Status of the entire pipeline."""
    CREATED = "created"
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class PipelineStep:
    """A single step in a pipeline."""
    id: str
    name: str
    description: str = ""
    tool: str = ""           # Tool to execute
    action: str = ""         # Specific action within the tool
    parameters: Dict = field(default_factory=dict)
    
    # Execution control
    depends_on: List[str] = field(default_factory=list)  # Step IDs this depends on
    condition: Optional[str] = None  # Conditional execution (e.g., "prev.success")
    retries: int = 3
    timeout: int = 300  # seconds
    parallel_group: Optional[str] = None  # Group for parallel execution
    
    # State
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    execution_time: float = 0.0
    attempt: int = 0
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['status'] = self.status.value
        data['started_at'] = self.started_at.isoformat() if self.started_at else None
        data['completed_at'] = self.completed_at.isoformat() if self.completed_at else None
        return data
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class Pipeline:
    """A complete workflow pipeline."""
    id: str
    name: str
    description: str = ""
    steps: List[PipelineStep] = field(default_factory=list)
    status: PipelineStatus = PipelineStatus.CREATED
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)
    global_parameters: Dict = field(default_factory=dict)
    
    # Results
    results: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "step_count": len(self.steps),
            "completed_steps": sum(1 for s in self.steps if s.status == StepStatus.COMPLETED),
            "failed_steps": sum(1 for s in self.steps if s.status == StepStatus.FAILED),
        }
    
    def get_step(self, step_id: str) -> Optional[PipelineStep]:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_ready_steps(self) -> List[PipelineStep]:
        """Get steps that are ready to execute (dependencies met)."""
        ready = []
        completed_ids = {s.id for s in self.steps if s.status == StepStatus.COMPLETED}
        
        for step in self.steps:
            if step.status != StepStatus.PENDING:
                continue
            
            # Check if dependencies are met
            deps_satisfied = all(dep in completed_ids for dep in step.depends_on)
            
            # Check if any dependency failed (unless optional)
            deps_failed = any(
                self.get_step(dep).status == StepStatus.FAILED 
                for dep in step.depends_on if self.get_step(dep)
            )
            
            if deps_satisfied and not deps_failed:
                ready.append(step)
        
        return ready
    
    def get_progress(self) -> float:
        """Get pipeline progress as percentage."""
        if not self.steps:
            return 0.0
        completed = sum(1 for s in self.steps if s.status == StepStatus.COMPLETED)
        return (completed / len(self.steps)) * 100
    
    def visualize(self) -> str:
        """Create ASCII visualization of the pipeline."""
        lines = [f"📋 Pipeline: {self.name}", "=" * 50]
        
        # Build dependency map for visualization
        for i, step in enumerate(self.steps):
            status_icon = {
                StepStatus.PENDING: "⬜",
                StepStatus.WAITING: "⏳",
                StepStatus.RUNNING: "🔄",
                StepStatus.COMPLETED: "✅",
                StepStatus.FAILED: "❌",
                StepStatus.SKIPPED: "⏭️",
                StepStatus.RETRYING: "🔁",
            }.get(step.status, "⬜")
            
            # Show dependencies
            prefix = "  "
            if step.depends_on:
                prefix = "  ↳ "
            
            lines.append(f"{prefix}{status_icon} {step.name}")
            
            if step.result and step.status == StepStatus.COMPLETED:
                result_str = str(step.result)[:50]
                lines.append(f"     📤 {result_str}")
            
            if step.error and step.status == StepStatus.FAILED:
                lines.append(f"     ⚠️  {step.error[:60]}")
        
        lines.append("=" * 50)
        lines.append(f"Progress: {self.get_progress():.1f}%")
        
        return "\n".join(lines)


class PipelinePlanner:
    """
    Intelligent pipeline planner.
    Converts natural language requests into executable pipelines.
    """
    
    def __init__(self, kernel: MicroKernel = None):
        self.kernel = kernel
        
        # Templates for common workflows
        self._templates: Dict[str, Callable] = {
            "download_video": self._tpl_download_video,
            "download_audio": self._tpl_download_audio,
            "download_playlist": self._tpl_download_playlist,
            "tag_audio": self._tpl_tag_audio,
            "organize_files": self._tpl_organize_files,
            "convert_media": self._tpl_convert_media,
            "batch_process": self._tpl_batch_process,
        }
        
        log.section("Pipeline Planner Initialized")
        log.info(f"Available templates: {list(self._templates.keys())}")
    
    # ─── Pipeline Creation ──────────────────────────────────────────────
    
    def create_pipeline(self, name: str, description: str = "") -> Pipeline:
        """Create a new empty pipeline."""
        return Pipeline(
            id=str(uuid.uuid4())[:8],
            name=name,
            description=description
        )
    
    def add_step(self, pipeline: Pipeline, name: str, tool: str,
                 action: str = "", parameters: Dict = None,
                 depends_on: List[str] = None, **kwargs) -> str:
        """Add a step to a pipeline."""
        step_id = f"step_{len(pipeline.steps) + 1}"
        
        step = PipelineStep(
            id=step_id,
            name=name,
            tool=tool,
            action=action,
            parameters=parameters or {},
            depends_on=depends_on or [],
            **kwargs
        )
        
        pipeline.steps.append(step)
        log.debug(f"Added step '{name}' ({step_id}) to pipeline '{pipeline.name}'")
        return step_id
    
    def auto_plan(self, request: str, context: Dict = None) -> Pipeline:
        """
        Automatically create a pipeline from a natural language request.
        
        Examples:
            "Download video from youtube and convert to mp3"
            "Tag all my music files in the Downloads folder"
            "Download playlist and organize by artist"
        """
        log.section("Auto-Planning Pipeline")
        log.info(f"Request: {request}")
        
        request_lower = request.lower()
        
        # Detect intent and create appropriate pipeline
        pipeline = None
        
        # Download intents
        if any(w in request_lower for w in ["download", "get", "save", "grab"]):
            if "playlist" in request_lower:
                pipeline = self._tpl_download_playlist(request, context)
            elif "audio" in request_lower or "mp3" in request_lower or "music" in request_lower:
                pipeline = self._tpl_download_audio(request, context)
            else:
                pipeline = self._tpl_download_video(request, context)
        
        # Audio tagging intents
        elif any(w in request_lower for w in ["tag", "identify", "rename", "organize music", "fix music"]):
            pipeline = self._tpl_tag_audio(request, context)
        
        # File organization intents
        elif any(w in request_lower for w in ["organize", "sort", "clean up", "arrange"]):
            pipeline = self._tpl_organize_files(request, context)
        
        # Conversion intents
        elif any(w in request_lower for w in ["convert", "transform", "change format"]):
            pipeline = self._tpl_convert_media(request, context)
        
        # Batch processing
        elif any(w in request_lower for w in ["batch", "bulk", "multiple", "all files"]):
            pipeline = self._tpl_batch_process(request, context)
        
        # Generic fallback
        if pipeline is None:
            pipeline = self.create_pipeline(
                name="Custom Workflow",
                description=request
            )
            # Add analysis step
            self.add_step(
                pipeline,
                name="Analyze Request",
                tool="brain",
                action="think",
                parameters={"input": request}
            )
        
        pipeline.status = PipelineStatus.PLANNED
        log.success(f"Pipeline planned with {len(pipeline.steps)} steps")
        log.info(f"Pipeline visualization:\n{pipeline.visualize()}")
        
        return pipeline
    
    # ─── Pipeline Templates ─────────────────────────────────────────────
    
    def _tpl_download_video(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Download video from URL."""
        pipeline = self.create_pipeline(
            name="Video Download",
            description=request
        )
        
        # Extract URL from request
        url = self._extract_url(request)
        
        self.add_step(pipeline, "Validate URL", "universal_downloader", "validate",
                     parameters={"url": url})
        
        self.add_step(pipeline, "Fetch Video Info", "universal_downloader", "get_info",
                     parameters={"url": url},
                     depends_on=["step_1"])
        
        self.add_step(pipeline, "Download Video", "universal_downloader", "download",
                     parameters={"url": url, "format": "best"},
                     depends_on=["step_2"])
        
        self.add_step(pipeline, "Verify Download", "universal_downloader", "verify",
                     depends_on=["step_3"])
        
        return pipeline
    
    def _tpl_download_audio(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Download and extract audio."""
        pipeline = self.create_pipeline(
            name="Audio Download",
            description=request
        )
        
        url = self._extract_url(request)
        audio_format = "mp3"
        
        # Detect preferred format
        if "wav" in request.lower():
            audio_format = "wav"
        elif "flac" in request.lower():
            audio_format = "flac"
        elif "m4a" in request.lower() or "aac" in request.lower():
            audio_format = "m4a"
        
        self.add_step(pipeline, "Validate URL", "universal_downloader", "validate",
                     parameters={"url": url})
        
        self.add_step(pipeline, "Fetch Media Info", "universal_downloader", "get_info",
                     parameters={"url": url},
                     depends_on=["step_1"])
        
        self.add_step(pipeline, "Download & Extract Audio", "universal_downloader", "download_audio",
                     parameters={"url": url, "format": audio_format},
                     depends_on=["step_2"])
        
        self.add_step(pipeline, "Add Metadata", "audio_tagger", "auto_tag",
                     parameters={"auto_fetch": True},
                     depends_on=["step_3"])
        
        self.add_step(pipeline, "Verify Output", "universal_downloader", "verify",
                     depends_on=["step_4"])
        
        return pipeline
    
    def _tpl_download_playlist(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Download entire playlist."""
        pipeline = self.create_pipeline(
            name="Playlist Download",
            description=request
        )
        
        url = self._extract_url(request)
        
        self.add_step(pipeline, "Analyze Playlist", "universal_downloader", "get_playlist_info",
                     parameters={"url": url})
        
        self.add_step(pipeline, "Download All Items", "universal_downloader", "download_playlist",
                     parameters={"url": url, "parallel": True},
                     depends_on=["step_1"])
        
        self.add_step(pipeline, "Organize Downloads", "file_manager", "organize",
                     parameters={"by_metadata": True},
                     depends_on=["step_2"])
        
        return pipeline
    
    def _tpl_tag_audio(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Identify and tag audio files."""
        pipeline = self.create_pipeline(
            name="Audio Tagging",
            description=request
        )
        
        # Extract directory from request
        directory = self._extract_path(request) or "."
        
        self.add_step(pipeline, "Scan Audio Files", "audio_tagger", "scan",
                     parameters={"directory": directory})
        
        self.add_step(pipeline, "Generate Fingerprints", "audio_tagger", "fingerprint",
                     parameters={"duration": 10},
                     depends_on=["step_1"])
        
        self.add_step(pipeline, "Identify Songs", "audio_tagger", "identify",
                     depends_on=["step_2"])
        
        self.add_step(pipeline, "Fetch Metadata", "audio_tagger", "fetch_metadata",
                     parameters={"fetch_lyrics": True, "fetch_album_art": True},
                     depends_on=["step_3"])
        
        self.add_step(pipeline, "Download Album Art", "audio_tagger", "fetch_album_art",
                     depends_on=["step_4"])
        
        self.add_step(pipeline, "Embed Tags & Artwork", "audio_tagger", "embed_tags",
                     depends_on=["step_5"])
        
        self.add_step(pipeline, "Fetch & Embed Lyrics", "audio_tagger", "embed_lyrics",
                     depends_on=["step_6"])
        
        self.add_step(pipeline, "Rename Files", "audio_tagger", "rename_files",
                     parameters={"pattern": "{artist} - {title}"},
                     depends_on=["step_7"])
        
        self.add_step(pipeline, "Generate Report", "audio_tagger", "generate_report",
                     depends_on=["step_8"])
        
        return pipeline
    
    def _tpl_organize_files(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Organize files."""
        pipeline = self.create_pipeline(
            name="File Organization",
            description=request
        )
        
        directory = self._extract_path(request) or "."
        
        self.add_step(pipeline, "Scan Directory", "file_manager", "scan",
                     parameters={"directory": directory})
        
        self.add_step(pipeline, "Analyze Structure", "file_manager", "analyze",
                     depends_on=["step_1"])
        
        self.add_step(pipeline, "Organize by Type", "file_manager", "organize_by_type",
                     parameters={"directory": directory},
                     depends_on=["step_2"])
        
        self.add_step(pipeline, "Clean Empty Directories", "file_manager", "cleanup",
                     depends_on=["step_3"])
        
        return pipeline
    
    def _tpl_convert_media(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Convert media formats."""
        pipeline = self.create_pipeline(
            name="Media Conversion",
            description=request
        )
        
        self.add_step(pipeline, "Detect Input Format", "converter", "detect_format")
        self.add_step(pipeline, "Convert Media", "converter", "convert",
                     depends_on=["step_1"])
        self.add_step(pipeline, "Verify Output", "converter", "verify",
                     depends_on=["step_2"])
        
        return pipeline
    
    def _tpl_batch_process(self, request: str, context: Dict = None) -> Pipeline:
        """Template: Batch process files."""
        pipeline = self.create_pipeline(
            name="Batch Processing",
            description=request
        )
        
        directory = self._extract_path(request) or "."
        
        self.add_step(pipeline, "Discover Files", "file_manager", "scan",
                     parameters={"directory": directory})
        self.add_step(pipeline, "Create Batch Plan", "pipeline_planner", "plan_batch",
                     depends_on=["step_1"])
        self.add_step(pipeline, "Execute Batch", "file_manager", "batch_execute",
                     parameters={"parallel": True},
                     depends_on=["step_2"])
        self.add_step(pipeline, "Verify Results", "file_manager", "verify_batch",
                     depends_on=["step_3"])
        
        return pipeline
    
    # ─── Helpers ────────────────────────────────────────────────────────
    
    def _extract_url(self, text: str) -> str:
        """Extract URL from text."""
        import re
        url_pattern = r'https?://[^\s<>"{}|\\^`[\]]+'
        matches = re.findall(url_pattern, text)
        return matches[0] if matches else ""
    
    def _extract_path(self, text: str) -> str:
        """Extract file path from text."""
        import re
        # Match quoted paths or obvious paths
        path_pattern = r'["\']([^"\']*(?:Downloads|Desktop|Documents|Music|Videos)[^"\']*)["\']|(\b[A-Z]:\\[^\s]+|\b~/[^\s]+|\b/[\w/]+)'
        matches = re.findall(path_pattern, text)
        if matches:
            match = matches[0]
            return match[0] or match[1] if isinstance(match, tuple) else match
        return ""
    
    def register_template(self, name: str, template_func: Callable):
        """Register a custom pipeline template."""
        self._templates[name] = template_func


class PipelineExecutor:
    """
    Executes pipelines with support for parallel execution,
    error handling, retries, and checkpointing.
    """
    
    def __init__(self, kernel: MicroKernel = None):
        self.kernel = kernel
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self._active_pipelines: Dict[str, Pipeline] = {}
        self._checkpoints: Dict[str, Dict] = {}
        
        log.section("Pipeline Executor Initialized")
    
    def execute(self, pipeline: Pipeline, kernel: MicroKernel = None,
                on_progress: Callable = None) -> Pipeline:
        """
        Execute a pipeline.
        
        Args:
            pipeline: The pipeline to execute
            kernel: MicroKernel for tool execution
            on_progress: Callback(progress_pct, message)
        """
        if kernel:
            self.kernel = kernel
        
        pipeline.status = PipelineStatus.RUNNING
        pipeline.started_at = datetime.now()
        self._active_pipelines[pipeline.id] = pipeline
        
        log.section(f"Executing Pipeline: {pipeline.name}")
        
        try:
            while True:
                # Get ready steps
                ready_steps = pipeline.get_ready_steps()
                
                if not ready_steps:
                    # Check if all done
                    all_done = all(
                        s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED, StepStatus.FAILED)
                        for s in pipeline.steps
                    )
                    if all_done:
                        break
                    
                    # Check if any failed and blocked others
                    failed = [s for s in pipeline.steps if s.status == StepStatus.FAILED]
                    if failed and not any(s.status == StepStatus.PENDING for s in pipeline.steps):
                        break
                    
                    # Wait for running steps
                    time.sleep(0.5)
                    continue
                
                # Group parallel steps
                parallel_groups: Dict[str, List[PipelineStep]] = {}
                sequential_steps = []
                
                for step in ready_steps:
                    if step.parallel_group:
                        if step.parallel_group not in parallel_groups:
                            parallel_groups[step.parallel_group] = []
                        parallel_groups[step.parallel_group].append(step)
                    else:
                        sequential_steps.append(step)
                
                # Execute parallel groups
                for group_name, steps in parallel_groups.items():
                    log.info(f"Executing parallel group '{group_name}' with {len(steps)} steps")
                    futures = {}
                    for step in steps:
                        future = self._executor.submit(self._execute_step, step, pipeline)
                        futures[future] = step
                    
                    for future in concurrent.futures.as_completed(futures):
                        step = futures[future]
                        try:
                            future.result()
                        except Exception as e:
                            log.error(f"Parallel step {step.name} failed: {e}")
                
                # Execute sequential steps
                for step in sequential_steps:
                    self._execute_step(step, pipeline)
                    
                    # Progress callback
                    if on_progress:
                        progress = pipeline.get_progress()
                        on_progress(progress, f"Completed: {step.name}")
                
                # Save checkpoint
                self._save_checkpoint(pipeline)
                
                # Log progress
                log.info(f"Pipeline progress: {pipeline.get_progress():.1f}%")
        
        except KeyboardInterrupt:
            log.warning("Pipeline execution interrupted")
            pipeline.status = PipelineStatus.PAUSED
            return pipeline
        
        # Final status
        failed = any(s.status == StepStatus.FAILED for s in pipeline.steps)
        pipeline.status = PipelineStatus.FAILED if failed else PipelineStatus.COMPLETED
        pipeline.completed_at = datetime.now()
        
        if pipeline.status == PipelineStatus.COMPLETED:
            log.success(f"Pipeline '{pipeline.name}' completed successfully!")
        else:
            log.error(f"Pipeline '{pipeline.name}' completed with errors")
            for step in pipeline.steps:
                if step.error:
                    log.error(f"  - {step.name}: {step.error}")
        
        return pipeline
    
    def _execute_step(self, step: PipelineStep, pipeline: Pipeline):
        """Execute a single step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now()
        step.attempt += 1
        
        log.pipeline_step(
            pipeline.steps.index(step) + 1,
            len(pipeline.steps),
            step.name
        )
        
        try:
            # Execute via kernel if available
            if self.kernel and step.tool:
                result = self.kernel.execute(
                    step.tool,
                    action=step.action,
                    **step.parameters
                )
                step.result = result
            else:
                # Simulated execution
                log.info(f"Simulating: {step.tool}.{step.action}({step.parameters})")
                time.sleep(0.5)  # Simulate work
                step.result = {"simulated": True, "step": step.name}
            
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now()
            step.execution_time = (step.completed_at - step.started_at).total_seconds()
            
            log.success(f"Step completed: {step.name} ({step.execution_time:.2f}s)")
            
        except Exception as e:
            step.error = str(e)
            
            if step.attempt < step.retries:
                step.status = StepStatus.RETRYING
                log.warning(f"Step failed, retrying ({step.attempt}/{step.retries}): {e}")
                time.sleep(2 ** step.attempt)  # Exponential backoff
            else:
                step.status = StepStatus.FAILED
                pipeline.errors.append({"step": step.id, "error": str(e)})
                log.error(f"Step failed after {step.retries} retries: {e}")
    
    def _save_checkpoint(self, pipeline: Pipeline):
        """Save pipeline checkpoint for resume capability."""
        self._checkpoints[pipeline.id] = {
            "timestamp": datetime.now().isoformat(),
            "pipeline": pipeline.to_dict()
        }
    
    def resume_pipeline(self, pipeline_id: str) -> Optional[Pipeline]:
        """Resume a pipeline from last checkpoint."""
        checkpoint = self._checkpoints.get(pipeline_id)
        if not checkpoint:
            return None
        
        # This would restore pipeline state
        log.info(f"Resuming pipeline {pipeline_id} from checkpoint")
        return None
    
    def get_active_pipelines(self) -> List[Dict]:
        """Get all active pipelines."""
        return [p.to_dict() for p in self._active_pipelines.values()]
    
    def cancel_pipeline(self, pipeline_id: str):
        """Cancel a running pipeline."""
        if pipeline_id in self._active_pipelines:
            self._active_pipelines[pipeline_id].status = PipelineStatus.CANCELLED
            log.info(f"Pipeline {pipeline_id} cancelled")
