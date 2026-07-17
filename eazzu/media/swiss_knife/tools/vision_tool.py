"""
Vision Tool - Image Analysis and Recognition
Uses the core vision system to actually SEE and understand images.

Features:
- Describe images in natural language
- OCR (text extraction)
- Object detection
- Scene classification
- Face detection
- Image comparison/similarity
- Batch image processing
- Support for URLs and local files
"""

import os
import io
import base64
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.request import urlopen

from core.kernel import ToolBase, ToolMetadata, MicroKernel
from core.vision import VisionSystem, VisionResult
from utils.logger import log


class VisionTool(ToolBase):
    """
    Vision Tool - Makes the AI actually SEE images.
    Not just read filenames, but understand visual content.
    """
    
    metadata = ToolMetadata(
        name="vision",
        version="2.0.0",
        description="See and understand images. Extract text, detect objects, "
                   "describe scenes, and analyze visual content.",
        category="vision",
        tags=["vision", "image", "ocr", "object_detection", "analysis"],
        provides=["image_analysis", "ocr", "object_recognition", "scene_understanding"],
        permissions=["filesystem", "network"]
    )
    
    def __init__(self, kernel: MicroKernel = None):
        super().__init__(kernel)
        self.vision_system = VisionSystem()
    
    def execute(self, *args, **kwargs) -> Any:
        """Main execution method."""
        action = kwargs.get("action", "describe")
        
        actions = {
            "describe": self.describe_image,
            "read_text": self.read_text,
            "detect_objects": self.detect_objects,
            "analyze": self.analyze_image,
            "compare": self.compare_images,
            "batch_process": self.batch_process,
        }
        
        if action in actions:
            return actions[action](**kwargs)
        
        raise ValueError(f"Unknown action: {action}")
    
    def _get_image_path(self, source: str) -> str:
        """Get local path from URL or local path."""
        if source.startswith(("http://", "https://")):
            # Download image
            log.info(f"Downloading image: {source}")
            
            ext = ".jpg"
            if ".png" in source.lower():
                ext = ".png"
            elif ".gif" in source.lower():
                ext = ".gif"
            
            tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
            try:
                with urlopen(source, timeout=30) as response:
                    tmp.write(response.read())
                tmp.close()
                return tmp.name
            except Exception as e:
                tmp.close()
                raise ValueError(f"Failed to download image: {e}")
        
        elif os.path.exists(source):
            return source
        
        else:
            raise ValueError(f"Image not found: {source}")
    
    def describe_image(self, image: str, detail: str = "normal", **kwargs) -> str:
        """
        Get a natural language description of an image.
        
        Args:
            image: File path or URL
            detail: 'brief', 'normal', or 'detailed'
        """
        log.section("Vision: Image Description")
        
        try:
            image_path = self._get_image_path(image)
            result = self.vision_system.see(image_path)
            
            description = result.description or "I couldn't analyze this image."
            
            log.info(f"Description: {description[:200]}...")
            
            # Clean up temp file
            if image_path != image and os.path.exists(image_path):
                os.unlink(image_path)
            
            return description
            
        except Exception as e:
            log.error(f"Vision error: {e}")
            return f"Error analyzing image: {e}"
    
    def read_text(self, image: str, **kwargs) -> str:
        """
        Extract text from image (OCR).
        
        Args:
            image: File path or URL
        """
        log.section("Vision: OCR")
        
        try:
            image_path = self._get_image_path(image)
            result = self.vision_system.see(image_path, tasks=["text"])
            
            text = result.text_content or "No text found in image."
            
            log.info(f"Extracted text: {text[:200]}...")
            
            if image_path != image and os.path.exists(image_path):
                os.unlink(image_path)
            
            return text
            
        except Exception as e:
            log.error(f"OCR error: {e}")
            return f"Error extracting text: {e}"
    
    def detect_objects(self, image: str, **kwargs) -> List[Dict]:
        """
        Detect objects in an image.
        
        Returns list of detected objects with labels and confidence.
        """
        log.section("Vision: Object Detection")
        
        try:
            image_path = self._get_image_path(image)
            result = self.vision_system.see(image_path, tasks=["objects"])
            
            objects = []
            for obj in result.objects:
                objects.append({
                    "label": obj.label,
                    "confidence": obj.confidence,
                    "bbox": obj.bbox
                })
            
            log.info(f"Detected {len(objects)} objects")
            for obj in objects[:10]:
                log.info(f"  - {obj['label']} ({obj['confidence']:.0%})")
            
            if image_path != image and os.path.exists(image_path):
                os.unlink(image_path)
            
            return objects
            
        except Exception as e:
            log.error(f"Object detection error: {e}")
            return []
    
    def analyze_image(self, image: str, **kwargs) -> VisionResult:
        """
        Full image analysis - everything.
        
        Returns complete VisionResult with all available information.
        """
        log.section("Vision: Full Analysis")
        
        try:
            image_path = self._get_image_path(image)
            result = self.vision_system.see(image_path)
            
            # Print summary
            print(result.summarize())
            
            if image_path != image and os.path.exists(image_path):
                os.unlink(image_path)
            
            return result
            
        except Exception as e:
            log.error(f"Analysis error: {e}")
            return VisionResult(description=f"Error: {e}")
    
    def compare_images(self, image1: str, image2: str, **kwargs) -> Dict:
        """
        Compare two images for similarity.
        
        Returns:
            Dict with similarity score and differences
        """
        log.section("Vision: Image Comparison")
        
        try:
            path1 = self._get_image_path(image1)
            path2 = self._get_image_path(image2)
            
            # Compare using perceptual hash if available
            try:
                from PIL import Image
                import imagehash
                
                img1 = Image.open(path1)
                img2 = Image.open(path2)
                
                hash1 = imagehash.average_hash(img1)
                hash2 = imagehash.average_hash(img2)
                
                similarity = 1 - (hash1 - hash2) / 64.0
                
                result = {
                    "similarity": similarity,
                    "hash_difference": hash1 - hash2,
                    "likely_same_image": similarity > 0.9,
                    "possibly_similar": similarity > 0.7,
                }
                
            except ImportError:
                # Fallback: file size and dimension comparison
                stat1 = os.stat(path1)
                stat2 = os.stat(path2)
                
                from PIL import Image
                img1 = Image.open(path1)
                img2 = Image.open(path2)
                
                size_sim = 1 - abs(stat1.st_size - stat2.st_size) / max(stat1.st_size, 1)
                
                result = {
                    "similarity": size_sim,
                    "same_dimensions": img1.size == img2.size,
                    "size_ratio": stat1.st_size / max(stat2.st_size, 1),
                }
            
            log.info(f"Similarity: {result['similarity']:.1%}")
            
            # Cleanup
            for p, orig in [(path1, image1), (path2, image2)]:
                if p != orig and os.path.exists(p):
                    os.unlink(p)
            
            return result
            
        except Exception as e:
            log.error(f"Comparison error: {e}")
            return {"error": str(e)}
    
    def batch_process(self, directory: str = ".", 
                      action: str = "describe",
                      pattern: str = "*.jpg",
                      **kwargs) -> List[Dict]:
        """
        Process multiple images in a directory.
        
        Args:
            directory: Directory to scan
            action: What to do ('describe', 'read_text', 'detect_objects')
            pattern: File pattern to match
        """
        log.section(f"Vision Batch: {action}")
        
        path = Path(directory)
        images = list(path.rglob(pattern))
        
        # Also check common image extensions
        all_images = set()
        for ext in ["*.jpg", "*.jpeg", "*.png", "*.gif", "*.bmp", "*.webp"]:
            all_images.update(path.rglob(ext))
        
        images = sorted(all_images)
        
        log.info(f"Found {len(images)} images")
        
        results = []
        for i, img_path in enumerate(images, 1):
            log.info(f"[{i}/{len(images)}] {img_path.name}")
            
            try:
                if action == "describe":
                    result = self.describe_image(str(img_path))
                elif action == "read_text":
                    result = self.read_text(str(img_path))
                elif action == "detect_objects":
                    result = self.detect_objects(str(img_path))
                else:
                    result = self.describe_image(str(img_path))
                
                results.append({
                    "file": str(img_path),
                    "result": result
                })
                
            except Exception as e:
                results.append({
                    "file": str(img_path),
                    "error": str(e)
                })
        
        log.success(f"Processed {len(results)} images")
        return results
    
    def health_check(self) -> Dict:
        providers = self.vision_system.list_providers()
        return {
            "status": "healthy" if any(p["available"] for p in providers) else "degraded",
            "name": self.metadata.name,
            "version": self.metadata.version,
            "providers": providers
        }
