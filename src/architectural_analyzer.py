import os
import json
import base64
import cv2
import numpy as np
from PIL import Image
from openai import OpenAI
import ezdxf
from typing import Dict, List, Tuple, Optional

# the newest OpenAI model is "gpt-5" which was released August 7, 2025.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
openai = None
if OPENAI_API_KEY:
    openai = OpenAI(api_key=OPENAI_API_KEY)
else:
    print("Warning: OPENAI_API_KEY not found. AI analysis will be disabled.")

class ArchitecturalAnalyzer:
    """
    AI-powered architectural drawing analyzer that can:
    1. Detect floor plans vs elevations
    2. Identify interior/exterior walls, garage spaces, doors, windows
    3. Generate proper layer names for AutoCAD
    4. Trace walls and create AutoCAD-compatible output
    """
    
    def __init__(self):
        self.layer_names = {
            'basement': {
                'interior': 'basement_interior_wall',
                'exterior': 'basement_exterior_wall'
            },
            'main_floor': {
                'interior': 'main_floor_interior_wall',
                'exterior': 'main_floor_exterior_wall',
                'garage': 'main_floor_garage_wall'
            },
            'second_floor': {
                'interior': 'second_floor_interior_wall',
                'exterior': 'second_floor_exterior_wall'
            },
            'doors': {
                'front': 'front_door_main',
                'back': 'back_door_main',
                'patio': 'patio_door_main',
                'garage': 'garage_door_main'
            },
            'windows': {
                'front': 'front_window_main',
                'back': 'back_window_main',
                'side': 'side_window_main',
                'door': 'door_window_main'
            }
        }
    
    def encode_image_to_base64(self, image_path: str) -> str:
        """Convert image file to base64 string for OpenAI API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    
    def analyze_drawing_type(self, image_path: str) -> Dict:
        """
        Determine if the drawing is a floor plan or elevation using AI
        """
        if not openai:
            raise Exception("OpenAI API key not configured. Please set up your OpenAI API key to use AI analysis features.")
        
        base64_image = self.encode_image_to_base64(image_path)
        
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert in architectural drawings. Analyze the image and determine if it's a floor plan (top-down view showing room layouts) or an elevation (side view showing the exterior facade of a building). Respond with JSON format: {'type': 'floor_plan' or 'elevation', 'confidence': 0.0-1.0, 'reasoning': 'explanation'}"
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this architectural drawing and determine if it's a floor plan or elevation view."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            timeout=20.0
        )
        
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response content from OpenAI API for drawing type analysis")
        result = json.loads(content)
        return result
    
    def analyze_floor_plan(self, image_path: str) -> Dict:
        """
        Analyze floor plan to detect walls, rooms, and spaces
        """
        if not openai:
            raise Exception("OpenAI API key not configured. Please set up your OpenAI API key to use AI analysis features.")
        
        base64_image = self.encode_image_to_base64(image_path)
        
        prompt = """
        You are an expert architectural analyst. Analyze this floor plan and identify:
        
        1. Floor type (basement, main_floor, second_floor, etc.)
        2. Interior walls (walls inside the house)
        3. Exterior walls (walls forming the house perimeter)
        4. Garage spaces (unheated but enclosed areas)
        5. Buffered/protected walls (walls adjacent to garage or other unheated spaces)
        6. Room types and their boundaries
        
        For each wall or space, provide coordinates where lines should be drawn to trace:
        - Interior walls
        - Exterior walls  
        - Garage-adjacent walls (different from full exterior)
        
        Respond in JSON format with:
        {
            "floor_type": "basement/main_floor/second_floor",
            "spaces": [
                {
                    "type": "interior/exterior/garage_adjacent",
                    "coordinates": [[x1,y1], [x2,y2], ...],
                    "layer_name": "suggested_layer_name"
                }
            ],
            "rooms": [
                {
                    "type": "living_room/kitchen/garage/etc",
                    "boundaries": [[x1,y1], [x2,y2], ...]
                }
            ]
        }
        """
        
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this floor plan drawing for wall detection and space identification."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            timeout=20.0
        )
        
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response content from OpenAI API for floor plan analysis")
        result = json.loads(content)
        return result
    
    def analyze_elevation(self, image_path: str) -> Dict:
        """
        Analyze elevation to detect doors, windows, and their dimensions
        """
        if not openai:
            raise Exception("OpenAI API key not configured. Please set up your OpenAI API key to use AI analysis features.")
        
        base64_image = self.encode_image_to_base64(image_path)
        
        prompt = """
        You are an expert architectural analyst. Analyze this elevation drawing and identify:
        
        1. Elevation direction (front, back, left, right)
        2. Doors (front door, patio door, etc.) with dimensions if visible
        3. Windows with their locations and sizes
        4. Door windows (windows within doors)
        
        For each element, provide:
        - Type (door/window)
        - Subtype (front_door, patio_door, regular_window, door_window)
        - Coordinates for drawing the element outline
        - Dimensions if visible (e.g., "36x80" for doors)
        - Floor level (main, basement, second, etc.)
        
        Respond in JSON format with:
        {
            "elevation_direction": "front/back/left/right",
            "elements": [
                {
                    "type": "door/window",
                    "subtype": "front_door/patio_door/window/door_window",
                    "coordinates": [[x1,y1], [x2,y2], [x3,y3], [x4,y4]],
                    "dimensions": "36x80" or null,
                    "floor_level": "main/basement/second",
                    "layer_name": "suggested_layer_name"
                }
            ]
        }
        """
        
        response = openai.chat.completions.create(
            model="gpt-5",
            messages=[
                {
                    "role": "system",
                    "content": prompt
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Analyze this elevation drawing for door and window detection."
                        },
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
                        }
                    ]
                }
            ],
            response_format={"type": "json_object"},
            timeout=20.0
        )
        
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("Empty response content from OpenAI API for elevation analysis")
        result = json.loads(content)
        return result
    
    def process_drawing(self, image_path: str) -> Dict:
        """
        Main processing function that analyzes any architectural drawing
        and returns comprehensive analysis with AutoCAD instructions
        """
        # First determine drawing type
        drawing_type_analysis = self.analyze_drawing_type(image_path)
        
        analysis_type = drawing_type_analysis.get('type')
        if analysis_type == 'floor_plan':
            analysis = self.analyze_floor_plan(image_path)
            analysis['drawing_type'] = 'floor_plan'
        else:
            analysis = self.analyze_elevation(image_path)
            analysis['drawing_type'] = 'elevation'
        
        analysis['type_analysis'] = drawing_type_analysis
        
        return analysis
    
    def analyze_geometric_data(self, geometric_data: Dict, spatial_analysis: Dict) -> Dict:
        """
        Analyze geometric data using AI to enhance wall classification and spatial understanding
        """
        if not openai:
            raise Exception("OpenAI API key not configured. Please set up your OpenAI API key to use AI analysis features.")

        try:
            print("Starting OpenAI API call for geometric analysis...")
            # Prepare geometric data summary for AI analysis
            analysis_prompt = self._create_geometric_analysis_prompt(geometric_data, spatial_analysis)
            
            # Add shorter timeout to prevent hanging on large files
            response = openai.chat.completions.create(
                model="gpt-5",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert architectural analyst specializing in CAD drawing interpretation. 
                        Analyze the geometric data from a DXF file to classify walls, spaces, and architectural elements.
                        Focus on spatial relationships, connectivity patterns, and architectural logic."""
                    },
                    {
                        "role": "user",
                        "content": analysis_prompt
                    }
                ],
                response_format={"type": "json_object"},
                timeout=10.0  # Reduced to 10 second timeout
            )
            
            content = response.choices[0].message.content
            if content is None:
                raise ValueError("Empty response content from OpenAI API for geometric analysis")
            ai_analysis = json.loads(content)
            
            # Enhance the spatial analysis with AI insights
            enhanced_analysis = self._merge_ai_with_geometric_analysis(ai_analysis, spatial_analysis)
            
            print("AI-enhanced geometric analysis completed")
            return enhanced_analysis

        except Exception as e:
            error_msg = f"AI analysis failed: {str(e)}"
            print(f"Error in AI geometric analysis: {e}")
            raise Exception(error_msg)

    def _create_geometric_analysis_prompt(self, geometric_data: Dict, spatial_analysis: Dict) -> str:
        """Create a prompt for AI analysis of geometric data"""
        
        # Summarize the geometric data
        entities_summary = geometric_data.get('entities_extracted', {})
        wall_groups = spatial_analysis.get('wall_groups_found', 0)
        building_bounds = spatial_analysis.get('building_bounds', {})
        
        prompt = f"""
        Analyze this architectural DXF file geometric data:

        GEOMETRIC ENTITIES FOUND:
        - Lines: {entities_summary.get('lines', 0)}
        - Polylines: {entities_summary.get('polylines', 0)}
        - Arcs: {entities_summary.get('arcs', 0)}
        - Circles: {entities_summary.get('circles', 0)}

        SPATIAL ANALYSIS:
        - Wall groups identified: {wall_groups}
        - Building dimensions: {building_bounds.get('width', 'unknown')} x {building_bounds.get('height', 'unknown')} units
        - Building bounds: {building_bounds}

        WALL GROUP DETAILS:
        """
        
        # Add details about each wall group from spatial analysis
        if 'wall_groups' in spatial_analysis:
            for i, group in enumerate(spatial_analysis['wall_groups'][:5]):  # Limit to first 5 for prompt size
                prompt += f"""
        Wall Group {i+1}:
        - Total length: {group.get('total_length', 0):.1f} units
        - Segment count: {len(group.get('segments', []))}
        - Layers involved: {list(group.get('layers', set()))}
        - Bounds: {group.get('bounds', {})}
        """

        prompt += """

        ANALYSIS REQUIRED:
        Based on this geometric data, provide architectural classification:

        1. For each wall group, determine:
           - Type: 'exterior', 'interior', or 'garage_adjacent'
           - Reasoning based on position, connectivity, and architectural logic
           - Confidence level (0.0-1.0)

        2. Identify potential room spaces and their characteristics

        3. Suggest appropriate layer naming following these patterns:
           - Exterior walls: '[floor]_exterior_wall_[n]' 
           - Interior walls: '[floor]_interior_wall_[n]'
           - Garage walls: '[floor]_garage_wall_[n]'

        Respond in JSON format:
        {
            "wall_classifications": [
                {
                    "group_index": 0,
                    "type": "exterior/interior/garage_adjacent",
                    "confidence": 0.0-1.0,
                    "reasoning": "explanation",
                    "suggested_layer": "layer_name"
                }
            ],
            "spatial_insights": {
                "building_type": "residential/commercial/mixed",
                "floor_count_estimate": 1-3,
                "has_garage": true/false,
                "architectural_style": "description"
            },
            "recommendations": [
                "specific suggestions for layer organization or analysis improvements"
            ]
        }
        """
        
        return prompt

    def _merge_ai_with_geometric_analysis(self, ai_analysis: Dict, spatial_analysis: Dict) -> Dict:
        """Merge AI insights with geometric analysis results"""
        
        enhanced_analysis = spatial_analysis.copy()
        enhanced_analysis['ai_insights'] = ai_analysis
        
        # Apply AI classifications to wall groups
        wall_classifications = ai_analysis.get('wall_classifications', [])
        
        if 'wall_groups' in enhanced_analysis:
            for classification in wall_classifications:
                group_index = classification.get('group_index', 0)
                if group_index < len(enhanced_analysis['wall_groups']):
                    group = enhanced_analysis['wall_groups'][group_index]
                    group['ai_classification'] = {
                        'type': classification.get('type', 'interior'),
                        'confidence': classification.get('confidence', 0.5),
                        'reasoning': classification.get('reasoning', ''),
                        'suggested_layer': classification.get('suggested_layer', '')
                    }

        # Add spatial insights
        enhanced_analysis['spatial_insights'] = ai_analysis.get('spatial_insights', {})
        enhanced_analysis['ai_recommendations'] = ai_analysis.get('recommendations', [])
        
        return enhanced_analysis

    def _create_basic_analysis(self, geometric_data: Dict, spatial_analysis: Dict) -> Dict:
        """Create basic analysis when AI is not available"""
        
        basic_analysis = spatial_analysis.copy()
        basic_analysis['ai_insights'] = {
            "note": "AI analysis not available - using geometric analysis only",
            "wall_classifications": [],
            "spatial_insights": {
                "building_type": "unknown",
                "analysis_method": "geometric_only"
            }
        }
        
        return basic_analysis
    
    def generate_autocad_commands(self, analysis: Dict) -> List[str]:
        """
        Generate AutoCAD command sequence based on analysis results
        """
        commands = []
        
        if analysis['drawing_type'] == 'floor_plan':
            # Generate commands for wall tracing
            for space in analysis.get('spaces', []):
                layer_name = space['layer_name']
                coords = space['coordinates']
                
                # Create layer
                commands.append(f"-LAYER M {layer_name}")
                
                # Draw polyline for wall tracing
                if len(coords) > 1:
                    polyline_cmd = "PLINE "
                    for coord in coords:
                        polyline_cmd += f"{coord[0]},{coord[1]} "
                    polyline_cmd += "C"  # Close polyline
                    commands.append(polyline_cmd)
        
        elif analysis['drawing_type'] == 'elevation':
            # Generate commands for doors and windows
            for element in analysis.get('elements', []):
                layer_name = element['layer_name']
                coords = element['coordinates']
                
                # Create layer
                commands.append(f"-LAYER M {layer_name}")
                
                # Draw rectangle for door/window
                if len(coords) >= 4:
                    rect_cmd = f"RECTANG {coords[0][0]},{coords[0][1]} {coords[2][0]},{coords[2][1]}"
                    commands.append(rect_cmd)
        
        return commands

def main():
    """
    Example usage of the ArchitecturalAnalyzer
    """
    analyzer = ArchitecturalAnalyzer()
    
    # Example usage - you would replace this with actual file paths
    print("Architectural Drawing Analyzer initialized")
    print("Ready to process AutoCAD drawings and PDFs")
    print("\nSupported operations:")
    print("1. Detect floor plans vs elevations")
    print("2. Trace interior/exterior walls")
    print("3. Identify garage and buffered spaces")
    print("4. Detect doors and windows in elevations")
    print("5. Generate proper AutoCAD layer names")
    print("6. Create AutoCAD command sequences")

if __name__ == "__main__":
    main()