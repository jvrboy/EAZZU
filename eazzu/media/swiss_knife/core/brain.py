"""
Brain System - AI Reasoning Engine for Swiss Knife
A human-like brain with multiple cognitive capabilities:
- Perception: Interprets input from all tools and sensors
- Reasoning: Multi-step logical thinking and problem solving  
- Planning: Creates and executes multi-step plans
- Learning: Learns from experience and improves over time
- Creativity: Generates novel solutions and ideas
- Reflection: Self-analyzes and improves reasoning
"""

import os
import json
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
from enum import Enum
import threading

from core.memory import MemorySystem, MemoryEntry
from utils.logger import log


class ThoughtType(Enum):
    """Types of thoughts the brain can have."""
    PERCEPTION = "perception"      # Observing input
    ANALYSIS = "analysis"          # Breaking down problems
    REASONING = "reasoning"        # Logical deduction
    PLANNING = "planning"          # Creating action plans
    REFLECTION = "reflection"      # Self-evaluation
    CREATIVE = "creative"          # Generating ideas
    MEMORY = "memory"              # Recalling information
    DECISION = "decision"          # Making choices
    EXECUTION = "execution"        # Carrying out actions
    LEARNING = "learning"          # Updating knowledge


@dataclass
class Thought:
    """A single thought in the brain's stream of consciousness."""
    content: str
    thought_type: ThoughtType
    confidence: float = 1.0  # 0.0 to 1.0
    source: str = ""         # What triggered this thought
    timestamp: datetime = field(default_factory=datetime.now)
    related_thoughts: List[str] = field(default_factory=list)
    
    def __str__(self):
        icon = {
            ThoughtType.PERCEPTION: "👁️",
            ThoughtType.ANALYSIS: "🔍",
            ThoughtType.REASONING: "🧮",
            ThoughtType.PLANNING: "📋",
            ThoughtType.REFLECTION: "💭",
            ThoughtType.CREATIVE: "💡",
            ThoughtType.MEMORY: "💾",
            ThoughtType.DECISION: "⚡",
            ThoughtType.EXECUTION: "⚙️",
            ThoughtType.LEARNING: "📚",
        }.get(self.thought_type, "🧠")
        
        return f"{icon} [{self.thought_type.value}] {self.content}"


@dataclass
class ReasoningChain:
    """A chain of thoughts forming a reasoning process."""
    id: str
    goal: str
    thoughts: List[Thought] = field(default_factory=list)
    conclusion: str = ""
    confidence: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    completed: bool = False
    
    def add_thought(self, thought: Thought):
        self.thoughts.append(thought)
    
    def summarize(self) -> str:
        """Summarize the reasoning chain."""
        lines = [f"🎯 Goal: {self.goal}", ""]
        for t in self.thoughts:
            lines.append(f"  {t}")
        lines.append("")
        lines.append(f"📌 Conclusion: {self.conclusion} (confidence: {self.confidence:.2f})")
        return "\n".join(lines)


class CognitiveModule(ABC):
    """Base class for cognitive modules."""
    
    @abstractmethod
    def process(self, input_data: Any, context: Dict) -> Thought:
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass


class PerceptionModule(CognitiveModule):
    """Processes raw input into meaningful perceptions."""
    
    @property
    def name(self) -> str:
        return "Perception"
    
    def process(self, input_data: Any, context: Dict) -> Thought:
        """Convert raw input to structured perception."""
        content = f"I perceive: {str(input_data)[:200]}"
        
        # Categorize input type
        if isinstance(input_data, str):
            if input_data.startswith("http"):
                content = f"I see a URL: {input_data}. This could be a download request."
            elif any(cmd in input_data.lower() for cmd in ["download", "get", "save"]):
                content = f"I detect a download intent in: '{input_data}'"
            elif any(cmd in input_data.lower() for cmd in ["tag", "rename", "music", "song", "audio"]):
                content = f"I detect an audio processing intent: '{input_data}'"
            elif any(cmd in input_data.lower() for cmd in ["image", "picture", "photo", "see", "look"]):
                content = f"I detect a vision/image request: '{input_data}'"
            elif any(cmd in input_data.lower() for cmd in ["plan", "workflow", "pipeline", "automate"]):
                content = f"I detect a planning/automation request: '{input_data}'"
        
        return Thought(
            content=content,
            thought_type=ThoughtType.PERCEPTION,
            source="input",
            confidence=0.9
        )


class AnalysisModule(CognitiveModule):
    """Analyzes problems and breaks them down."""
    
    @property
    def name(self) -> str:
        return "Analysis"
    
    def process(self, input_data: Any, context: Dict) -> Thought:
        """Analyze the current situation."""
        perceptions = [t for t in context.get("thoughts", []) 
                      if t.thought_type == ThoughtType.PERCEPTION]
        
        if not perceptions:
            return Thought("No perceptions to analyze", ThoughtType.ANALYSIS)
        
        last_perception = perceptions[-1].content
        
        # Extract key information
        analysis = f"Analyzing: {last_perception}\n"
        
        # Identify required tools
        required_tools = []
        if "download" in last_perception.lower() or "url" in last_perception.lower():
            required_tools.append("universal_downloader")
        if "audio" in last_perception.lower() or "music" in last_perception.lower():
            required_tools.append("audio_tagger")
        if "image" in last_perception.lower() or "vision" in last_perception.lower():
            required_tools.append("vision")
        if "plan" in last_perception.lower() or "workflow" in last_perception.lower():
            required_tools.append("pipeline_planner")
        
        if required_tools:
            analysis += f"Required tools: {', '.join(required_tools)}"
        else:
            analysis += "No specific tools identified yet, need more information."
        
        return Thought(
            content=analysis,
            thought_type=ThoughtType.ANALYSIS,
            confidence=0.8
        )


class ReasoningModule(CognitiveModule):
    """Logical reasoning and deduction."""
    
    @property
    def name(self) -> str:
        return "Reasoning"
    
    def process(self, input_data: Any, context: Dict) -> Thought:
        """Apply logical reasoning."""
        analysis = [t for t in context.get("thoughts", [])
                   if t.thought_type == ThoughtType.ANALYSIS]
        
        if not analysis:
            return Thought("Need analysis before reasoning", ThoughtType.REASONING)
        
        last_analysis = analysis[-1].content
        
        # Build reasoning chain
        reasoning = "Reasoning through the problem:\n"
        
        # Check available tools
        available = context.get("available_tools", [])
        
        # Determine approach
        if "universal_downloader" in last_analysis:
            reasoning += "1. User wants to download content from a URL\n"
            reasoning += "2. I should use the universal_downloader tool\n"
            reasoning += "3. Need to extract URL and format preferences\n"
        
        elif "audio_tagger" in last_analysis:
            reasoning += "1. User has audio files needing identification/tagging\n"
            reasoning += "2. I should use the audio_tagger tool\n"
            reasoning += "3. Need to scan files, fingerprint audio, fetch metadata\n"
        
        elif "vision" in last_analysis:
            reasoning += "1. User wants to analyze or understand images\n"
            reasoning += "2. I should use the vision tool\n"
            reasoning += "3. Need to process image and describe contents\n"
        
        else:
            reasoning += "1. The request is ambiguous\n"
            reasoning += "2. I should ask clarifying questions or use the brain to interpret\n"
        
        return Thought(
            content=reasoning,
            thought_type=ThoughtType.REASONING,
            confidence=0.85
        )


class PlanningModule(CognitiveModule):
    """Creates action plans."""
    
    @property
    def name(self) -> str:
        return "Planning"
    
    def process(self, input_data: Any, context: Dict) -> Thought:
        """Create an action plan."""
        reasoning = [t for t in context.get("thoughts", [])
                    if t.thought_type == ThoughtType.REASONING]
        
        if not reasoning:
            return Thought("Need reasoning before planning", ThoughtType.PLANNING)
        
        # Generate plan steps
        plan = "Action Plan:\n"
        
        # Check what the user wants and create appropriate plan
        user_input = str(input_data).lower()
        
        if "download" in user_input or "http" in user_input:
            plan += "Step 1: Extract URL from user input\n"
            plan += "Step 2: Determine content type (video/audio/file)\n"
            plan += "Step 3: Configure download options\n"
            plan += "Step 4: Execute download\n"
            plan += "Step 5: Post-process (convert, tag, organize)\n"
        
        elif "tag" in user_input or "music" in user_input or "song" in user_input:
            plan += "Step 1: Scan local audio files\n"
            plan += "Step 2: Generate audio fingerprints\n"
            plan += "Step 3: Identify songs using fingerprint database\n"
            plan += "Step 4: Fetch metadata (artist, title, album, lyrics)\n"
            plan += "Step 5: Download album artwork\n"
            plan += "Step 6: Embed tags and artwork\n"
            plan += "Step 7: Rename files with proper naming\n"
        
        elif "image" in user_input or "picture" in user_input or "see" in user_input:
            plan += "Step 1: Locate image file or URL\n"
            plan += "Step 2: Process image with vision system\n"
            plan += "Step 3: Generate description/analysis\n"
            plan += "Step 4: Return insights to user\n"
        
        else:
            plan += "Step 1: Clarify user intent\n"
            plan += "Step 2: Identify appropriate tools\n"
            plan += "Step 3: Execute with user confirmation\n"
        
        return Thought(
            content=plan,
            thought_type=ThoughtType.PLANNING,
            confidence=0.9
        )


class BrainSystem:
    """
    The Brain: Central intelligence of Swiss Knife.
    
    Capabilities:
    - Multi-step reasoning with thought chains
    - Context-aware decision making
    - Tool selection and orchestration
    - Learning from outcomes
    - Natural language understanding
    - Reflection and self-improvement
    """
    
    def __init__(self, memory: MemorySystem = None):
        self.memory = memory or MemorySystem()
        
        # Cognitive modules
        self.modules: Dict[str, CognitiveModule] = {
            "perception": PerceptionModule(),
            "analysis": AnalysisModule(),
            "reasoning": ReasoningModule(),
            "planning": PlanningModule(),
        }
        
        # Thought stream
        self.thoughts: List[Thought] = []
        self.reasoning_chains: Dict[str, ReasoningChain] = {}
        
        # Current reasoning context
        self._context: Dict[str, Any] = {
            "thoughts": [],
            "available_tools": [],
            "user_preferences": {},
            "session_history": []
        }
        
        # Active chain
        self._active_chain: Optional[ReasoningChain] = None
        
        # Reflection settings
        self.reflection_enabled = True
        self.max_thoughts = 100
        
        log.section("Brain System Initialized")
        log.brain_think("Brain online. Cognitive modules loaded: " + 
                       ", ".join(self.modules.keys()))
    
    # ─── Perception ─────────────────────────────────────────────────────
    
    def perceive(self, input_data: Any) -> Thought:
        """Process raw input through perception module."""
        thought = self.modules["perception"].process(input_data, self._context)
        self._add_thought(thought)
        log.brain_think(f"Perception: {thought.content}")
        
        # Store in sensory memory
        self.memory.sensory_input(input_data, source="brain_perception")
        
        return thought
    
    # ─── Reasoning ──────────────────────────────────────────────────────
    
    def think(self, input_data: Any, depth: str = "deep") -> ReasoningChain:
        """
        Main thinking process - multi-step reasoning.
        
        Args:
            input_data: What to think about
            depth: "shallow", "normal", or "deep"
        """
        import hashlib
        chain_id = hashlib.md5(f"{input_data}{datetime.now()}".encode()).hexdigest()[:8]
        
        chain = ReasoningChain(
            id=chain_id,
            goal=str(input_data)[:200]
        )
        self.reasoning_chains[chain_id] = chain
        self._active_chain = chain
        
        log.section("Brain Thinking")
        log.brain_think(f"Starting reasoning chain #{chain_id}: {chain.goal}")
        
        # Step 1: Perception
        perception = self.perceive(input_data)
        chain.add_thought(perception)
        
        # Step 2: Analysis
        analysis = self.modules["analysis"].process(input_data, self._context)
        chain.add_thought(analysis)
        log.brain_think(f"Analysis: {analysis.content[:100]}")
        
        # Step 3: Memory recall
        relevant_memories = self.memory.recall(str(input_data), limit=3)
        if relevant_memories:
            memory_thought = Thought(
                content=f"I recall: {[str(m.content)[:80] for m in relevant_memories]}",
                thought_type=ThoughtType.MEMORY,
                confidence=0.7
            )
            chain.add_thought(memory_thought)
            log.brain_think(f"Memory: Found {len(relevant_memories)} relevant memories")
        
        # Step 4: Reasoning
        reasoning = self.modules["reasoning"].process(input_data, self._context)
        chain.add_thought(reasoning)
        log.brain_think(f"Reasoning: {reasoning.content[:100]}")
        
        # Step 5: Planning (for deep reasoning)
        if depth in ("normal", "deep"):
            planning = self.modules["planning"].process(input_data, self._context)
            chain.add_thought(planning)
            log.brain_think(f"Planning: {planning.content[:100]}")
        
        # Step 6: Reflection (for deep reasoning)
        if depth == "deep" and self.reflection_enabled:
            reflection = self._reflect(chain)
            chain.add_thought(reflection)
        
        # Final decision
        decision = self._make_decision(chain)
        chain.add_thought(decision)
        chain.conclusion = decision.content
        chain.confidence = decision.confidence
        chain.completed = True
        
        # Store in memory
        self.memory.remember(
            content=chain.summarize(),
            importance=0.6,
            tags=["reasoning", "brain"],
            source="brain",
            memory_type="episodic"
        )
        
        log.brain_think(f"Conclusion: {chain.conclusion[:150]}")
        log.success(f"Reasoning chain #{chain_id} complete (confidence: {chain.confidence:.2f})")
        
        return chain
    
    def quick_think(self, input_data: Any) -> str:
        """Fast single-step thinking for simple decisions."""
        thought = self.perceive(input_data)
        
        # Quick pattern matching for common tasks
        user_input = str(input_data).lower()
        
        if any(word in user_input for word in ["download", "http", "youtube", "url"]):
            return "I'll help you download that content. Let me use the universal downloader."
        
        elif any(word in user_input for word in ["music", "song", "audio", "tag", "rename"]):
            return "I'll process your audio files. Let me scan and identify them."
        
        elif any(word in user_input for word in ["image", "picture", "photo", "look", "see"]):
            return "I'll analyze that image for you using my vision system."
        
        elif any(word in user_input for word in ["plan", "workflow", "automate", "pipeline"]):
            return "I'll create a workflow pipeline for that task."
        
        else:
            return f"I understand you want to: {input_data}. Let me figure out the best approach."
    
    # ─── Reflection ─────────────────────────────────────────────────────
    
    def _reflect(self, chain: ReasoningChain) -> Thought:
        """Self-reflection on reasoning quality."""
        reflection_text = "Reflecting on my reasoning:\n"
        
        # Check if reasoning is complete
        has_plan = any(t.thought_type == ThoughtType.PLANNING for t in chain.thoughts)
        has_reasoning = any(t.thought_type == ThoughtType.REASONING for t in chain.thoughts)
        
        if has_plan and has_reasoning:
            reflection_text += "- Reasoning appears complete with analysis and plan\n"
        else:
            reflection_text += "- Reasoning may be incomplete, need more analysis\n"
        
        # Check for potential issues
        analysis_thoughts = [t for t in chain.thoughts if t.thought_type == ThoughtType.ANALYSIS]
        if analysis_thoughts:
            if "ambiguous" in analysis_thoughts[-1].content:
                reflection_text += "- The request is ambiguous, I should ask for clarification\n"
        
        reflection_text += "- I should consider edge cases and alternative approaches\n"
        
        return Thought(
            content=reflection_text,
            thought_type=ThoughtType.REFLECTION,
            confidence=0.8
        )
    
    # ─── Decision Making ────────────────────────────────────────────────
    
    def _make_decision(self, chain: ReasoningChain) -> Thought:
        """Make final decision based on reasoning chain."""
        # Extract the plan and recommended tools
        plans = [t for t in chain.thoughts if t.thought_type == ThoughtType.PLANNING]
        
        if plans:
            # We have a plan - recommend tool execution
            plan_text = plans[-1].content
            
            # Determine which tool to use
            user_input = chain.goal.lower()
            
            if "download" in user_input or "http" in user_input:
                return Thought(
                    content="Decision: Use universal_downloader tool to download the content",
                    thought_type=ThoughtType.DECISION,
                    confidence=0.95
                )
            elif any(w in user_input for w in ["music", "song", "audio", "tag"]):
                return Thought(
                    content="Decision: Use audio_tagger tool to identify and tag audio files",
                    thought_type=ThoughtType.DECISION,
                    confidence=0.95
                )
            elif any(w in user_input for w in ["image", "picture", "photo"]):
                return Thought(
                    content="Decision: Use vision tool to analyze the image",
                    thought_type=ThoughtType.DECISION,
                    confidence=0.95
                )
            else:
                return Thought(
                    content="Decision: Need more information to determine the right tool",
                    thought_type=ThoughtType.DECISION,
                    confidence=0.5
                )
        
        return Thought(
            content="Decision: Unable to form a complete plan. Please provide more details.",
            thought_type=ThoughtType.DECISION,
            confidence=0.3
        )
    
    # ─── Tool Management ────────────────────────────────────────────────
    
    def set_available_tools(self, tools: List[str]):
        """Update the list of available tools."""
        self._context["available_tools"] = tools
        log.brain_think(f"Available tools updated: {tools}")
    
    # ─── Learning ───────────────────────────────────────────────────────
    
    def learn(self, experience: str, outcome: str, success: bool):
        """Learn from an experience."""
        importance = 0.8 if success else 0.9  # Learn more from failures
        
        self.memory.remember(
            content={
                "experience": experience,
                "outcome": outcome,
                "success": success
            },
            importance=importance,
            tags=["learning", "experience"],
            source="brain",
            memory_type="episodic"
        )
        
        log.brain_think(f"Learned from experience: {experience[:80]}... Success: {success}")
    
    # ─── Context Management ─────────────────────────────────────────────
    
    def _add_thought(self, thought: Thought):
        """Add a thought to the stream."""
        self.thoughts.append(thought)
        self._context["thoughts"] = self.thoughts[-self.max_thoughts:]
        
        # Keep stream manageable
        if len(self.thoughts) > self.max_thoughts * 2:
            self.thoughts = self.thoughts[-self.max_thoughts:]
    
    def get_context(self) -> str:
        """Get current brain context for external use."""
        return self.memory.get_context()
    
    def get_thought_stream(self, limit: int = 20) -> List[Thought]:
        """Get recent thoughts."""
        return self.thoughts[-limit:]
    
    def clear_thoughts(self):
        """Clear the thought stream."""
        self.thoughts.clear()
        self._context["thoughts"] = []
    
    # ─── Status ─────────────────────────────────────────────────────────
    
    def status(self) -> Dict:
        """Get brain status."""
        return {
            "cognitive_modules": list(self.modules.keys()),
            "total_thoughts": len(self.thoughts),
            "reasoning_chains": len(self.reasoning_chains),
            "active_chain": self._active_chain.id if self._active_chain else None,
            "available_tools": self._context["available_tools"],
            "memory_stats": self.memory.get_stats()
        }
    
    def __repr__(self):
        return f"<BrainSystem modules={len(self.modules)} thoughts={len(self.thoughts)}>"
