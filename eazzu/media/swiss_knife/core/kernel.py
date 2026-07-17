"""
Micro-Kernel Plugin System
The heart of Swiss Knife - manages tool registration, discovery, and execution.
Uses a micro-kernel pattern where core services are minimal and tools are plugins.
"""

import os
import sys
import inspect
import importlib
import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Type, Set
from pathlib import Path
from datetime import datetime
import threading
import concurrent.futures

from utils.logger import log


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    category: str = "general"
    tags: List[str] = field(default_factory=list)
    requires: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    config_schema: Dict = field(default_factory=dict)
    permissions: List[str] = field(default_factory=list)
    is_async: bool = False
    priority: int = 50  # Lower = higher priority
    enabled: bool = True


class ToolBase(ABC):
    """Abstract base class for all tools."""
    
    # Override these in subclasses
    metadata: ToolMetadata = ToolMetadata(name="base")
    
    def __init__(self, kernel: "MicroKernel" = None):
        self.kernel = kernel
        self._state: Dict[str, Any] = {}
        self._initialized = False
        log.debug(f"Tool '{self.metadata.name}' instance created")
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method - must be implemented by all tools."""
        pass
    
    def initialize(self) -> bool:
        """Initialize the tool - called before first use. Override if needed."""
        self._initialized = True
        return True
    
    def shutdown(self):
        """Cleanup when tool is unloaded. Override if needed."""
        self._initialized = False
    
    def get_state(self, key: str, default=None):
        """Get persistent state for this tool."""
        return self._state.get(key, default)
    
    def set_state(self, key: str, value: Any):
        """Set persistent state for this tool."""
        self._state[key] = value
    
    def health_check(self) -> Dict[str, Any]:
        """Return health status of the tool."""
        return {
            "status": "healthy" if self._initialized else "not_initialized",
            "name": self.metadata.name,
            "version": self.metadata.version
        }
    
    def __repr__(self):
        return f"<{self.metadata.name} v{self.metadata.version}>"


class ToolHook:
    """Represents a hook point that tools can attach to."""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self._handlers: List[Callable] = []
        self._priority_map: Dict[Callable, int] = {}
    
    def register(self, handler: Callable, priority: int = 50):
        """Register a handler with priority (lower = earlier execution)."""
        if handler not in self._handlers:
            self._handlers.append(handler)
            self._priority_map[handler] = priority
            # Sort by priority
            self._handlers.sort(key=lambda h: self._priority_map.get(h, 50))
            log.debug(f"Hook '{self.name}': registered handler {handler.__name__}")
    
    def unregister(self, handler: Callable):
        """Remove a handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
            del self._priority_map[handler]
    
    def fire(self, *args, **kwargs) -> List[Any]:
        """Execute all handlers and return results."""
        results = []
        for handler in self._handlers:
            try:
                result = handler(*args, **kwargs)
                results.append(result)
            except Exception as e:
                log.error(f"Hook '{self.name}' handler failed: {e}")
        return results
    
    @property
    def handlers(self) -> List[Callable]:
        return self._handlers.copy()


class MicroKernel:
    """
    Micro-Kernel: The core of Swiss Knife.
    
    Principles:
    - Minimal core, maximum extensibility
    - Tools are self-contained plugins
    - Message passing between tools
    - Hook system for extensibility
    - Thread-safe operations
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Tool registry
        self._tools: Dict[str, ToolBase] = {}
        self._tool_classes: Dict[str, Type[ToolBase]] = {}
        self._metadata: Dict[str, ToolMetadata] = {}
        
        # Hook system
        self._hooks: Dict[str, ToolHook] = {}
        
        # Message bus for inter-tool communication
        self._message_queue: List[Dict] = []
        self._message_handlers: Dict[str, List[Callable]] = {}
        
        # Event system
        self._events: Dict[str, List[Callable]] = {}
        
        # Thread pool for parallel execution
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=10)
        
        # Services registry (shared services tools can use)
        self._services: Dict[str, Any] = {}
        
        self._initialized = True
        self._running = False
        
        log.section("Micro-Kernel Initialized")
        log.info("Core system ready - awaiting tool registration")
    
    # ─── Tool Registration ──────────────────────────────────────────────
    
    def register_tool(self, tool_class: Type[ToolBase], auto_init: bool = True) -> bool:
        """Register a tool class with the kernel."""
        try:
            meta = tool_class.metadata
            name = meta.name
            
            if name in self._tool_classes:
                log.warning(f"Tool '{name}' already registered, overwriting")
            
            self._tool_classes[name] = tool_class
            self._metadata[name] = meta
            
            # Create instance
            instance = tool_class(kernel=self)
            self._tools[name] = instance
            
            if auto_init:
                instance.initialize()
            
            # Fire registration hook
            self.fire_hook("tool_registered", name=name, metadata=meta)
            
            log.success(f"Tool registered: {name} v{meta.version}")
            return True
            
        except Exception as e:
            log.error(f"Failed to register tool: {e}")
            return False
    
    def unregister_tool(self, name: str) -> bool:
        """Unregister and shutdown a tool."""
        if name not in self._tools:
            return False
        
        self._tools[name].shutdown()
        del self._tools[name]
        del self._tool_classes[name]
        del self._metadata[name]
        
        self.fire_hook("tool_unregistered", name=name)
        log.info(f"Tool unregistered: {name}")
        return True
    
    def get_tool(self, name: str) -> Optional[ToolBase]:
        """Get a tool instance by name."""
        return self._tools.get(name)
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered."""
        return name in self._tools
    
    def list_tools(self, category: Optional[str] = None, 
                   tags: Optional[List[str]] = None) -> List[Dict]:
        """List registered tools with optional filtering."""
        results = []
        for name, meta in self._metadata.items():
            if category and meta.category != category:
                continue
            if tags and not any(t in meta.tags for t in tags):
                continue
            results.append({
                "name": name,
                "metadata": meta,
                "healthy": self._tools[name].health_check()
            })
        return sorted(results, key=lambda x: x["metadata"].priority)
    
    def get_tool_categories(self) -> Set[str]:
        """Get all unique tool categories."""
        return set(m.category for m in self._metadata.values())
    
    # ─── Tool Discovery ─────────────────────────────────────────────────
    
    def discover_tools(self, directory: str = "tools") -> int:
        """Auto-discover and register tools from a directory."""
        count = 0
        tools_path = Path(directory)
        
        if not tools_path.exists():
            log.warning(f"Tools directory not found: {directory}")
            return 0
        
        # Add to path if needed
        abs_path = str(tools_path.absolute())
        if abs_path not in sys.path:
            sys.path.insert(0, abs_path)
        
        for file_path in tools_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            try:
                module_name = file_path.stem
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find ToolBase subclasses
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, ToolBase) and 
                        obj is not ToolBase and
                        hasattr(obj, 'metadata')):
                        
                        if self.register_tool(obj):
                            count += 1
                            
            except Exception as e:
                log.error(f"Failed to load tool from {file_path}: {e}")
        
        log.success(f"Discovered {count} tools from {directory}")
        return count
    
    def discover_from_module(self, module) -> int:
        """Discover tools from an already loaded module."""
        count = 0
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, ToolBase) and 
                obj is not ToolBase and
                hasattr(obj, 'metadata')):
                
                if self.register_tool(obj):
                    count += 1
        return count
    
    # ─── Execution ──────────────────────────────────────────────────────
    
    def execute(self, tool_name: str, *args, **kwargs) -> Any:
        """Execute a tool by name."""
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")
        
        if not tool._initialized:
            tool.initialize()
        
        log.tool_start(tool_name)
        start_time = datetime.now()
        
        try:
            # Fire pre-execution hook
            self.fire_hook("pre_execute", tool_name=tool_name, args=args, kwargs=kwargs)
            
            # Execute
            result = tool.execute(*args, **kwargs)
            
            # Fire post-execution hook
            self.fire_hook("post_execute", tool_name=tool_name, result=result)
            
            elapsed = (datetime.now() - start_time).total_seconds()
            log.tool_end(tool_name, "success")
            log.info(f"Execution time: {elapsed:.2f}s")
            
            return result
            
        except Exception as e:
            log.tool_end(tool_name, "failed")
            log.error(f"Tool execution failed: {e}")
            self.fire_hook("execution_error", tool_name=tool_name, error=e)
            raise
    
    def execute_async(self, tool_name: str, *args, **kwargs) -> concurrent.futures.Future:
        """Execute a tool asynchronously."""
        return self._executor.submit(self.execute, tool_name, *args, **kwargs)
    
    def execute_parallel(self, tasks: List[Dict]) -> List[Any]:
        """
        Execute multiple tools in parallel.
        tasks: [{"tool": "name", "args": [], "kwargs": {}}]
        """
        futures = []
        for task in tasks:
            future = self.execute_async(
                task["tool"],
                *task.get("args", []),
                **task.get("kwargs", {})
            )
            futures.append(future)
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                results.append(future.result())
            except Exception as e:
                results.append({"error": str(e)})
        
        return results
    
    # ─── Hook System ────────────────────────────────────────────────────
    
    def register_hook(self, name: str, description: str = "") -> ToolHook:
        """Create or get a hook point."""
        if name not in self._hooks:
            self._hooks[name] = ToolHook(name, description)
            log.debug(f"Hook registered: {name}")
        return self._hooks[name]
    
    def add_hook_handler(self, hook_name: str, handler: Callable, priority: int = 50):
        """Add a handler to a hook."""
        hook = self.register_hook(hook_name)
        hook.register(handler, priority)
    
    def fire_hook(self, hook_name: str, **kwargs) -> List[Any]:
        """Fire a hook and return all handler results."""
        if hook_name not in self._hooks:
            return []
        return self._hooks[hook_name].fire(**kwargs)
    
    # ─── Message Bus ────────────────────────────────────────────────────
    
    def publish(self, topic: str, message: Dict):
        """Publish a message to a topic."""
        msg = {
            "topic": topic,
            "data": message,
            "timestamp": datetime.now().isoformat()
        }
        self._message_queue.append(msg)
        
        # Notify subscribers
        if topic in self._message_handlers:
            for handler in self._message_handlers[topic]:
                try:
                    handler(message)
                except Exception as e:
                    log.error(f"Message handler error: {e}")
        
        self.fire_hook("message_published", topic=topic, message=msg)
    
    def subscribe(self, topic: str, handler: Callable):
        """Subscribe to a topic."""
        if topic not in self._message_handlers:
            self._message_handlers[topic] = []
        self._message_handlers[topic].append(handler)
        log.debug(f"Subscribed to topic: {topic}")
    
    # ─── Services ───────────────────────────────────────────────────────
    
    def register_service(self, name: str, service: Any):
        """Register a shared service for tools to use."""
        self._services[name] = service
        log.debug(f"Service registered: {name}")
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a shared service."""
        return self._services.get(name)
    
    # ─── Events ─────────────────────────────────────────────────────────
    
    def on(self, event: str, handler: Callable):
        """Register an event handler."""
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(handler)
    
    def emit(self, event: str, **data):
        """Emit an event."""
        if event in self._events:
            for handler in self._events[event]:
                try:
                    handler(**data)
                except Exception as e:
                    log.error(f"Event handler error: {e}")
    
    # ─── Lifecycle ──────────────────────────────────────────────────────
    
    def start(self):
        """Start the kernel."""
        self._running = True
        self.fire_hook("kernel_start")
        log.section("Swiss Knife Engine Started")
    
    def stop(self):
        """Stop the kernel and cleanup."""
        self._running = False
        
        # Shutdown all tools
        for name, tool in self._tools.items():
            try:
                tool.shutdown()
            except Exception as e:
                log.error(f"Error shutting down {name}: {e}")
        
        self._executor.shutdown(wait=True)
        self.fire_hook("kernel_stop")
        log.section("Swiss Knife Engine Stopped")
    
    def status(self) -> Dict:
        """Get kernel status report."""
        return {
            "running": self._running,
            "tools_registered": len(self._tools),
            "tools": list(self._tools.keys()),
            "categories": list(self.get_tool_categories()),
            "hooks": list(self._hooks.keys()),
            "services": list(self._services.keys()),
            "health": {name: tool.health_check() for name, tool in self._tools.items()}
        }
    
    def __repr__(self):
        return f"<MicroKernel tools={len(self._tools)} hooks={len(self._hooks)}>"
