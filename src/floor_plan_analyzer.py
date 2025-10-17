"""
FloorPlanAnalyzer - AI-powered floor plan analysis and boundary tracing
Single optimized API call for complete floor plan analysis
"""
import os
import base64
import json
import logging
from io import BytesIO
from PIL import Image
from openai import OpenAI

logger = logging.getLogger(__name__)


class FloorPlanAnalyzer:
    """Analyzes floor plans and traces wall boundaries using AI vision"""
    
    def __init__(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        self.client = OpenAI(api_key=api_key)
    
    def analyze_floor_plan(self, image: Image.Image) -> dict:
        """
        Analyze floor plan image and trace all wall boundaries in a single AI call.
        
        Args:
            image: PIL Image of the floor plan drawing
            
        Returns:
            Dictionary with:
            - floor_type: str (basement, main_floor, second_floor, etc.)
            - confidence: float (0-1)
            - outer_boundary: list of [x, y] coordinates
            - inner_boundaries: list of boundary lists (each is list of [x, y])
            - garage_wall: list of [x, y] coordinates (if garage detected)
            - has_garage: bool
        """
        # Convert image to base64
        buffered = BytesIO()
        image.save(buffered, format="PNG")
        img_base64 = base64.b64encode(buffered.getvalue()).decode()
        
        # Create comprehensive prompt for single AI call
        prompt = self._create_analysis_prompt(image.width, image.height)
        
        logger.info(f"Sending floor plan analysis request to AI (image size: {image.width}x{image.height})")
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=4000,
                temperature=0.1  # Low temperature for consistent, accurate results
            )
            
            # Parse AI response
            content = response.choices[0].message.content
            logger.info("Received AI response, parsing JSON...")
            logger.debug(f"AI Response (first 500 chars): {content[:500]}")
            
            # Extract JSON from response (metadata only)
            result = self._parse_ai_response(content, image.width, image.height)
            
            logger.info(f"Floor plan metadata: {result['floor_type']} (confidence: {result['confidence']:.0%})")
            logger.info(f"  - Garage detected: {result['has_garage']}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            raise Exception(f"Floor plan analysis failed: {str(e)}")
    
    def _create_analysis_prompt(self, img_width: int, img_height: int) -> str:
        """Create AI prompt for floor plan analysis with wall location identification"""
        return f"""You are an expert architectural drawing analyzer. This is a {img_width}x{img_height} pixel image of an architectural floor plan.

YOUR TASK: Analyze the floor plan and identify:
1. Metadata (floor type, garage presence)
2. Main wall locations (BOUNDING BOXES ONLY - not precise traces)

METADATA TO IDENTIFY:

1. FLOOR TYPE: Identify which floor level this plan represents
   - Options: basement, main_floor, second_floor, third_floor, terrace
   - Look for labels like "BASEMENT PLAN", "FIRST FLOOR", "SECOND FLOOR", etc.
   - Consider room types (furnace room suggests basement, living room suggests main floor)

2. CONFIDENCE: Your confidence level in the floor type identification (0.0 to 1.0)

3. GARAGE: Determine if there is a garage in this floor plan
   - Look for labels like "GARAGE", "2-CAR GARAGE", etc.
   - Look for garage door symbols

MAIN WALL LOCATIONS TO IDENTIFY:

4. EXTERIOR OUTER WALL: Identify the REGION where the main building's outer perimeter wall is located
   - This is the OUTERMOST wall that defines the building envelope
   - Return a bounding box (min_x, min_y, max_x, max_y) that contains this wall
   - Coordinates in PIXELS relative to image (0,0 is top-left)

5. EXTERIOR INNER WALL: Identify the REGION where the main building's inner perimeter wall is located  
   - This is the INNER edge of the exterior wall (parallel to outer wall, slightly inside)
   - Return a bounding box that contains this wall
   - Should be slightly inside the outer wall boundary

IMPORTANT:
- Focus on the MAIN BUILDING PERIMETER walls, NOT interior room dividers
- Ignore small details like door frames, window frames, closets
- The bounding boxes should encompass the general region where these walls are located
- Precise coordinates will come from vector analysis - you just identify WHERE to look

Return JSON in this EXACT structure:
{{
  "floor_type": "basement|main_floor|second_floor|third_floor|terrace",
  "confidence": 0.95,
  "has_garage": true|false,
  "exterior_outer_bbox": {{"min_x": 100, "min_y": 50, "max_x": 1100, "max_y": 750}},
  "exterior_inner_bbox": {{"min_x": 110, "min_y": 60, "max_x": 1090, "max_y": 740}}
}}

Return ONLY the JSON object, no additional text or explanations."""

    def _parse_ai_response(self, content: str, img_width: int, img_height: int) -> dict:
        """Parse and validate AI response including wall location bounding boxes"""
        try:
            # Remove markdown code blocks if present
            content = content.replace('```json', '').replace('```', '').strip()
            
            # Extract JSON from response (sometimes AI adds explanation text)
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            
            if json_start == -1 or json_end == 0:
                logger.error(f"No JSON found. Response content: {content[:1000]}")
                raise ValueError("No JSON found in AI response")
            
            json_str = content[json_start:json_end]
            data = json.loads(json_str)
            
            # Validate required metadata fields
            required_fields = ["floor_type", "confidence", "has_garage"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate floor type
            valid_floor_types = ["basement", "main_floor", "second_floor", "third_floor", "terrace"]
            if data["floor_type"] not in valid_floor_types:
                logger.warning(f"Unknown floor type '{data['floor_type']}', defaulting to 'main_floor'")
                data["floor_type"] = "main_floor"
            
            # Ensure confidence is between 0 and 1
            data["confidence"] = max(0.0, min(1.0, float(data["confidence"])))
            
            # Ensure has_garage is boolean
            data["has_garage"] = bool(data["has_garage"])
            
            # Parse and validate bounding boxes (optional - may not be present)
            data["exterior_outer_bbox"] = self._parse_bbox(
                data.get("exterior_outer_bbox"), img_width, img_height, "exterior_outer"
            )
            data["exterior_inner_bbox"] = self._parse_bbox(
                data.get("exterior_inner_bbox"), img_width, img_height, "exterior_inner"
            )
            
            logger.info(f"  - Outer wall bbox: {data['exterior_outer_bbox']}")
            logger.info(f"  - Inner wall bbox: {data['exterior_inner_bbox']}")
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response content: {content[:500]}")
            raise ValueError(f"AI returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise
    
    def _parse_bbox(self, bbox_data: dict, max_width: int, max_height: int, name: str) -> dict:
        """Parse and validate a bounding box from AI response"""
        if not bbox_data:
            logger.warning(f"No bbox data for {name}, returning None")
            return None
        
        try:
            # Ensure all required fields are present
            required = ["min_x", "min_y", "max_x", "max_y"]
            for field in required:
                if field not in bbox_data:
                    logger.warning(f"Missing {field} in {name} bbox, returning None")
                    return None
            
            # Clamp values to image bounds
            min_x = max(0, min(int(bbox_data["min_x"]), max_width))
            min_y = max(0, min(int(bbox_data["min_y"]), max_height))
            max_x = max(0, min(int(bbox_data["max_x"]), max_width))
            max_y = max(0, min(int(bbox_data["max_y"]), max_height))
            
            # Validate bbox is not inverted
            if min_x >= max_x or min_y >= max_y:
                logger.warning(f"Invalid bbox for {name}: min >= max")
                return None
            
            return {
                "min_x": min_x,
                "min_y": min_y,
                "max_x": max_x,
                "max_y": max_y
            }
        except Exception as e:
            logger.warning(f"Failed to parse bbox for {name}: {e}")
            return None
    
    def _validate_boundary(self, boundary: list, max_x: int, max_y: int, name: str) -> list:
        """Validate and clean boundary coordinates"""
        if not boundary or len(boundary) < 3:
            logger.warning(f"Boundary '{name}' has too few points ({len(boundary)}), skipping")
            return []
        
        # Ensure coordinates are within bounds
        cleaned = []
        for point in boundary:
            if len(point) != 2:
                continue
            x, y = point
            x = max(0, min(x, max_x))
            y = max(0, min(y, max_y))
            cleaned.append([x, y])
        
        # Ensure boundary is closed
        if len(cleaned) >= 3:
            if cleaned[0] != cleaned[-1]:
                cleaned.append(cleaned[0])
        
        logger.debug(f"Boundary '{name}': {len(cleaned)} points")
        return cleaned
