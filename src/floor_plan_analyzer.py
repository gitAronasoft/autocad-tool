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
            
            # Extract JSON from response
            result = self._parse_ai_response(content, image.width, image.height)
            
            logger.info(f"Floor plan analyzed: {result['floor_type']} (confidence: {result['confidence']:.0%})")
            logger.info(f"  - Outer boundary: {len(result['outer_boundary'])} points")
            logger.info(f"  - Inner boundaries: {len(result['inner_boundaries'])} found")
            logger.info(f"  - Garage detected: {result['has_garage']}")
            
            return result
            
        except Exception as e:
            logger.error(f"AI analysis failed: {str(e)}")
            raise Exception(f"Floor plan analysis failed: {str(e)}")
    
    def _create_analysis_prompt(self, img_width: int, img_height: int) -> str:
        """Create comprehensive AI prompt for floor plan analysis"""
        return f"""You are an expert architectural drawing analyzer. This is a {img_width}x{img_height} pixel image of an architectural floor plan.

YOUR TASK: Meticulously trace the EXACT wall boundaries as drawn in the floor plan.

CRITICAL: DO NOT create approximations or simple rectangles. You MUST follow the ACTUAL drawn wall lines PRECISELY with many coordinate points to capture every corner, turn, and angle.

UNDERSTANDING ARCHITECTURAL WALLS:
- Walls are drawn with TWO parallel black lines (representing wall thickness)
- You must trace BOTH the outer edge and inner edge of walls
- Each wall boundary is a polygon that follows the drawn lines exactly

WHAT TO TRACE:

1. EXTERIOR WALLS - OUTER EDGE:
   - Trace the outermost black line of the building perimeter
   - Follow every corner, jog, bump-out, and architectural feature EXACTLY
   - This should trace around the OUTSIDE of the entire building
   - Use 40-80 points to capture all detail

2. EXTERIOR WALLS - INNER EDGE (return as first item in inner_boundaries):
   - Trace the innermost black line of exterior walls (facing the interior space)
   - Follow every corner and detail EXACTLY, parallel to outer edge but offset by wall thickness
   - Use 40-80 points to capture all detail

3. INTERIOR WALLS (return as additional items in inner_boundaries):
   - For EACH interior wall, trace both parallel edges
   - Each wall becomes a separate closed polygon
   - Follow the drawn lines precisely
   - Use 15-40 points per wall to capture all details

4. IDENTIFY: Floor type (basement, main_floor, second_floor, terrace)

5. IF GARAGE EXISTS: Trace the wall separating conditioned space from garage

CRITICAL REQUIREMENTS:
✓ Trace ACTUAL drawn lines, not bounding boxes
✓ Use MANY coordinate points (40-80 for perimeters, 15-40 for interior walls)
✓ Capture EVERY corner, angle, bump-out, and architectural feature
✓ Coordinates in pixels, (0,0) = top-left
✓ Each polygon must be CLOSED (first point = last point)
✗ DO NOT create simple 4-point rectangles
✗ DO NOT approximate - trace exactly

Return JSON in this EXACT structure:
{{
  "floor_type": "basement|main_floor|second_floor|third_floor|terrace",
  "confidence": 0.95,
  "has_garage": true|false,
  "outer_boundary": [[x1,y1], [x2,y2], ... many points ..., [x1,y1]],
  "inner_boundaries": [
    [[x1,y1], [x2,y2], ... many points ..., [x1,y1]],
    [[x1,y1], [x2,y2], ... points ..., [x1,y1]],
    ... more interior walls ...
  ],
  "garage_wall": [[x1,y1], [x2,y2], ... points ..., [x1,y1]]
}}

COORDINATE CONSTRAINTS:
- X must be 0 to {img_width}
- Y must be 0 to {img_height}
- If no garage, set "has_garage": false, "garage_wall": []

REMEMBER: The quality of your tracing is judged by how accurately it follows the actual drawn wall lines. Use MANY points to capture all architectural detail.

Return ONLY the JSON object."""

    def _parse_ai_response(self, content: str, img_width: int, img_height: int) -> dict:
        """Parse and validate AI response"""
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
            
            # Validate required fields
            required_fields = ["floor_type", "confidence", "has_garage", "outer_boundary", "inner_boundaries"]
            for field in required_fields:
                if field not in data:
                    raise ValueError(f"Missing required field: {field}")
            
            # Validate floor type
            valid_floor_types = ["basement", "main_floor", "second_floor", "third_floor", "terrace"]
            if data["floor_type"] not in valid_floor_types:
                logger.warning(f"Unknown floor type '{data['floor_type']}', defaulting to 'main_floor'")
                data["floor_type"] = "main_floor"
            
            # Validate coordinates are within image bounds
            data["outer_boundary"] = self._validate_boundary(data["outer_boundary"], img_width, img_height, "outer")
            data["inner_boundaries"] = [
                self._validate_boundary(b, img_width, img_height, f"inner_{i}")
                for i, b in enumerate(data["inner_boundaries"])
            ]
            
            # Handle garage wall
            if data["has_garage"] and "garage_wall" in data and data["garage_wall"]:
                data["garage_wall"] = self._validate_boundary(data["garage_wall"], img_width, img_height, "garage")
            else:
                data["garage_wall"] = []
                data["has_garage"] = False
            
            return data
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response content: {content[:500]}")
            raise ValueError(f"AI returned invalid JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            raise
    
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
