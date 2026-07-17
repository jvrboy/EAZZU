"""
Advanced Memory System for Swiss Knife Brain
Simulates human memory with multiple memory types:
- Sensory Memory: Very short-term, raw input buffer
- Working Memory: Short-term, current context/conversation
- Short-Term Memory: Recent events and interactions  
- Long-Term Memory: Important knowledge and facts (persistent)
- Episodic Memory: Specific experiences and events
- Semantic Memory: Concepts, facts, relationships
- Procedural Memory: How to do things (learned skills/workflows)
"""

import os
import json
import pickle
import hashlib
import numpy as np
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Tuple, Set
from datetime import datetime, timedelta
from pathlib import Path
import threading
import time

from utils.logger import log


@dataclass
class MemoryEntry:
    """A single memory entry."""
    id: str
    content: Any
    memory_type: str  # working, short_term, long_term, episodic, semantic, procedural
    importance: float = 0.5  # 0.0 to 1.0
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    source: str = ""  # Where this memory came from
    emotions: Dict[str, float] = field(default_factory=dict)  # emotional valence
    associations: List[str] = field(default_factory=list)  # IDs of related memories
    embedding: Optional[List[float]] = None  # Vector embedding for similarity search
    
    def touch(self):
        """Update access metadata."""
        self.accessed_at = datetime.now()
        self.access_count += 1
    
    @property
    def age_hours(self) -> float:
        """How old is this memory in hours."""
        return (datetime.now() - self.created_at).total_seconds() / 3600
    
    @property
    def recency_score(self) -> float:
        """Score based on how recently accessed (0-1)."""
        hours_since_access = (datetime.now() - self.accessed_at).total_seconds() / 3600
        return max(0, 1 - (hours_since_access / 168))  # Decay over 1 week
    
    @property
    def relevance_score(self) -> float:
        """Combined relevance score."""
        return (self.importance * 0.4 + 
                self.recency_score * 0.3 + 
                min(1, self.access_count / 10) * 0.3)
    
    def to_dict(self) -> Dict:
        data = asdict(self)
        data['created_at'] = self.created_at.isoformat()
        data['accessed_at'] = self.accessed_at.isoformat()
        return data


class MemoryStore(ABC):
    """Abstract base for memory storage backends."""
    
    @abstractmethod
    def store(self, entry: MemoryEntry) -> bool:
        pass
    
    @abstractmethod
    def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        pass
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        pass
    
    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        pass
    
    @abstractmethod
    def list_all(self) -> List[MemoryEntry]:
        pass
    
    @abstractmethod
    def clear(self):
        pass


class InMemoryStore(MemoryStore):
    """Fast in-memory storage with optional persistence."""
    
    def __init__(self, persist_path: Optional[str] = None):
        self._memories: Dict[str, MemoryEntry] = {}
        self._persist_path = persist_path
        self._lock = threading.RLock()
        
        # Load existing if available
        if persist_path and os.path.exists(persist_path):
            self._load()
    
    def store(self, entry: MemoryEntry) -> bool:
        with self._lock:
            self._memories[entry.id] = entry
            self._maybe_persist()
            return True
    
    def retrieve(self, memory_id: str) -> Optional[MemoryEntry]:
        with self._lock:
            entry = self._memories.get(memory_id)
            if entry:
                entry.touch()
            return entry
    
    def search(self, query: str, limit: int = 10) -> List[MemoryEntry]:
        """Simple text search with relevance scoring."""
        with self._lock:
            query_lower = query.lower()
            results = []
            
            for entry in self._memories.values():
                score = 0
                content_str = str(entry.content).lower()
                
                # Exact match
                if query_lower in content_str:
                    score += 10
                
                # Tag match
                for tag in entry.tags:
                    if query_lower in tag.lower():
                        score += 5
                
                # Word match
                query_words = query_lower.split()
                content_words = content_str.split()
                matches = sum(1 for w in query_words if w in content_words)
                score += matches * 2
                
                if score > 0:
                    results.append((entry, score + entry.relevance_score))
            
            # Sort by combined score
            results.sort(key=lambda x: x[1], reverse=True)
            return [r[0] for r in results[:limit]]
    
    def delete(self, memory_id: str) -> bool:
        with self._lock:
            if memory_id in self._memories:
                del self._memories[memory_id]
                self._maybe_persist()
                return True
            return False
    
    def list_all(self) -> List[MemoryEntry]:
        with self._lock:
            return list(self._memories.values())
    
    def clear(self):
        with self._lock:
            self._memories.clear()
            self._maybe_persist()
    
    def get_by_type(self, memory_type: str) -> List[MemoryEntry]:
        with self._lock:
            return [m for m in self._memories.values() if m.memory_type == memory_type]
    
    def _maybe_persist(self):
        if self._persist_path:
            self._save()
    
    def _save(self):
        """Save to disk."""
        try:
            data = {k: v.to_dict() for k, v in self._memories.items()}
            os.makedirs(os.path.dirname(self._persist_path), exist_ok=True)
            with open(self._persist_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            log.error(f"Failed to persist memory: {e}")
    
    def _load(self):
        """Load from disk."""
        try:
            with open(self._persist_path, 'r') as f:
                data = json.load(f)
            # Basic restoration (datetime strings need parsing)
            log.info(f"Loaded {len(data)} memories from {self._persist_path}")
        except Exception as e:
            log.error(f"Failed to load memory: {e}")


class MemorySystem:
    """
    Multi-tier memory system simulating human memory.
    
    Architecture:
        Sensory → Working → Short-Term → Long-Term
                            ↓              ↑
                         Episodic ←──→ Semantic
                            ↓
                        Procedural
    """
    
    def __init__(self, storage_dir: str = "memory"):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        
        # Different memory stores for different types
        self._sensory: List[MemoryEntry] = []  # Ring buffer, very small
        self._working: Dict[str, MemoryEntry] = {}  # Current context
        self._short_term = InMemoryStore(str(self.storage_dir / "short_term.json"))
        self._long_term = InMemoryStore(str(self.storage_dir / "long_term.json"))
        self._episodic = InMemoryStore(str(self.storage_dir / "episodic.json"))
        self._semantic = InMemoryStore(str(self.storage_dir / "semantic.json"))
        self._procedural = InMemoryStore(str(self.storage_dir / "procedural.json"))
        
        # Configuration
        self.sensory_capacity = 10  # Keep last 10 sensory inputs
        self.working_capacity = 5   # Keep 5 items in working memory
        self.short_term_capacity = 100
        self.consolidation_threshold = 0.7  # Importance threshold to promote to long-term
        
        # Consolidation thread
        self._consolidation_thread = threading.Thread(target=self._consolidation_loop, daemon=True)
        self._running = False
        
        log.section("Memory System Initialized")
        log.info("Memory tiers: Sensory → Working → Short-Term → Long-Term")
        log.info("               ↓              ↓              ↓")
        log.info("            Episodic ←────→ Semantic ←── Procedural")
    
    # ─── Memory Creation ────────────────────────────────────────────────
    
    def _generate_id(self, content: Any) -> str:
        """Generate unique ID for memory."""
        content_str = str(content) + str(time.time())
        return hashlib.md5(content_str.encode()).hexdigest()[:12]
    
    def sensory_input(self, content: Any, source: str = ""):
        """Raw sensory input - goes to sensory buffer first."""
        entry = MemoryEntry(
            id=self._generate_id(content),
            content=content,
            memory_type="sensory",
            source=source,
            importance=0.1
        )
        
        self._sensory.append(entry)
        
        # Keep only recent sensory data
        if len(self._sensory) > self.sensory_capacity:
            self._sensory.pop(0)
        
        log.memory_op("SENSORY", f"{source}: {str(content)[:60]}...")
        
        # Auto-promote interesting sensory data to working memory
        return entry
    
    def working_remember(self, content: Any, importance: float = 0.5, 
                         tags: List[str] = None, source: str = "") -> str:
        """Add to working memory (current focus)."""
        entry = MemoryEntry(
            id=self._generate_id(content),
            content=content,
            memory_type="working",
            importance=importance,
            tags=tags or [],
            source=source
        )
        
        self._working[entry.id] = entry
        
        # Manage working memory capacity
        if len(self._working) > self.working_capacity:
            # Remove least important
            sorted_items = sorted(self._working.items(), 
                                key=lambda x: x[1].relevance_score)
            to_remove = sorted_items[0][0]
            del self._working[to_remove]
        
        log.memory_op("WORKING", entry.id)
        return entry.id
    
    def remember(self, content: Any, importance: float = 0.5,
                 tags: List[str] = None, source: str = "",
                 memory_type: str = "short_term") -> str:
        """
        Store a memory. Auto-determines tier based on importance.
        
        Args:
            content: What to remember
            importance: 0.0-1.0, higher = more important
            tags: Searchable tags
            source: Origin of this memory
            memory_type: Force specific memory type
        """
        entry = MemoryEntry(
            id=self._generate_id(content),
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags or [],
            source=source
        )
        
        # Route to appropriate store
        if importance >= self.consolidation_threshold:
            self._long_term.store(entry)
            log.memory_op("LONG-TERM", f"[{importance:.2f}] {str(content)[:60]}")
        elif memory_type == "episodic":
            self._episodic.store(entry)
            log.memory_op("EPISODIC", entry.id)
        elif memory_type == "semantic":
            self._semantic.store(entry)
            log.memory_op("SEMANTIC", entry.id)
        elif memory_type == "procedural":
            self._procedural.store(entry)
            log.memory_op("PROCEDURAL", entry.id)
        else:
            self._short_term.store(entry)
            log.memory_op("SHORT-TERM", f"[{importance:.2f}] {str(content)[:60]}")
        
        return entry.id
    
    # ─── Memory Retrieval ───────────────────────────────────────────────
    
    def recall(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """
        Search all memory tiers for relevant memories.
        Returns most relevant results first.
        """
        all_results = []
        
        # Search all stores
        for store_name, store in [
            ("long_term", self._long_term),
            ("episodic", self._episodic),
            ("semantic", self._semantic),
            ("short_term", self._short_term),
            ("procedural", self._procedural)
        ]:
            results = store.search(query, limit=limit)
            for entry in results:
                entry.touch()
            all_results.extend(results)
        
        # Sort by relevance score
        all_results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Add working memory if relevant
        working_results = [
            m for m in self._working.values() 
            if query.lower() in str(m.content).lower()
        ]
        
        final = working_results + all_results
        return final[:limit]
    
    def recall_recent(self, hours: int = 24, limit: int = 10) -> List[MemoryEntry]:
        """Get recent memories from all tiers."""
        cutoff = datetime.now() - timedelta(hours=hours)
        results = []
        
        for store in [self._short_term, self._long_term, self._episodic]:
            for entry in store.list_all():
                if entry.created_at > cutoff:
                    results.append(entry)
        
        results.sort(key=lambda x: x.created_at, reverse=True)
        return results[:limit]
    
    def get_working_memory(self) -> List[MemoryEntry]:
        """Get current working memory contents."""
        return sorted(self._working.values(), 
                     key=lambda x: x.relevance_score, reverse=True)
    
    def get_context(self, limit: int = 10) -> str:
        """Get current context as formatted string for AI."""
        context_parts = []
        
        # Working memory
        working = self.get_working_memory()
        if working:
            context_parts.append("=== CURRENT FOCUS ===")
            for entry in working[:3]:
                context_parts.append(f"- {str(entry.content)[:100]}")
        
        # Recent important memories
        recent = self.recall_recent(hours=1, limit=5)
        if recent:
            context_parts.append("\n=== RECENT CONTEXT ===")
            for entry in recent[:5]:
                context_parts.append(f"- {str(entry.content)[:100]}")
        
        return "\n".join(context_parts)
    
    # ─── Memory Management ──────────────────────────────────────────────
    
    def forget(self, memory_id: str) -> bool:
        """Delete a memory by ID."""
        for store in [self._short_term, self._long_term, self._episodic, 
                      self._semantic, self._procedural]:
            if store.delete(memory_id):
                log.memory_op("FORGET", memory_id)
                return True
        return False
    
    def consolidate(self):
        """
        Memory consolidation: promote important short-term memories to long-term.
        Simulates sleep/learning consolidation.
        """
        log.info("Running memory consolidation...")
        promoted = 0
        forgotten = 0
        
        for entry in self._short_term.list_all():
            # Promote if important or frequently accessed
            if (entry.importance >= self.consolidation_threshold or 
                entry.access_count >= 3):
                entry.memory_type = "long_term"
                self._long_term.store(entry)
                self._short_term.delete(entry.id)
                promoted += 1
            
            # Forget old, unimportant memories
            elif entry.age_hours > 48 and entry.importance < 0.3:
                self._short_term.delete(entry.id)
                forgotten += 1
        
        log.info(f"Consolidation complete: {promoted} promoted, {forgotten} forgotten")
    
    def _consolidation_loop(self):
        """Background thread for periodic consolidation."""
        while self._running:
            time.sleep(3600)  # Every hour
            if self._running:
                self.consolidate()
    
    def start_consolidation(self):
        """Start background consolidation."""
        self._running = True
        self._consolidation_thread.start()
        log.info("Memory consolidation thread started")
    
    def stop_consolidation(self):
        """Stop background consolidation."""
        self._running = False
    
    def get_stats(self) -> Dict:
        """Get memory system statistics."""
        return {
            "sensory_buffer": len(self._sensory),
            "working_memory": len(self._working),
            "short_term": len(self._short_term.list_all()),
            "long_term": len(self._long_term.list_all()),
            "episodic": len(self._episodic.list_all()),
            "semantic": len(self._semantic.list_all()),
            "procedural": len(self._procedural.list_all()),
            "total_stored": (
                len(self._short_term.list_all()) +
                len(self._long_term.list_all()) +
                len(self._episodic.list_all()) +
                len(self._semantic.list_all()) +
                len(self._procedural.list_all())
            )
        }
    
    def export_memory(self, filepath: str):
        """Export all memories to file."""
        data = {
            "long_term": [m.to_dict() for m in self._long_term.list_all()],
            "episodic": [m.to_dict() for m in self._episodic.list_all()],
            "semantic": [m.to_dict() for m in self._semantic.list_all()],
            "procedural": [m.to_dict() for m in self._procedural.list_all()],
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        log.success(f"Memory exported to {filepath}")
    
    def __repr__(self):
        stats = self.get_stats()
        return f"<MemorySystem total={stats['total_stored']}>"
