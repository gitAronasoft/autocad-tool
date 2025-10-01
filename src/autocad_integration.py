import ezdxf
import os
from typing import List, Dict, Tuple, Optional, Any, Union
import cv2
import numpy as np
from PIL import Image
import math
from collections import defaultdict
from .enhanced_geometry_processor import EnhancedGeometryProcessor

class AutoCADIntegration:
    """
    Handles AutoCAD file operations and layer management
    """
    
    def __init__(self):
        self.current_doc = None
        self.modelspace = None
        self.enhanced_processor = EnhancedGeometryProcessor()
    
    def load_dxf_file(self, file_path: str) -> bool:
        """Load an existing DXF or DWG file"""
        try:
            # Check file extension
            file_ext = os.path.splitext(file_path)[1].lower()
            
            if file_ext == '.dwg':
                print("DWG files are not directly supported by ezdxf. Please convert to DXF format.")
                return False
            
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
            print(f"Error loading file: {e}")
            if 'DWG' in str(e).upper():
                print("Note: DWG files require conversion to DXF format for processing.")
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
    
    def draw_arc(self, center: Tuple[float, float], radius: float, start_angle: float, 
                 end_angle: float, layer_name: str = "0"):
        """Draw an arc"""
        if self.current_doc is None or self.modelspace is None:
            print("No DXF document loaded")
            return False
        
        try:
            center_3d = (center[0], center[1], 0)
            arc = self.modelspace.add_arc(center_3d, radius, start_angle, end_angle)
            arc.dxf.layer = layer_name
            print(f"Drew arc with radius {radius} on layer {layer_name}")
            return True
        except Exception as e:
            print(f"Error drawing arc: {e}")
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
        Execute AutoCAD drawing commands based on enhanced analysis results
        """
        if self.current_doc is None:
            print("No DXF document loaded. Creating new document.")
            self.create_new_dxf()
        
        commands_executed = 0
        
        # Handle enhanced drawing commands if available
        if 'drawing_commands' in analysis_result:
            return self._execute_enhanced_commands(analysis_result['drawing_commands'])
        
        # Fallback to legacy command processing
        
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
    
    def _execute_enhanced_commands(self, drawing_commands: List[Dict]) -> int:
        """
        Execute enhanced drawing commands from the enhanced geometry processor
        """
        commands_executed = 0
        layers_created = set()
        
        print(f"Executing {len(drawing_commands)} enhanced drawing commands...")
        
        for command in drawing_commands:
            try:
                action = command.get('action')
                
                if action == 'create_layer':
                    layer_name = command.get('layer_name')
                    color = command.get('color', 7)
                    linetype = command.get('linetype', 'CONTINUOUS')
                    
                    if layer_name and layer_name not in layers_created:
                        success = self.create_layer(layer_name, color, linetype)
                        if success:
                            layers_created.add(layer_name)
                            commands_executed += 1
                
                elif action == 'draw_line':
                    start_point = command.get('start_point')
                    end_point = command.get('end_point')
                    layer_name = command.get('layer_name', '0')
                    
                    if start_point and end_point:
                        success = self.draw_line(start_point, end_point, layer_name)
                        if success:
                            commands_executed += 1
                
                elif action == 'draw_rectangle':
                    point1 = command.get('point1')
                    point2 = command.get('point2')
                    layer_name = command.get('layer_name', '0')
                    
                    if point1 and point2:
                        success = self.draw_rectangle(point1, point2, layer_name)
                        if success:
                            commands_executed += 1
                
                elif action == 'draw_arc':
                    center = command.get('center')
                    radius = command.get('radius')
                    start_angle = command.get('start_angle', 0)
                    end_angle = command.get('end_angle', 90)
                    layer_name = command.get('layer_name', '0')
                    
                    if center and radius:
                        success = self.draw_arc(center, radius, start_angle, end_angle, layer_name)
                        if success:
                            commands_executed += 1
                
                elif action == 'draw_polyline':
                    coordinates = command.get('coordinates')
                    layer_name = command.get('layer_name', '0')
                    
                    if coordinates and len(coordinates) >= 2:
                        success = self.draw_polyline(coordinates, layer_name)
                        if success:
                            commands_executed += 1
                
                else:
                    print(f"Unknown command action: {action}")
            
            except Exception as e:
                print(f"Error executing command {action}: {e}")
        
        print(f"Successfully executed {commands_executed} enhanced drawing commands")
        return commands_executed
    
    def export_measurements(self, measurements: Dict, output_dir: str = 'outputs') -> Dict[str, str]:
        """
        Export measurements to CSV and JSON formats
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        csv_path = os.path.join(output_dir, 'measurements.csv')
        json_path = os.path.join(output_dir, 'measurements.json')
        
        results = {}
        
        # Export to CSV
        if self.enhanced_processor.export_measurements_csv(measurements, csv_path):
            results['csv'] = csv_path
        
        # Export to JSON
        if self.enhanced_processor.export_measurements_json(measurements, json_path):
            results['json'] = json_path
        
        return results
    
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
        
        # Use stateless extraction to avoid state corruption issues
        return self._extract_entities_from_modelspace(self.modelspace)
    
    def _extract_entities_from_modelspace(self, modelspace) -> Dict[str, List]:
        """
        Stateless extraction method that doesn't rely on instance state
        """
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
            entity_count = 0
            for entity in modelspace:
                entity_count += 1
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

            total_extracted = (len(entities['lines']) + len(entities['lwpolylines']) + 
                             len(entities['polylines']) + len(entities['arcs']) + len(entities['circles']))
            
            print(f"Extracted {len(entities['lines'])} lines, {len(entities['lwpolylines'])} lwpolylines, "
                  f"{len(entities['polylines'])} polylines, {len(entities['arcs'])} arcs, "
                  f"{len(entities['circles'])} circles (total: {total_extracted} from {entity_count} entities)")
            
            # Diagnostic: warn if no entities were extracted from a non-empty modelspace
            if entity_count > 0 and total_extracted == 0:
                print(f"WARNING: Iterated over {entity_count} entities but extracted 0. Check entity types.")
            
            return entities

        except Exception as e:
            print(f"Error extracting geometric entities: {e}")
            import traceback
            traceback.print_exc()
            return {}


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
            print("Analyzing spatial relationships...")
            
            # Combine all linear entities (lines and polylines) for wall analysis
            wall_segments = []
            
            # Add lines as wall segments
            print(f"Processing {len(entities.get('lines', []))} lines...")
            for line in entities.get('lines', []):
                wall_segments.append({
                    'start': line['start'],
                    'end': line['end'],
                    'layer': line['layer'],
                    'length': line['length'],
                    'type': 'line'
                })
            
            # Add polyline segments
            total_polylines = len(entities.get('lwpolylines', [])) + len(entities.get('polylines', []))
            print(f"Processing {total_polylines} polylines...")
            
            for polyline in entities.get('lwpolylines', []) + entities.get('polylines', []):
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

            print(f"Total wall segments to analyze: {len(wall_segments)}")
            
            # Group wall segments by connectivity and orientation
            print("Grouping connected wall segments...")
            wall_groups = self._group_connected_walls(wall_segments)
            analysis['wall_groups'] = wall_groups

            print("Calculating building bounds...")
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
            print("Identifying enclosed areas...")
            for polyline in entities.get('lwpolylines', []) + entities.get('polylines', []):
                if polyline.get('closed', False) and polyline.get('area', 0) > 0:
                    analysis['enclosed_areas'].append({
                        'points': polyline['points'],
                        'area': polyline['area'],
                        'layer': polyline['layer']
                    })

            print(f"Spatial analysis complete: {len(wall_groups)} wall groups, {len(analysis['enclosed_areas'])} enclosed areas")
            return analysis

        except Exception as e:
            print(f"Error analyzing spatial relationships: {e}")
            import traceback
            traceback.print_exc()
            return analysis

    def _group_connected_walls(self, wall_segments: List[Dict]) -> List[Dict]:
        """Group wall segments that are connected to each other (optimized with spatial indexing)"""
        if not wall_segments:
            return []

        # Use spatial indexing for datasets larger than 1000 segments
        if len(wall_segments) > 1000:
            print(f"Large dataset detected ({len(wall_segments)} segments). Using spatial indexing optimization.")
            return self._group_connected_walls_spatial(wall_segments)

        # For very large datasets, use simplified grouping
        if len(wall_segments) > 5000:
            print(f"Very large dataset detected ({len(wall_segments)} segments). Using simplified grouping.")
            return self._group_connected_walls_simplified(wall_segments)

        groups = []
        used_segments = set()
        tolerance = 1.0
        max_iterations = min(len(wall_segments), 1000)  # Cap iterations to prevent infinite loops

        import time
        start_time = time.time()
        timeout_seconds = 30  # 30 second timeout

        for i, segment in enumerate(wall_segments):
            if i in used_segments:
                continue

            # Check timeout
            if time.time() - start_time > timeout_seconds:
                print(f"Wall grouping timed out after {timeout_seconds} seconds. Creating individual groups for remaining segments.")
                # Create individual groups for remaining segments
                for j in range(i, len(wall_segments)):
                    if j not in used_segments:
                        groups.append({
                            'segments': [wall_segments[j]],
                            'total_length': wall_segments[j]['length'],
                            'layers': {wall_segments[j]['layer']},
                            'bounds': self._get_segment_bounds(wall_segments[j])
                        })
                break

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
                
                # Check timeout periodically
                if iterations % 100 == 0 and time.time() - start_time > timeout_seconds:
                    print(f"Wall grouping timed out during group {len(groups)+1}")
                    break
                
                for j, other_segment in enumerate(wall_segments):
                    if j in used_segments:
                        continue

                    # Check if this segment connects to any segment in the group
                    if self._segments_connected_simple(group['segments'], other_segment, tolerance):
                        group['segments'].append(other_segment)
                        group['total_length'] += other_segment['length']
                        group['layers'].add(other_segment['layer'])
                        group['bounds'] = self._update_bounds(group['bounds'], other_segment)
                        used_segments.add(j)
                        found_connection = True
                        break  # Process one connection per iteration

            groups.append(group)

        print(f"Grouped {len(wall_segments)} segments into {len(groups)} wall groups in {time.time() - start_time:.2f} seconds")
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

    def _group_connected_walls_simplified(self, wall_segments: List[Dict]) -> List[Dict]:
        """Simplified grouping for very large datasets - groups by layer and proximity only"""
        print(f"Using simplified grouping for {len(wall_segments)} segments...")
        
        # Group segments by layer first
        layer_groups = defaultdict(list)
        for segment in wall_segments:
            layer_groups[segment['layer']].append(segment)
        
        groups = []
        for layer_name, layer_segments in layer_groups.items():
            # For each layer, create groups based on spatial proximity
            if len(layer_segments) <= 100:
                # Small enough to use normal grouping
                layer_group = {
                    'segments': layer_segments,
                    'total_length': sum(seg['length'] for seg in layer_segments),
                    'layers': {layer_name},
                    'bounds': self._calculate_segment_bounds(layer_segments)
                }
                groups.append(layer_group)
            else:
                # Split large layer groups into spatial chunks
                chunk_size = 50
                for i in range(0, len(layer_segments), chunk_size):
                    chunk = layer_segments[i:i+chunk_size]
                    chunk_group = {
                        'segments': chunk,
                        'total_length': sum(seg['length'] for seg in chunk),
                        'layers': {layer_name},
                        'bounds': self._calculate_segment_bounds(chunk)
                    }
                    groups.append(chunk_group)
        
        print(f"Simplified grouping created {len(groups)} groups from {len(layer_groups)} layers")
        return groups

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
        Main method to analyze DXF geometry using enhanced processing
        """
        print("Starting enhanced DXF geometric analysis...")
        
        # Use the enhanced geometry processor for comprehensive analysis
        try:
            analysis_result = self.enhanced_processor.process_dxf_geometry(self, analyzer)
            print("Enhanced geometric analysis completed successfully")
            return analysis_result
        except Exception as e:
            print(f"Enhanced analysis failed: {e}. Falling back to basic analysis.")
            return self._fallback_to_basic_analysis(analyzer)
    
    def _fallback_to_basic_analysis(self, analyzer=None) -> Dict:
        """
        Fallback to the original analysis method if enhanced processing fails
        """
        print("Using fallback analysis method...")
        
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
                    
                    # Use AI to enhance the spatial analysis with improved timeout handling  
                    try:
                        enhanced_analysis = analyzer.analyze_geometric_data(analysis_metadata, spatial_analysis)
                        spatial_analysis = enhanced_analysis
                        print("✅ AI analysis integration completed successfully")
                    except Exception as e:
                        if "timeout" in str(e).lower() or "timed out" in str(e).lower():
                            print("⚠️ AI enhancement failed: Request timed out. Continuing with geometric analysis.")
                        else:
                            print(f"⚠️ AI enhancement failed: {e}. Continuing with geometric analysis.")
                        # Continue with geometric-only analysis - this is expected fallback behavior
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

        # Group walls by type and create continuous boundary traces (as requested by user)
        boundary_groups = self._create_boundary_traces(classified_walls)
        
        # Convert boundary traces to spaces for drawing
        for boundary_type, boundary_data in boundary_groups.items():
            if boundary_data['coordinates']:
                result['spaces'].append({
                    'type': boundary_type,
                    'coordinates': boundary_data['coordinates'],
                    'layer_name': boundary_data['layer_name'],
                    'metadata': {
                        'total_length': boundary_data['total_length'],
                        'wall_groups_merged': boundary_data['groups_merged'],
                        'bounds': boundary_data['bounds'],
                        'is_continuous_boundary': True
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
                
                # Enhanced wall classification logic
                wall_type = self._classify_wall_type_enhanced(group, building_bounds, perimeter_tolerance)

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

    def _create_boundary_traces(self, classified_walls: List[Dict]) -> Dict:
        """
        Create clean, organized architectural element traces
        Instead of merging all walls into chaotic overlapping lines, create proper organized layers
        """
        print(f"Creating organized architectural traces from {len(classified_walls)} wall groups...")
        
        # Identify building perimeter (exterior boundary)
        exterior_perimeter = self._find_building_perimeter(classified_walls)
        
        # Identify room boundaries and interior features
        room_boundaries = self._find_room_boundaries(classified_walls)
        
        # Detect architectural features (doors, windows, etc.)
        architectural_features = self._detect_architectural_features(classified_walls)
        
        # Detect floor type for proper layer naming
        floor_type = self._detect_floor_type(classified_walls, exterior_perimeter)
        
        # Validate and fix geometric issues
        if exterior_perimeter:
            exterior_perimeter = self._validate_and_fix_boundary(exterior_perimeter, 'exterior')
        
        validated_rooms = []
        for room in room_boundaries:
            validated_room = self._validate_and_fix_boundary(room, 'interior')
            if validated_room:  # Only include valid rooms
                validated_rooms.append(validated_room)
        room_boundaries = validated_rooms
        
        # Create organized layer structure
        boundary_groups = {}
        
        # Add exterior perimeter if found
        if exterior_perimeter:
            boundary_groups['exterior'] = {
                'coordinates': exterior_perimeter['coordinates'],
                'layer_name': f'{floor_type}_exterior_perimeter',
                'total_length': exterior_perimeter['total_length'],
                'groups_merged': exterior_perimeter['groups_merged'],
                'bounds': exterior_perimeter['bounds']
            }
            print(f"Building exterior perimeter: {len(exterior_perimeter['coordinates'])} points, "
                  f"length {exterior_perimeter['total_length']:.1f}")
        
        # Add room boundaries (limit to avoid chaos)
        max_rooms_to_show = 5  # Limit room boundaries to keep output clean
        for i, room in enumerate(room_boundaries[:max_rooms_to_show]):
            room_layer_name = f'{floor_type}_room_boundary_{i+1}'
            boundary_groups[f'room_{i+1}'] = {
                'coordinates': room['coordinates'],
                'layer_name': room_layer_name,
                'total_length': room['total_length'],
                'groups_merged': room['groups_merged'],
                'bounds': room['bounds']
            }
            print(f"Room boundary {i+1}: {len(room['coordinates'])} points, "
                  f"length {room['total_length']:.1f}")
        
        # Add architectural features with unique identifiers
        feature_count = 0
        for feature_type, features in architectural_features.items():
            for i, feature in enumerate(features[:3]):  # Limit features to avoid clutter
                feature_count += 1
                unique_id = f"{feature_type}_{i+1}_{hash(str(feature['coordinates']))%1000:03d}"
                boundary_groups[unique_id] = {
                    'coordinates': feature['coordinates'],
                    'layer_name': f"{floor_type}_{feature_type}_{i+1}",
                    'total_length': 0,  # Features don't have length
                    'groups_merged': 1,
                    'bounds': feature['bounds'],
                    'feature_type': feature_type,
                    'unique_id': unique_id,
                    'dimensions': feature['dimensions']
                }
                print(f"Detected {feature_type} {i+1}: {feature['dimensions']} (ID: {unique_id})")
        
        print(f"Created {len(boundary_groups)} organized architectural layers ({feature_count} features detected)")
        return boundary_groups
    
    def _find_building_perimeter(self, classified_walls: List[Dict]) -> Optional[Dict]:
        """Find the main building exterior perimeter"""
        # Look for walls classified as exterior or at building boundaries
        perimeter_walls = [wall for wall in classified_walls if wall['type'] == 'exterior']
        
        if not perimeter_walls:
            return None
        
        # For now, take the largest exterior wall group as the main perimeter
        main_perimeter = max(perimeter_walls, key=lambda w: w['total_length'])
        
        return {
            'coordinates': main_perimeter['coordinates'],
            'total_length': main_perimeter['total_length'],
            'groups_merged': 1,
            'bounds': main_perimeter['bounds']
        }
    
    def _find_room_boundaries(self, classified_walls: List[Dict]) -> List[Dict]:
        """Identify individual room boundaries from interior walls"""
        # Group interior walls by spatial proximity to identify room boundaries
        interior_walls = [wall for wall in classified_walls if wall['type'] == 'interior']
        
        if not interior_walls:
            return []
        
        # For now, limit to a reasonable number of room boundaries to avoid chaos
        max_rooms = 10
        room_boundaries = []
        
        # Sort walls by total length (longer walls likely form main room boundaries)
        sorted_walls = sorted(interior_walls, key=lambda w: w['total_length'], reverse=True)
        
        for i, wall in enumerate(sorted_walls[:max_rooms]):
            # Skip walls that are too small (likely fixtures or details)
            if wall['total_length'] < 50:  # Minimum wall length threshold
                continue
                
            room_boundaries.append({
                'coordinates': wall['coordinates'],
                'total_length': wall['total_length'],
                'groups_merged': 1,
                'bounds': wall['bounds']
            })
        
        return room_boundaries

    def _classify_wall_type_enhanced(self, group: Dict, building_bounds: Dict, perimeter_tolerance: float) -> str:
        """
        Enhanced wall classification with better logic for architectural elements
        """
        group_bounds = group['bounds']
        segments = group['segments']
        
        # Check if this wall group is on the building perimeter
        is_perimeter = (
            abs(group_bounds['min_x'] - building_bounds['min_x']) <= perimeter_tolerance or
            abs(group_bounds['max_x'] - building_bounds['max_x']) <= perimeter_tolerance or
            abs(group_bounds['min_y'] - building_bounds['min_y']) <= perimeter_tolerance or
            abs(group_bounds['max_y'] - building_bounds['max_y']) <= perimeter_tolerance
        )
        
        # Check for garage walls based on layer names
        layer_names = [layer.lower() for layer in group['layers']]
        has_garage_indicator = any('garage' in layer for layer in layer_names)
        
        # Analyze wall characteristics
        total_length = group['total_length']
        segment_count = len(segments)
        
        # Classification logic
        if is_perimeter and total_length > 100:  # Long perimeter walls are likely exterior
            return 'exterior'
        elif has_garage_indicator:
            return 'garage_adjacent'
        elif total_length > 200:  # Very long walls are likely main structural walls
            return 'exterior' if is_perimeter else 'interior'
        elif segment_count == 1 and total_length < 50:  # Short single segments might be doors/windows
            return 'feature'  # Will be processed separately for door/window detection
        else:
            return 'interior'

    def _detect_architectural_features(self, classified_walls: List[Dict]) -> Dict:
        """
        Detect doors, windows, and other architectural features
        """
        features = {
            'doors': [],
            'windows': [],
            'openings': []
        }
        
        # Look for feature-type walls (short segments that might be doors/windows)
        feature_walls = [wall for wall in classified_walls if wall['type'] == 'feature']
        
        for feature in feature_walls:
            # Analyze feature characteristics to classify as door or window
            total_length = feature['total_length']
            bounds = feature['bounds']
            width = bounds['max_x'] - bounds['min_x']
            height = bounds['max_y'] - bounds['min_y']
            
            if total_length < 20:  # Very small features might be windows
                features['windows'].append({
                    'coordinates': feature['coordinates'],
                    'bounds': bounds,
                    'layer_name': 'windows',
                    'dimensions': {'width': width, 'height': height}
                })
            elif total_length < 50:  # Medium features might be doors
                features['doors'].append({
                    'coordinates': feature['coordinates'],
                    'bounds': bounds,
                    'layer_name': 'doors',
                    'dimensions': {'width': width, 'height': height}
                })
            else:  # Larger features are general openings
                features['openings'].append({
                    'coordinates': feature['coordinates'],
                    'bounds': bounds,
                    'layer_name': 'openings',
                    'dimensions': {'width': width, 'height': height}
                })
        
        return features

    def _detect_floor_type(self, classified_walls: List[Dict], exterior_perimeter: Optional[Dict]) -> str:
        """
        Detect floor type (basement, main_floor, second_floor) based on architectural cues
        """
        # Analyze wall characteristics and spatial patterns
        if not classified_walls:
            return 'main_floor'  # Default
        
        # Count different wall types
        exterior_count = len([w for w in classified_walls if w['type'] == 'exterior'])
        interior_count = len([w for w in classified_walls if w['type'] == 'interior'])
        garage_count = len([w for w in classified_walls if w['type'] == 'garage_adjacent'])
        
        # Analyze building dimensions if exterior perimeter exists
        if exterior_perimeter:
            bounds = exterior_perimeter['bounds']
            building_area = (bounds['max_x'] - bounds['min_x']) * (bounds['max_y'] - bounds['min_y'])
            
            # Very large buildings might indicate main floor
            if building_area > 500000:  # Large building
                return 'main_floor'
        
        # Analyze layer names for clues
        all_layer_names = []
        for wall in classified_walls:
            all_layer_names.extend(wall.get('layer_suggestions', []))
        
        layer_text = ' '.join(all_layer_names).lower()
        
        # Look for basement indicators
        if any(keyword in layer_text for keyword in ['basement', 'foundation', 'lower', 'cellar']):
            return 'basement'
        
        # Look for second floor indicators  
        if any(keyword in layer_text for keyword in ['second', 'upper', '2nd', 'floor_2']):
            return 'second_floor'
            
        # Look for garage indicators (often main floor)
        if garage_count > 0 or 'garage' in layer_text:
            return 'main_floor'
        
        # Default classification based on wall patterns
        if interior_count > exterior_count * 3:  # Many interior walls suggest main living floor
            return 'main_floor'
        elif exterior_count > interior_count:  # More exterior walls might suggest basement (foundation)
            return 'basement'
        else:
            return 'main_floor'  # Default

    def _validate_and_fix_boundary(self, boundary: Dict, boundary_type: str) -> Optional[Dict]:
        """
        Validate and fix geometric issues in boundaries
        Ensures boundaries are closed, non-self-intersecting loops suitable for professional CAD workflows
        """
        if not boundary or 'coordinates' not in boundary:
            print(f"Rejected: {boundary_type} boundary missing coordinates")
            return None
            
        coords = boundary['coordinates']
        
        # STRICT: Reject boundaries with insufficient points
        if len(coords) < 3:
            print(f"Rejected: {boundary_type} boundary has insufficient points ({len(coords)}) - minimum 3 required")
            return None
        
        validated_coords = []
        
        # Remove duplicate consecutive points with stricter tolerance
        for i, coord in enumerate(coords):
            if i == 0 or self._distance_between_points(coord, coords[i-1]) > 0.5:  # Stricter tolerance
                validated_coords.append(coord)
        
        # STRICT: After deduplication, must still have at least 3 points
        if len(validated_coords) < 3:
            print(f"Rejected: {boundary_type} boundary has insufficient unique points after deduplication ({len(validated_coords)})")
            return None
        
        # Ensure boundary is closed
        first_point = validated_coords[0]
        last_point = validated_coords[-1]
        
        if self._distance_between_points(first_point, last_point) > 1.0:  # Not closed
            validated_coords.append(first_point)  # Close the boundary
            print(f"Fixed: Closed {boundary_type} boundary by connecting endpoints")
        
        # STRICT: Check and reject self-intersections
        if self._has_obvious_self_intersection(validated_coords):
            print(f"Rejected: {boundary_type} boundary has self-intersections - cannot be used for professional CAD workflows")
            return None
        
        # STRICT: Final validation - ensure we have a valid polygon
        if len(validated_coords) < 4:  # Need at least 3 unique points + closure
            print(f"Rejected: {boundary_type} boundary insufficient for closed polygon ({len(validated_coords)} points)")
            return None
        
        # Calculate area to ensure polygon is valid
        area = self._calculate_polygon_area(validated_coords)
        if abs(area) < 10.0:  # Very small area might indicate degenerate polygon
            print(f"Rejected: {boundary_type} boundary has very small area ({area:.2f}) - likely degenerate")
            return None
        
        # Update boundary with validated coordinates
        validated_boundary = boundary.copy()
        validated_boundary['coordinates'] = validated_coords
        validated_boundary['is_closed'] = True
        validated_boundary['validation_status'] = 'validated'
        validated_boundary['polygon_area'] = abs(area)
        
        # Recalculate bounds with validated coordinates
        x_coords = [coord[0] for coord in validated_coords]
        y_coords = [coord[1] for coord in validated_coords]
        validated_boundary['bounds'] = {
            'min_x': min(x_coords), 'max_x': max(x_coords),
            'min_y': min(y_coords), 'max_y': max(y_coords)
        }
        
        print(f"Validated: {boundary_type} boundary - {len(validated_coords)} points, area {abs(area):.1f}")
        return validated_boundary
    
    def _calculate_polygon_area(self, coords: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula"""
        if len(coords) < 3:
            return 0.0
        
        area = 0.0
        n = len(coords)
        for i in range(n):
            j = (i + 1) % n
            area += coords[i][0] * coords[j][1]
            area -= coords[j][0] * coords[i][1]
        return area / 2.0
    
    def _distance_between_points(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate Euclidean distance between two points"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _has_obvious_self_intersection(self, coords: List[Tuple[float, float]]) -> bool:
        """Simple check for obvious self-intersections"""
        # This is a basic check - in production, use more sophisticated algorithms
        if len(coords) < 4:
            return False
        
        # Check if any non-adjacent line segments intersect
        for i in range(len(coords) - 1):
            for j in range(i + 2, len(coords) - 1):
                if j == len(coords) - 2 and i == 0:  # Skip checking first and last segments (they should meet)
                    continue
                if self._line_segments_intersect(coords[i], coords[i+1], coords[j], coords[j+1]):
                    return True
        return False
    
    def _line_segments_intersect(self, p1, p2, p3, p4) -> bool:
        """Check if two line segments intersect"""
        # Using cross product method
        def ccw(A, B, C):
            return (C[1] - A[1]) * (B[0] - A[0]) > (B[1] - A[1]) * (C[0] - A[0])
        
        return ccw(p1, p3, p4) != ccw(p2, p3, p4) and ccw(p1, p2, p3) != ccw(p1, p2, p4)

    def _generate_layer_name_enhanced(self, wall: Dict, index: int) -> str:
        """Generate layer name using AI suggestions when available (legacy method - now replaced by boundary tracing)"""
        
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