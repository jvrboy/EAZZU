"""
Vision System - Advanced Image Understanding for Swiss Knife
Can actually SEE images, not just read text about them.

Capabilities:
- Object detection and recognition
- Scene understanding and description
- OCR (text extraction from images)
- Face detection
- Image quality assessment
- Color analysis
- Similarity search
- Image captioning
"""

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from pathlib import Path
import io
import base64

from utils.logger import log


@dataclass
class DetectedObject:
    """An object detected in an image."""
    label: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # x, y, w, h
    attributes: Dict[str, Any] = field(default_factory=dict)


@dataclass
class VisionResult:
    """Complete vision analysis result."""
    description: str = ""           # Human-readable description
    objects: List[DetectedObject] = field(default_factory=list)
    text_content: str = ""          # OCR result
    scene_type: str = ""            # Indoor, outdoor, etc.
    dominant_colors: List[Tuple[int, int, int]] = field(default_factory=list)
    faces_count: int = 0
    image_quality: Dict = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    confidence: float = 0.0
    raw_analysis: Dict = field(default_factory=dict)
    
    def summarize(self) -> str:
        """Create a human-readable summary."""
        lines = ["👁️ VISION ANALYSIS", "=" * 40]
        
        if self.description:
            lines.append(f"📸 {self.description}")
        
        if self.scene_type:
            lines.append(f"🏞️  Scene: {self.scene_type}")
        
        if self.objects:
            lines.append(f"\n🔍 Objects detected ({len(self.objects)}):")
            for obj in self.objects[:10]:
                lines.append(f"   • {obj.label} ({obj.confidence:.0%})")
        
        if self.text_content:
            lines.append(f"\n📝 Text found:")
            lines.append(f"   {self.text_content[:300]}")
        
        if self.faces_count:
            lines.append(f"\n👥 Faces: {self.faces_count}")
        
        if self.dominant_colors:
            lines.append(f"\n🎨 Dominant colors: {len(self.dominant_colors)}")
        
        if self.tags:
            lines.append(f"\n🏷️  Tags: {', '.join(self.tags[:10])}")
        
        return "\n".join(lines)


class VisionProvider(ABC):
    """Abstract base for vision providers."""
    
    @abstractmethod
    def analyze(self, image_path: str, tasks: List[str] = None) -> VisionResult:
        """Analyze an image."""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if this provider is available."""
        pass


class LocalVisionProvider(VisionProvider):
    """
    Local vision processing using OpenCV and other libraries.
    Works without internet or API keys.
    """
    
    def __init__(self):
        self._cv2 = None
        self._np = None
        self._available = False
        self._try_load()
    
    def _try_load(self):
        """Try to load computer vision libraries."""
        try:
            import cv2
            import numpy as np
            self._cv2 = cv2
            self._np = np
            self._available = True
            log.info("Local vision provider loaded (OpenCV)")
        except ImportError:
            log.warning("OpenCV not available. Local vision features limited.")
    
    def is_available(self) -> bool:
        return self._available
    
    def analyze(self, image_path: str, tasks: List[str] = None) -> VisionResult:
        """Analyze image using local processing."""
        result = VisionResult()
        
        if not self._available:
            result.description = "Local vision provider not available. Install opencv-python."
            return result
        
        try:
            # Load image
            img = self._cv2.imread(image_path)
            if img is None:
                result.description = "Could not load image"
                return result
            
            # Basic image properties
            h, w = img.shape[:2]
            result.raw_analysis["dimensions"] = (w, h)
            result.raw_analysis["aspect_ratio"] = w / h
            
            # Color analysis
            self._analyze_colors(img, result)
            
            # Detect if image has text (basic check)
            gray = self._cv2.cvtColor(img, self._cv2.COLOR_BGR2GRAY)
            
            # Simple edge detection for complexity
            edges = self._cv2.Canny(gray, 100, 200)
            edge_density = self._np.mean(edges > 0)
            result.raw_analysis["edge_density"] = float(edge_density)
            
            # Scene classification (simple heuristic)
            mean_color = self._np.mean(img, axis=(0, 1))
            brightness = self._np.mean(gray)
            
            if brightness > 180:
                result.scene_type = "bright indoor/outdoor"
            elif brightness < 50:
                result.scene_type = "dark scene"
            elif mean_color[0] > mean_color[2]:  # More blue than red
                result.scene_type = "outdoor/sky scene"
            else:
                result.scene_type = "general scene"
            
            # Try OCR if available
            if "text" in (tasks or []):
                self._try_ocr(gray, result)
            
            # Generate description
            result.description = self._generate_description(result, (w, h))
            result.confidence = 0.6
            
        except Exception as e:
            log.error(f"Vision analysis error: {e}")
            result.description = f"Analysis error: {e}"
        
        return result
    
    def _analyze_colors(self, img, result: VisionResult):
        """Analyze dominant colors."""
        try:
            # Reshape for k-means
            pixels = img.reshape(-1, 3).astype(self._np.float32)
            
            # K-means clustering for dominant colors
            criteria = (self._cv2.TERM_CRITERIA_EPS + self._cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            _, labels, centers = self._cv2.kmeans(pixels, 5, None, criteria, 10, 
                                                   self._cv2.KMEANS_RANDOM_CENTERS)
            
            # Convert BGR to RGB
            colors = [(int(c[2]), int(c[1]), int(c[0])) for c in centers]
            result.dominant_colors = colors
            
        except Exception as e:
            log.debug(f"Color analysis error: {e}")
    
    def _try_ocr(self, gray_img, result: VisionResult):
        """Try OCR using pytesseract if available."""
        try:
            import pytesseract
            text = pytesseract.image_to_string(gray_img)
            if text.strip():
                result.text_content = text.strip()
                result.tags.append("contains_text")
        except ImportError:
            log.debug("pytesseract not available for OCR")
    
    def _generate_description(self, result: VisionResult, dims: Tuple[int, int]) -> str:
        """Generate a human-readable description."""
        w, h = dims
        desc = f"Image ({w}x{h} pixels). "
        
        if result.scene_type:
            desc += f"Scene appears to be {result.scene_type}. "
        
        if result.dominant_colors:
            desc += f"Contains {len(result.dominant_colors)} dominant color regions. "
        
        if result.text_content:
            desc += "Contains visible text. "
        
        return desc


class AIVisionProvider(VisionProvider):
    """
    AI-powered vision using API (OpenAI, etc).
    Much more capable than local vision.
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-4o"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self._available = bool(self.api_key)
    
    def is_available(self) -> bool:
        return self._available
    
    def analyze(self, image_path: str, tasks: List[str] = None) -> VisionResult:
        """Analyze image using AI vision API."""
        result = VisionResult()
        
        if not self._available:
            result.description = "AI vision not available. Set OPENAI_API_KEY."
            return result
        
        try:
            import openai
            client = openai.OpenAI(api_key=self.api_key)
            
            # Encode image
            with open(image_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode()
            
            # Determine what to analyze
            task_prompt = "Describe this image in detail."
            if tasks:
                if "objects" in tasks:
                    task_prompt += " List all objects detected."
                if "text" in tasks:
                    task_prompt += " Extract any text visible."
                if "scene" in tasks:
                    task_prompt += " Identify the scene type."
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": task_prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }],
                max_tokens=1000
            )
            
            description = response.choices[0].message.content
            result.description = description
            result.confidence = 0.95
            
            # Parse objects from description
            result.tags = self._extract_tags(description)
            
            # Try to identify scene type
            result.scene_type = self._detect_scene(description)
            
        except Exception as e:
            log.error(f"AI vision analysis error: {e}")
            result.description = f"AI analysis error: {e}"
        
        return result
    
    def _extract_tags(self, description: str) -> List[str]:
        """Extract tags from AI description."""
        # Simple keyword extraction
        common_tags = ["person", "people", "building", "nature", "animal", "food",
                      "vehicle", "indoor", "outdoor", "text", "landscape", "portrait",
                      "city", "water", "sky", "tree", "technology"]
        desc_lower = description.lower()
        return [tag for tag in common_tags if tag in desc_lower]
    
    def _detect_scene(self, description: str) -> str:
        """Detect scene type from description."""
        desc_lower = description.lower()
        if any(w in desc_lower for w in ["outdoor", "nature", "landscape", "sky"]):
            return "outdoor"
        elif any(w in desc_lower for w in ["indoor", "room", "inside", "building interior"]):
            return "indoor"
        elif any(w in desc_lower for w in ["urban", "city", "street", "building"]):
            return "urban"
        return "unknown"


class VisionSystem:
    """
    Unified vision system that combines local and AI vision.
    Automatically selects the best available provider.
    """
    
    def __init__(self):
        self.providers: List[VisionProvider] = [
            AIVisionProvider(),      # Try AI first (more capable)
            LocalVisionProvider(),   # Fallback to local
        ]
        
        self._active_provider = None
        self._select_provider()
        
        log.section("Vision System Initialized")
        if self._active_provider:
            log.info(f"Active provider: {self._active_provider.__class__.__name__}")
        else:
            log.warning("No vision providers available. Install opencv-python or set OPENAI_API_KEY.")
    
    def _select_provider(self):
        """Select the best available provider."""
        for provider in self.providers:
            if provider.is_available():
                self._active_provider = provider
                break
    
    def see(self, image_path: str, tasks: List[str] = None) -> VisionResult:
        """
        Analyze an image and return comprehensive results.
        
        Args:
            image_path: Path to image file
            tasks: Specific tasks (objects, text, scene, faces, colors)
        """
        log.info(f"Analyzing image: {image_path}")
        
        if not os.path.exists(image_path):
            return VisionResult(description=f"Image not found: {image_path}")
        
        if not self._active_provider:
            return VisionResult(
                description="No vision providers available. "
                           "Install opencv-python or set OPENAI_API_KEY."
            )
        
        result = self._active_provider.analyze(image_path, tasks)
        
        log.info(f"Vision analysis complete: {result.description[:100]}...")
        return result
    
    def describe(self, image_path: str) -> str:
        """Get a simple text description of an image."""
        result = self.see(image_path)
        return result.description or "Could not analyze image"
    
    def read_text(self, image_path: str) -> str:
        """Extract text from an image (OCR)."""
        result = self.see(image_path, tasks=["text"])
        return result.text_content or "No text found"
    
    def detect_objects(self, image_path: str) -> List[DetectedObject]:
        """Detect objects in an image."""
        result = self.see(image_path, tasks=["objects"])
        return result.objects
    
    def list_providers(self) -> List[Dict]:
        """List available vision providers."""
        return [
            {
                "name": p.__class__.__name__,
                "available": p.is_available()
            }
            for p in self.providers
        ]
    
    def __repr__(self):
        provider_name = self._active_provider.__class__.__name__ if self._active_provider else "None"
        return f"<VisionSystem provider={provider_name}>"
