import ezdxf
import os
from typing import List, Dict, Tuple, Optional, Any, Union
import cv2
import numpy as np
from PIL import Image
import math
from collections import defaultdict

class AutoCADIntegration:
    """
    Handles AutoCAD file operations and layer management
    """
    
    def __init__(self):
        self.current_doc = None
        self.modelspace = None
    
    def load_dxf_file(self, file_path: str) -> bool:
        """Load an existing DXF file"""
        try:
            # Type-safe access to ezdxf.readfile
            readfile_func = getattr(ezdxf, 'readfile', None)
            if readfile_func is None:
                print("Error: ezdxf.readfile not available")
                return False
            self.current_doc = readfile_func(file_path)
            self.modelspace = self.current_doc.modelspace()
            print(f"Successfully loaded DXF file: {file_path}")
            return True
        except Exception as e:
            print(f"Error loading DXF file: {e}")
            return False
    
    def create_new_dxf(self) -> bool:
        """Create a new DXF document"""
        try:
            # Type-safe access to ezdxf.new
            new_func = getattr(ezdxf, 'new', None)
            if new_func is None:
                print("Error: ezdxf.new not available")
                return False
            self.current_doc = new_func('R2010')
            self.modelspace = self.current_doc.modelspace()
            print("Created new DXF document")
            return True
        except Exception as e:
            print(f"Error creating new DXF document: {e}")
            return False
    
    def create_layer(self, layer_name: str, color: int = 7, linetype: str = 'CONTINUOUS'):
        """Create a new layer in the DXF file"""
        if self.current_doc is None:
            print("No DXF document loaded")
            return False
        
        try:
            layers = self.current_doc.layers
            if layer_name not in layers:
                layer = layers.new(name=layer_name)
                # Type-safe attribute setting
                if hasattr(layer, 'color'):
                    layer.color = color
                if hasattr(layer.dxf, 'linetype'):
                    layer.dxf.linetype = linetype
                print(f"Created layer: {layer_name}")
            else:
                print(f"Layer {layer_name} already exists")
            return True
        except Exception as e:
            print(f"Error creating layer {layer_name}: {e}")
            return False
    
    def draw_polyline(self, coordinates: List[Tuple[float, float]], layer_name: str = "0"):
        """Draw a polyline on the specified layer"""
        if self.current_doc is None or self.modelspace is None:
            print("No DXF document loaded")
            return False
        
        try:
            # Convert 2D coordinates to 3D (adding z=0)
            points_3d = [(x, y, 0) for x, y in coordinates]
            
            polyline = self.modelspace.add_lwpolyline(points_3d)
            polyline.dxf.layer = layer_name
            print(f"Drew polyline with {len(coordinates)} points on layer {layer_name}")
            return True
        except Exception as e:
            print(f"Error drawing polyline: {e}")
            return False
    
    def draw_rectangle(self, point1: Tuple[float, float], point2: Tuple[float, float], layer_name: str = "0"):
        """Draw a rectangle between two points"""
        if self.current_doc is None or self.modelspace is None:
            print("No DXF document loaded")
            return False
        
        try:
            x1, y1 = point1
            x2, y2 = point2
            
            # Create rectangle coordinates
            rectangle_points = [
                (x1, y1),
                (x2, y1),
                (x2, y2),
                (x1, y2),
                (x1, y1)  # Close the rectangle
            ]
            
            return self.draw_polyline(rectangle_points, layer_name)
        except Exception as e:
            print(f"Error drawing rectangle: {e}")
            return False
    
    def draw_line(self, start_point: Tuple[float, float], end_point: Tuple[float, float], layer_name: str = "0"):
        """Draw a single line"""
        if self.current_doc is None or self.modelspace is None:
            print("No DXF document loaded")
            return False
        
        try:
            start_3d = (start_point[0], start_point[1], 0)
            end_3d = (end_point[0], end_point[1], 0)
            
            line = self.modelspace.add_line(start_3d, end_3d)
            line.dxf.layer = layer_name
            print(f"Drew line from {start_point} to {end_point} on layer {layer_name}")
            return True
        except Exception as e:
            print(f"Error drawing line: {e}")
            return False
    
    def save_dxf(self, output_path: str):
        """Save the current DXF document"""
        if self.current_doc is None:
            print("No DXF document to save")
            return False
        
        try:
            self.current_doc.saveas(output_path)
            print(f"Saved DXF file to: {output_path}")
            return True
        except Exception as e:
            print(f"Error saving DXF file: {e}")
            return False
    
    def list_layers(self):
        """List all layers in the current document"""
        if self.current_doc is None:
            print("No DXF document loaded")
            return []
        
        layers = []
        for layer in self.current_doc.layers:
            layers.append({
                'name': layer.dxf.name,
                'color': layer.dxf.color,
                'linetype': layer.dxf.linetype
            })
        
        return layers
    
    def execute_autocad_commands(self, analysis_result: Dict):
        """
        Execute AutoCAD drawing commands based on AI analysis results
        """
        if self.current_doc is None:
            print("No DXF document loaded. Creating new document.")
            self.create_new_dxf()
        
        commands_executed = 0
        
        if analysis_result['drawing_type'] == 'floor_plan':
            print("Processing floor plan analysis...")
            
            # Process spaces (walls)
            for space in analysis_result.get('spaces', []):
                layer_name = space['layer_name']
                coordinates = space['coordinates']
                
                # Create layer
                color = self.get_layer_color(space['type'])
                self.create_layer(layer_name, color)
                
                # Draw the wall trace
                if len(coordinates) > 1:
                    self.draw_polyline(coordinates, layer_name)
                    commands_executed += 1
        
        elif analysis_result['drawing_type'] == 'elevation':
            print("Processing elevation analysis...")
            
            # Process doors and windows
            for element in analysis_result.get('elements', []):
                layer_name = element['layer_name']
                coordinates = element['coordinates']
                
                # Create layer
                color = self.get_layer_color(element['type'])
                self.create_layer(layer_name, color)
                
                # Draw rectangle for door/window
                if len(coordinates) >= 4:
                    point1 = coordinates[0]
                    point2 = coordinates[2]  # Diagonal point
                    self.draw_rectangle(point1, point2, layer_name)
                    commands_executed += 1
        
        print(f"Executed {commands_executed} drawing commands")
        return commands_executed
    
    def get_layer_color(self, element_type: str) -> int:
        """Get appropriate color for different element types"""
        color_map = {
            'interior': 1,      # Red
            'exterior': 2,      # Yellow
            'garage_adjacent': 3, # Green
            'door': 4,          # Cyan
            'window': 5,        # Blue
            'garage': 6         # Magenta
        }
        return color_map.get(element_type, 7)  # Default white

    def extract_geometric_entities(self) -> Dict[str, List]:
        """
        Extract all geometric entities from the loaded DXF document
        Returns a dictionary with entity types and their data
        """
        if self.current_doc is None or self.modelspace is None:
            print("No DXF document loaded")
            return {}

        entities = {
            'lines': [],
            'polylines': [],
            'lwpolylines': [],
            'arcs': [],
            'circles': [],
            'splines': [],
            'blocks': [],
            'text': []
        }

        try:
            for entity in self.modelspace:
                entity_type = entity.dxftype()
                
                if entity_type == 'LINE':
                    entities['lines'].append({
                        'start': (entity.dxf.start.x, entity.dxf.start.y),
                        'end': (entity.dxf.end.x, entity.dxf.end.y),
                        'layer': entity.dxf.layer,
                        'length': math.sqrt((entity.dxf.end.x - entity.dxf.start.x)**2 + 
                                          (entity.dxf.end.y - entity.dxf.start.y)**2)
                    })
                
                elif entity_type == 'LWPOLYLINE':
                    # Type-safe access to entity methods and attributes
                    get_points_method = getattr(entity, 'get_points', None)
                    if get_points_method is not None:
                        try:
                            points_data = get_points_method('xy')
                            points = [(point[0], point[1]) for point in points_data]
                        except (IndexError, TypeError):
                            # Fallback to vertices method
                            vertices_method = getattr(entity, 'vertices', None)
                            if vertices_method is not None:
                                points = list(vertices_method())
                            else:
                                points = []
                    else:
                        points = []
                    
                    # Type-safe access to closed attribute
                    is_closed = getattr(entity, 'closed', False)
                    
                    entities['lwpolylines'].append({
                        'points': points,
                        'layer': getattr(entity.dxf, 'layer', '0'),
                        'closed': is_closed,
                        'area': self._calculate_polygon_area(points) if is_closed else 0
                    })
                
                elif entity_type == 'POLYLINE':
                    # Type-safe access to vertices
                    vertices_attr = getattr(entity, 'vertices', None)
                    if vertices_attr is not None:
                        try:
                            points = []
                            for vertex in vertices_attr:
                                if hasattr(vertex, 'dxf') and hasattr(vertex.dxf, 'location'):
                                    location = vertex.dxf.location
                                    if hasattr(location, 'x') and hasattr(location, 'y'):
                                        points.append((location.x, location.y))
                        except (AttributeError, TypeError):
                            points = []
                    else:
                        points = []
                    
                    # Type-safe access to is_closed method
                    is_closed_method = getattr(entity, 'is_closed', None)
                    if callable(is_closed_method):
                        try:
                            is_closed = is_closed_method()
                        except Exception:
                            is_closed = False
                    else:
                        is_closed = False
                    
                    entities['polylines'].append({
                        'points': points,
                        'layer': getattr(entity.dxf, 'layer', '0'),
                        'closed': is_closed,
                        'area': self._calculate_polygon_area(points) if is_closed else 0
                    })
                
                elif entity_type == 'ARC':
                    entities['arcs'].append({
                        'center': (entity.dxf.center.x, entity.dxf.center.y),
                        'radius': entity.dxf.radius,
                        'start_angle': entity.dxf.start_angle,
                        'end_angle': entity.dxf.end_angle,
                        'layer': entity.dxf.layer
                    })
                
                elif entity_type == 'CIRCLE':
                    entities['circles'].append({
                        'center': (entity.dxf.center.x, entity.dxf.center.y),
                        'radius': entity.dxf.radius,
                        'layer': entity.dxf.layer,
                        'area': math.pi * entity.dxf.radius**2
                    })

            print(f"Extracted {len(entities['lines'])} lines, {len(entities['lwpolylines'])} lwpolylines, "
                  f"{len(entities['polylines'])} polylines, {len(entities['arcs'])} arcs, "
                  f"{len(entities['circles'])} circles")
            
            return entities

        except Exception as e:
            print(f"Error extracting geometric entities: {e}")
            return {}

    def _calculate_polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """Calculate the area of a polygon using the shoelace formula"""
        if len(points) < 3:
            return 0
        
        area = 0
        n = len(points)
        for i in range(n):
            j = (i + 1) % n
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        return abs(area) / 2

    def analyze_spatial_relationships(self, entities: Dict[str, List]) -> Dict:
        """
        Analyze spatial relationships between entities to identify wall patterns
        """
        analysis = {
            'potential_walls': [],
            'enclosed_areas': [],
            'wall_groups': [],
            'building_bounds': None
        }

        try:
            # Combine all linear entities (lines and polylines) for wall analysis
            wall_segments = []
            
            # Add lines as wall segments
            for line in entities['lines']:
                wall_segments.append({
                    'start': line['start'],
                    'end': line['end'],
                    'layer': line['layer'],
                    'length': line['length'],
                    'type': 'line'
                })
            
            # Add polyline segments
            for polyline in entities['lwpolylines'] + entities['polylines']:
                points = polyline['points']
                for i in range(len(points) - 1):
                    start, end = points[i], points[i + 1]
                    length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                    wall_segments.append({
                        'start': start,
                        'end': end,
                        'layer': polyline['layer'],
                        'length': length,
                        'type': 'polyline_segment'
                    })

            # Group wall segments by connectivity and orientation
            wall_groups = self._group_connected_walls(wall_segments)
            analysis['wall_groups'] = wall_groups

            # Find building bounds
            all_points = []
            for segment in wall_segments:
                all_points.extend([segment['start'], segment['end']])
            
            if all_points:
                min_x = min(p[0] for p in all_points)
                max_x = max(p[0] for p in all_points)
                min_y = min(p[1] for p in all_points)
                max_y = max(p[1] for p in all_points)
                analysis['building_bounds'] = {
                    'min_x': min_x, 'max_x': max_x, 
                    'min_y': min_y, 'max_y': max_y,
                    'width': max_x - min_x,
                    'height': max_y - min_y
                }

            # Identify enclosed areas from closed polylines
            for polyline in entities['lwpolylines'] + entities['polylines']:
                if polyline.get('closed', False) and polyline.get('area', 0) > 0:
                    analysis['enclosed_areas'].append({
                        'points': polyline['points'],
                        'area': polyline['area'],
                        'layer': polyline['layer']
                    })

            print(f"Found {len(wall_groups)} wall groups, {len(analysis['enclosed_areas'])} enclosed areas")
            return analysis

        except Exception as e:
            print(f"Error analyzing spatial relationships: {e}")
            return analysis

    def _group_connected_walls(self, wall_segments: List[Dict]) -> List[Dict]:
        """Group wall segments that are connected to each other (optimized with spatial indexing)"""
        if not wall_segments:
            return []

        # Use spatial indexing for large datasets
        if len(wall_segments) > 2000:
            print(f"Large dataset detected ({len(wall_segments)} segments). Using spatial indexing optimization.")
            return self._group_connected_walls_spatial(wall_segments)

        groups = []
        used_segments = set()
        tolerance = 1.0
        max_iterations = len(wall_segments) * 2  # More reasonable iteration limit

        for i, segment in enumerate(wall_segments):
            if i in used_segments:
                continue

            # Start a new group with this segment
            group = {
                'segments': [segment],
                'total_length': segment['length'],
                'layers': {segment['layer']},
                'bounds': self._get_segment_bounds(segment)
            }
            used_segments.add(i)

            # Find all segments connected to this group
            found_connection = True
            iterations = 0
            while found_connection and iterations < max_iterations:
                found_connection = False
                iterations += 1
                
                for j, other_segment in enumerate(wall_segments):
                    if j in used_segments:
                        continue

                    # Check if this segment connects to any segment in the group
                    if self._segments_connected(group['segments'], other_segment, tolerance):
                        group['segments'].append(other_segment)
                        group['total_length'] += other_segment['length']
                        group['layers'].add(other_segment['layer'])
                        group['bounds'] = self._update_bounds(group['bounds'], other_segment)
                        used_segments.add(j)
                        found_connection = True
                        break  # Process one connection per iteration

            groups.append(group)

        print(f"Grouped {len(wall_segments)} segments into {len(groups)} wall groups")
        return groups

    def _segments_connected(self, group_segments: List[Dict], segment: Dict, tolerance: float) -> bool:
        """Check if a segment is connected to any segment in a group"""
        seg_start, seg_end = segment['start'], segment['end']
        
        for group_seg in group_segments:
            group_start, group_end = group_seg['start'], group_seg['end']
            
            # Check if any endpoints are close enough
            distances = [
                math.sqrt((seg_start[0] - group_start[0])**2 + (seg_start[1] - group_start[1])**2),
                math.sqrt((seg_start[0] - group_end[0])**2 + (seg_start[1] - group_end[1])**2),
                math.sqrt((seg_end[0] - group_start[0])**2 + (seg_end[1] - group_start[1])**2),
                math.sqrt((seg_end[0] - group_end[0])**2 + (seg_end[1] - group_end[1])**2)
            ]
            
            if min(distances) <= tolerance:
                return True
        
        return False

    def _segments_connected_simple(self, group_segments: List[Dict], segment: Dict, tolerance: float) -> bool:
        """Simplified version for performance - only check connection to most recent segment in group"""
        if not group_segments:
            return False
            
        # Only check connection to the last added segment for better performance
        last_segment = group_segments[-1]
        seg_start, seg_end = segment['start'], segment['end']
        group_start, group_end = last_segment['start'], last_segment['end']
        
        # Check if any endpoints are close enough
        distances = [
            math.sqrt((seg_start[0] - group_start[0])**2 + (seg_start[1] - group_start[1])**2),
            math.sqrt((seg_start[0] - group_end[0])**2 + (seg_start[1] - group_end[1])**2),
            math.sqrt((seg_end[0] - group_start[0])**2 + (seg_end[1] - group_start[1])**2),
            math.sqrt((seg_end[0] - group_end[0])**2 + (seg_end[1] - group_end[1])**2)
        ]
        
        return min(distances) <= tolerance

    def _group_connected_walls_spatial(self, wall_segments: List[Dict]) -> List[Dict]:
        """Optimized wall grouping using spatial indexing for large datasets"""
        if not wall_segments:
            return []

        # Create spatial index for faster lookups
        tolerance = 1.0
        grid_size = 10.0  # Grid cell size for spatial indexing
        spatial_grid = defaultdict(list)

        # Index all segments by their spatial location
        for i, segment in enumerate(wall_segments):
            start, end = segment['start'], segment['end']
            points = [start, end]
            
            for point in points:
                grid_x = int(point[0] // grid_size)
                grid_y = int(point[1] // grid_size)
                # Add to multiple grid cells to handle tolerance
                for dx in [-1, 0, 1]:
                    for dy in [-1, 0, 1]:
                        spatial_grid[(grid_x + dx, grid_y + dy)].append(i)

        groups = []
        used_segments = set()
        
        for i, segment in enumerate(wall_segments):
            if i in used_segments:
                continue

            # Start a new group with this segment
            group = {
                'segments': [segment],
                'total_length': segment['length'],
                'layers': {segment['layer']},
                'bounds': self._get_segment_bounds(segment)
            }
            used_segments.add(i)

            # Use BFS to find connected segments
            to_process = [i]
            
            while to_process:
                current_idx = to_process.pop(0)
                current_segment = wall_segments[current_idx]
                
                # Find potential connections using spatial grid
                candidates = set()
                start, end = current_segment['start'], current_segment['end']
                for point in [start, end]:
                    grid_x = int(point[0] // grid_size)
                    grid_y = int(point[1] // grid_size)
                    for dx in [-1, 0, 1]:
                        for dy in [-1, 0, 1]:
                            candidates.update(spatial_grid.get((grid_x + dx, grid_y + dy), []))

                # Check actual connections
                for candidate_idx in candidates:
                    if candidate_idx in used_segments:
                        continue
                    
                    candidate_segment = wall_segments[candidate_idx]
                    if self._segments_directly_connected(current_segment, candidate_segment, tolerance):
                        group['segments'].append(candidate_segment)
                        group['total_length'] += candidate_segment['length']
                        group['layers'].add(candidate_segment['layer'])
                        group['bounds'] = self._update_bounds(group['bounds'], candidate_segment)
                        used_segments.add(candidate_idx)
                        to_process.append(candidate_idx)

            groups.append(group)

        print(f"Spatial indexing: Grouped {len(wall_segments)} segments into {len(groups)} wall groups")
        return groups

    def _segments_directly_connected(self, seg1: Dict, seg2: Dict, tolerance: float) -> bool:
        """Check if two segments are directly connected (optimized)"""
        seg1_start, seg1_end = seg1['start'], seg1['end']
        seg2_start, seg2_end = seg2['start'], seg2['end']
        
        # Check if any endpoints are close enough
        distances = [
            math.sqrt((seg1_start[0] - seg2_start[0])**2 + (seg1_start[1] - seg2_start[1])**2),
            math.sqrt((seg1_start[0] - seg2_end[0])**2 + (seg1_start[1] - seg2_end[1])**2),
            math.sqrt((seg1_end[0] - seg2_start[0])**2 + (seg1_end[1] - seg2_start[1])**2),
            math.sqrt((seg1_end[0] - seg2_end[0])**2 + (seg1_end[1] - seg2_end[1])**2)
        ]
        
        return min(distances) <= tolerance

    def _get_segment_bounds(self, segment: Dict) -> Dict:
        """Get bounding box for a segment"""
        start, end = segment['start'], segment['end']
        return {
            'min_x': min(start[0], end[0]),
            'max_x': max(start[0], end[0]),
            'min_y': min(start[1], end[1]),
            'max_y': max(start[1], end[1])
        }

    def _update_bounds(self, bounds: Dict, segment: Dict) -> Dict:
        """Update bounds to include a new segment"""
        seg_bounds = self._get_segment_bounds(segment)
        return {
            'min_x': min(bounds['min_x'], seg_bounds['min_x']),
            'max_x': max(bounds['max_x'], seg_bounds['max_x']),
            'min_y': min(bounds['min_y'], seg_bounds['min_y']),
            'max_y': max(bounds['max_y'], seg_bounds['max_y'])
        }

    def classify_wall_types(self, analysis: Dict) -> List[Dict]:
        """
        Classify wall groups as interior, exterior, or garage-adjacent based on spatial analysis
        """
        classified_walls = []
        
        if not analysis.get('wall_groups') or not analysis.get('building_bounds'):
            return classified_walls

        building_bounds = analysis['building_bounds']
        perimeter_tolerance = 5.0  # Distance tolerance for perimeter detection

        try:
            for group in analysis['wall_groups']:
                group_bounds = group['bounds']
                
                # Determine wall type based on position and characteristics
                wall_type = 'interior'  # Default
                
                # Check if this wall group is on the building perimeter
                is_perimeter = (
                    abs(group_bounds['min_x'] - building_bounds['min_x']) <= perimeter_tolerance or
                    abs(group_bounds['max_x'] - building_bounds['max_x']) <= perimeter_tolerance or
                    abs(group_bounds['min_y'] - building_bounds['min_y']) <= perimeter_tolerance or
                    abs(group_bounds['max_y'] - building_bounds['max_y']) <= perimeter_tolerance
                )
                
                if is_perimeter:
                    wall_type = 'exterior'

                # Check for garage walls based on layer names or area characteristics
                layer_names = [layer.lower() for layer in group['layers']]
                if any('garage' in layer for layer in layer_names):
                    wall_type = 'garage_adjacent'

                # Generate coordinates for wall tracing
                coordinates = self._generate_wall_trace_coordinates(group)

                classified_walls.append({
                    'type': wall_type,
                    'coordinates': coordinates,
                    'total_length': group['total_length'],
                    'layer_suggestions': list(group['layers']),
                    'bounds': group_bounds,
                    'segment_count': len(group['segments'])
                })

            print(f"Classified {len(classified_walls)} wall groups")
            return classified_walls

        except Exception as e:
            print(f"Error classifying wall types: {e}")
            return classified_walls

    def _generate_wall_trace_coordinates(self, wall_group: Dict) -> List[Tuple[float, float]]:
        """
        Generate coordinate sequence for tracing a wall group
        """
        segments = wall_group['segments']
        if not segments:
            return []

        # For simple cases, just return the endpoints of all segments
        # In a more sophisticated implementation, this would create optimized trace paths
        coordinates = []
        
        for segment in segments:
            coordinates.extend([segment['start'], segment['end']])

        # Remove duplicate consecutive points
        unique_coords = []
        for coord in coordinates:
            if not unique_coords or coord != unique_coords[-1]:
                unique_coords.append(coord)

        return unique_coords

    def analyze_dxf_geometry(self, analyzer=None) -> Dict:
        """
        Main method to analyze DXF geometry and return wall classifications
        This replaces the hardcoded analysis in the original code
        """
        print("Starting DXF geometric analysis...")
        
        # Step 1: Extract all geometric entities
        entities = self.extract_geometric_entities()
        if not entities:
            print("No geometric entities found")
            return self._create_fallback_analysis()

        # Step 2: Analyze spatial relationships
        spatial_analysis = self.analyze_spatial_relationships(entities)
        
        # Step 3: Use AI to enhance analysis if analyzer is provided and API key is available
        if analyzer:
            print("Checking AI analysis availability...")
            try:
                # Check if OpenAI API key is available
                import os
                if os.environ.get("OPENAI_API_KEY"):
                    print("Integrating AI analysis with geometric data...")
                    # Prepare metadata for AI analysis
                    analysis_metadata = {
                        'entities_extracted': {
                            'lines': len(entities.get('lines', [])),
                            'polylines': len(entities.get('lwpolylines', [])) + len(entities.get('polylines', [])),
                            'arcs': len(entities.get('arcs', [])),
                            'circles': len(entities.get('circles', []))
                        },
                        'wall_groups_found': len(spatial_analysis.get('wall_groups', [])),
                        'building_bounds': spatial_analysis.get('building_bounds')
                    }
                    
                    # Use AI to enhance the spatial analysis with timeout handling
                    import signal
                    
                    def timeout_handler(signum, frame):
                        raise TimeoutError("AI analysis timed out")
                    
                    # Set alarm for 15 seconds
                    signal.signal(signal.SIGALRM, timeout_handler)
                    signal.alarm(15)
                    
                    try:
                        enhanced_analysis = analyzer.analyze_geometric_data(analysis_metadata, spatial_analysis)
                        spatial_analysis = enhanced_analysis
                        print("AI analysis integration completed")
                    except TimeoutError:
                        print("AI analysis timed out. Proceeding with geometric-only analysis.")
                    finally:
                        signal.alarm(0)  # Cancel alarm
                else:
                    print("OpenAI API key not configured. Proceeding with geometric-only analysis.")
                
            except Exception as e:
                print(f"AI analysis failed: {str(e)}. Proceeding with geometric-only analysis.")
                # Continue with geometric analysis instead of failing completely
        
        # Step 4: Classify wall types (potentially enhanced by AI)
        classified_walls = self.classify_wall_types_enhanced(spatial_analysis)
        
        # Step 5: Format result in the expected structure
        result = {
            'drawing_type': 'floor_plan',
            'spaces': [],
            'elements': [],
            'analysis_metadata': {
                'entities_extracted': {
                    'lines': len(entities.get('lines', [])),
                    'polylines': len(entities.get('lwpolylines', [])) + len(entities.get('polylines', [])),
                    'arcs': len(entities.get('arcs', [])),
                    'circles': len(entities.get('circles', []))
                },
                'wall_groups_found': len(classified_walls),
                'building_bounds': spatial_analysis.get('building_bounds'),
                'ai_enhanced': analyzer is not None,
                'ai_insights': spatial_analysis.get('ai_insights', {}),
                'ai_recommendations': spatial_analysis.get('ai_recommendations', [])
            }
        }

        # Convert classified walls to the expected format
        for i, wall in enumerate(classified_walls):
            layer_name = self._generate_layer_name_enhanced(wall, i)
            
            result['spaces'].append({
                'type': wall['type'],
                'coordinates': wall['coordinates'],
                'layer_name': layer_name,
                'metadata': {
                    'total_length': wall['total_length'],
                    'segment_count': wall['segment_count'],
                    'bounds': wall['bounds'],
                    'ai_classification': wall.get('ai_classification', {}),
                    'confidence': wall.get('ai_classification', {}).get('confidence', 0.5)
                }
            })

        print(f"Analysis complete: found {len(result['spaces'])} wall spaces")
        return result

    def classify_wall_types_enhanced(self, analysis: Dict) -> List[Dict]:
        """
        Enhanced wall classification that uses AI insights when available
        """
        classified_walls = []
        
        if not analysis.get('wall_groups') or not analysis.get('building_bounds'):
            return classified_walls

        building_bounds = analysis['building_bounds']
        perimeter_tolerance = 5.0
        ai_insights = analysis.get('ai_insights', {})
        wall_classifications = ai_insights.get('wall_classifications', [])

        try:
            for i, group in enumerate(analysis['wall_groups']):
                group_bounds = group['bounds']
                
                # Start with geometric classification
                wall_type = 'interior'  # Default
                
                # Check if this wall group is on the building perimeter
                is_perimeter = (
                    abs(group_bounds['min_x'] - building_bounds['min_x']) <= perimeter_tolerance or
                    abs(group_bounds['max_x'] - building_bounds['max_x']) <= perimeter_tolerance or
                    abs(group_bounds['min_y'] - building_bounds['min_y']) <= perimeter_tolerance or
                    abs(group_bounds['max_y'] - building_bounds['max_y']) <= perimeter_tolerance
                )
                
                if is_perimeter:
                    wall_type = 'exterior'

                # Check for garage walls based on layer names
                layer_names = [layer.lower() for layer in group['layers']]
                if any('garage' in layer for layer in layer_names):
                    wall_type = 'garage_adjacent'

                # Override with AI classification if available and confident
                ai_classification = None
                for classification in wall_classifications:
                    if classification.get('group_index') == i:
                        ai_classification = classification
                        break
                
                if ai_classification and ai_classification.get('confidence', 0) > 0.7:
                    wall_type = ai_classification.get('type', wall_type)
                    print(f"AI override: Wall group {i} classified as {wall_type} "
                          f"(confidence: {ai_classification.get('confidence', 0):.2f})")

                # Generate coordinates for wall tracing
                coordinates = self._generate_wall_trace_coordinates(group)

                wall_data = {
                    'type': wall_type,
                    'coordinates': coordinates,
                    'total_length': group['total_length'],
                    'layer_suggestions': list(group['layers']),
                    'bounds': group_bounds,
                    'segment_count': len(group['segments'])
                }
                
                # Add AI classification data if available
                if ai_classification:
                    wall_data['ai_classification'] = ai_classification

                classified_walls.append(wall_data)

            print(f"Enhanced classification complete: {len(classified_walls)} wall groups")
            return classified_walls

        except Exception as e:
            print(f"Error in enhanced wall classification: {e}")
            # Fall back to basic classification
            return self.classify_wall_types(analysis)

    def _generate_layer_name_enhanced(self, wall: Dict, index: int) -> str:
        """Generate layer name using AI suggestions when available"""
        
        # Check if AI suggested a layer name
        ai_classification = wall.get('ai_classification', {})
        suggested_layer = ai_classification.get('suggested_layer', '')
        
        if suggested_layer and suggested_layer.strip():
            print(f"Using AI suggested layer name: {suggested_layer}")
            return suggested_layer
        
        # Fall back to standard naming
        wall_type = wall['type']
        layer_map = {
            'exterior': f'main_floor_exterior_wall_{index}',
            'interior': f'main_floor_interior_wall_{index}',
            'garage_adjacent': f'main_floor_garage_wall_{index}'
        }
        return layer_map.get(wall_type, f'main_floor_{wall_type}_wall_{index}')

    def _generate_layer_name(self, wall_type: str, index: int) -> str:
        """Generate appropriate layer name based on wall type (legacy method)"""
        layer_map = {
            'exterior': f'main_floor_exterior_wall_{index}',
            'interior': f'main_floor_interior_wall_{index}',
            'garage_adjacent': f'main_floor_garage_wall_{index}'
        }
        return layer_map.get(wall_type, f'main_floor_{wall_type}_wall_{index}')

    def _create_fallback_analysis(self) -> Dict:
        """Create a basic fallback analysis if no geometry is found"""
        print("Creating fallback analysis with minimal structure")
        return {
            'drawing_type': 'floor_plan',
            'spaces': [{
                'type': 'exterior',
                'coordinates': [(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)],
                'layer_name': 'main_floor_exterior_wall_fallback',
                'metadata': {
                    'fallback': True,
                    'message': 'No geometry detected - using minimal fallback'
                }
            }],
            'elements': [],
            'analysis_metadata': {
                'fallback_used': True
            }
        }

def convert_pdf_to_image(pdf_path: str, output_path: Optional[str] = None) -> str:
    """
    Convert PDF to image for AI analysis
    Note: This is a simplified version. For production, you'd use pdf2image library
    """
    if output_path is None:
        output_path = pdf_path.replace('.pdf', '.png')
    
    print(f"PDF to image conversion would happen here: {pdf_path} -> {output_path}")
    print("Note: For full implementation, install pdf2image library")
    
    return output_path

def main():
    """
    Demonstration of AutoCAD integration capabilities
    """
    print("AutoCAD Integration Module")
    print("=========================")
    
    # Create integration instance
    autocad = AutoCADIntegration()
    
    # Create a new DXF document
    autocad.create_new_dxf()
    
    # Create sample layers
    print("\nCreating sample layers...")
    autocad.create_layer("basement_interior_wall", color=1)  # Red
    autocad.create_layer("basement_exterior_wall", color=2)  # Yellow
    autocad.create_layer("main_floor_garage_wall", color=3)  # Green
    
    # Draw sample elements
    print("\nDrawing sample elements...")
    
    # Sample interior wall
    interior_coords = [(0, 0), (100, 0), (100, 50), (0, 50), (0, 0)]
    autocad.draw_polyline(interior_coords, "basement_interior_wall")
    
    # Sample exterior wall
    exterior_coords = [(0, 0), (150, 0), (150, 80), (0, 80), (0, 0)]
    autocad.draw_polyline(exterior_coords, "basement_exterior_wall")
    
    # Sample door
    autocad.draw_rectangle((50, 0), (80, 10), "basement_interior_wall")
    
    # List all layers
    print("\nLayers in document:")
    layers = autocad.list_layers()
    for layer in layers:
        print(f"  - {layer['name']} (Color: {layer['color']})")
    
    # Save the file
    output_file = "sample_architectural_output.dxf"
    autocad.save_dxf(output_file)
    
    print(f"\nSample DXF file created: {output_file}")
    print("AutoCAD integration test completed successfully!")

if __name__ == "__main__":
    main()