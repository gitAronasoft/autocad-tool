import math
import json
from typing import Dict, List, Tuple, Optional, Any, TYPE_CHECKING
from collections import defaultdict, Counter
import ezdxf

if TYPE_CHECKING:
    from .autocad_integration import AutoCADIntegration

class EnhancedGeometryProcessor:
    """
    Comprehensive DXF geometry processor that provides:
    1. House outline detection and tracing
    2. Standardized layer naming matching client specifications
    3. Element detection (doors, windows, garages)
    4. Measurement extraction and export
    5. Interior/exterior wall classification
    """
    
    def __init__(self):
        # Client-specified layer naming convention
        self.layer_naming = {
            'walls': {
                'basement': {
                    'interior': 'basement interior line',
                    'exterior': 'basement exterior line'
                },
                'main_floor': {
                    'interior': 'main floor interior line',
                    'exterior': 'main floor exterior line',
                    'garage': 'main floor garage line'
                },
                'second_floor': {
                    'interior': 'second floor interior line',
                    'exterior': 'second floor exterior line'
                }
            },
            'elements': {
                'doors': {
                    'front': 'front door main',
                    'back': 'back door main', 
                    'patio': 'patio door main',
                    'garage': 'garage door main',
                    'interior': 'interior door main'
                },
                'windows': {
                    'front': 'front window main',
                    'back': 'back window main',
                    'side': 'side window main',
                    'door': 'door window main'
                }
            }
        }
        
        # Color scheme matching user's manual highlighting:
        # - Outer boundaries (exterior/perimeter): Yellow/Lime for clear visibility
        # - Inner boundaries (interior walls): Magenta/Pink for contrast
        self.layer_colors = {
            'basement interior line': 6,  # Magenta (inner boundaries)
            'basement exterior line': 2,  # Yellow (outer boundary)
            'main floor interior line': 6,  # Magenta (inner boundaries)
            'main floor exterior line': 2,  # Yellow (outer boundary)
            'main floor garage line': 4,  # Cyan
            'second floor interior line': 6,  # Magenta (inner boundaries)
            'second floor exterior line': 2,  # Yellow (outer boundary)
            'front door main': 3,  # Green
            'back door main': 3,  # Green
            'patio door main': 3,  # Green
            'garage door main': 3,  # Green
            'interior door main': 3,  # Green
            'front window main': 5,  # Blue
            'back window main': 5,  # Blue
            'side window main': 5,  # Blue
            'door window main': 5,  # Blue
        }
    
    def process_dxf_geometry(self, autocad_integration: 'AutoCADIntegration', ai_analyzer=None) -> Dict:
        """
        Main processing method that performs comprehensive DXF analysis
        """
        print("Starting enhanced DXF geometry processing...")
        
        # Step 1: Extract all geometric entities
        entities = autocad_integration.extract_geometric_entities()
        if not entities:
            return self._create_enhanced_fallback()
        
        # Step 2: Detect house outline and structure
        house_structure = self._detect_house_outline(entities)
        
        # Step 3: Classify wall segments (interior vs exterior)
        wall_classification = self._classify_walls_advanced(house_structure, entities)
        
        # Step 4: Detect architectural elements (doors, windows, garages)
        elements_detected = self._detect_architectural_elements(entities, house_structure)
        
        # Step 5: Extract measurements and dimensions
        measurements = self._extract_measurements(entities, elements_detected, wall_classification)
        
        # Step 6: Enhance with AI analysis if available
        if ai_analyzer:
            house_structure, wall_classification, elements_detected = self._enhance_with_ai(
                ai_analyzer, house_structure, wall_classification, elements_detected, entities
            )
        
        # Step 7: Generate standardized layers and drawing commands
        drawing_commands = self._generate_drawing_commands(
            house_structure, wall_classification, elements_detected
        )
        
        # Step 8: Prepare results in expected format
        return self._format_results(
            house_structure, wall_classification, elements_detected, 
            measurements, drawing_commands
        )
    
    def _detect_house_outline(self, entities: Dict[str, List]) -> Dict:
        """
        Detect the main house outline and structure from DXF geometry
        """
        print("Detecting house outline and structure...")
        
        # Combine all linear entities
        all_segments = []
        
        # Process lines
        for line in entities.get('lines', []):
            all_segments.append({
                'start': line['start'],
                'end': line['end'],
                'length': line['length'],
                'layer': line['layer'],
                'type': 'line'
            })
        
        # Process polylines and lwpolylines
        for polyline in entities.get('lwpolylines', []) + entities.get('polylines', []):
            points = polyline['points']
            if len(points) >= 2:
                for i in range(len(points) - 1):
                    start, end = points[i], points[i + 1]
                    length = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                    all_segments.append({
                        'start': start,
                        'end': end,
                        'length': length,
                        'layer': polyline['layer'],
                        'type': 'polyline_segment',
                        'parent_closed': polyline.get('closed', False)
                    })
        
        # Find building bounds using percentile-based trimming to exclude outliers (dimensions/annotations)
        all_points = []
        for segment in all_segments:
            all_points.extend([segment['start'], segment['end']])
        
        if not all_points:
            return {'outline_detected': False, 'segments': [], 'bounds': None}
        
        # Use 2% trimming on each side to exclude dimension/annotation outliers
        x_coords = sorted([p[0] for p in all_points])
        y_coords = sorted([p[1] for p in all_points])
        trim_percent = 0.02  # Trim 2% from each end
        trim_count = max(1, int(len(x_coords) * trim_percent))
        
        bounds = {
            'min_x': x_coords[trim_count],
            'max_x': x_coords[-trim_count-1],
            'min_y': y_coords[trim_count],
            'max_y': y_coords[-trim_count-1]
        }
        bounds['width'] = bounds['max_x'] - bounds['min_x']
        bounds['height'] = bounds['max_y'] - bounds['min_y']
        
        print(f"Building bounds (2% trimmed): {bounds['width']:.1f} x {bounds['height']:.1f} units")
        
        # Detect main outline (exterior perimeter)
        perimeter_segments = self._find_perimeter_segments(all_segments, bounds)
        
        # Group connected segments into continuous walls
        wall_groups = self._group_connected_segments(all_segments)
        
        return {
            'outline_detected': True,
            'segments': all_segments,
            'perimeter_segments': perimeter_segments,
            'wall_groups': wall_groups,
            'bounds': bounds,
            'total_segments': len(all_segments)
        }
    
    def _find_perimeter_segments(self, segments: List[Dict], bounds: Dict) -> List[Dict]:
        """
        Identify segments that form the building perimeter (exterior walls).
        Uses adaptive tolerance based on building size.
        """
        # Use 1% of the smaller dimension as tolerance (adaptive to drawing scale)
        building_size = min(bounds['width'], bounds['height'])
        perimeter_tolerance = max(building_size * 0.01, 5.0)  # At least 5 units
        
        perimeter_segments = []
        
        for segment in segments:
            start_x, start_y = segment['start']
            end_x, end_y = segment['end']
            
            # Check if segment is on or near the building perimeter
            on_perimeter = (
                # Near left edge
                (abs(start_x - bounds['min_x']) <= perimeter_tolerance and 
                 abs(end_x - bounds['min_x']) <= perimeter_tolerance) or
                # Near right edge
                (abs(start_x - bounds['max_x']) <= perimeter_tolerance and 
                 abs(end_x - bounds['max_x']) <= perimeter_tolerance) or
                # Near bottom edge
                (abs(start_y - bounds['min_y']) <= perimeter_tolerance and 
                 abs(end_y - bounds['min_y']) <= perimeter_tolerance) or
                # Near top edge
                (abs(start_y - bounds['max_y']) <= perimeter_tolerance and 
                 abs(end_y - bounds['max_y']) <= perimeter_tolerance)
            )
            
            if on_perimeter:
                perimeter_segments.append(segment)
        
        print(f"Found {len(perimeter_segments)} perimeter segments out of {len(segments)} total (tolerance: {perimeter_tolerance:.1f} units)")
        return perimeter_segments
    
    def _group_connected_segments(self, segments: List[Dict]) -> List[Dict]:
        """
        Group segments that are connected to form continuous walls (optimized version).
        Prioritizes longer segments for better wall detection.
        """
        connection_tolerance = 2.0  # Units
        groups = []
        used_segments = set()
        
        # Sort segments by length (longest first) to prioritize main walls
        sorted_segments = sorted(segments, key=lambda s: s.get('length', 0), reverse=True)
        
        # Limit processing for performance - balanced between coverage and speed
        max_segments_to_process = min(len(sorted_segments), 1500)  # Balanced limit
        segments_to_process = sorted_segments[:max_segments_to_process]
        
        print(f"Processing {len(segments_to_process)} segments for grouping (prioritized by length from {len(segments)} total)")
        
        for i, segment in enumerate(segments_to_process):
            if i in used_segments:
                continue
            
            # Start a new group
            group = {
                'segments': [segment],
                'total_length': segment['length'],
                'layers': {segment['layer']},
                'bounds': self._calculate_segment_bounds([segment])
            }
            used_segments.add(i)
            
            # Find connected segments with iteration limit to prevent infinite loops
            max_iterations = 50  # Prevent infinite loops
            iteration_count = 0
            changed = True
            
            while changed and iteration_count < max_iterations:
                changed = False
                iteration_count += 1
                
                for j, other_segment in enumerate(segments_to_process):
                    if j in used_segments:
                        continue
                    
                    # Check if this segment connects to any in the current group
                    if self._segments_connected(group['segments'], other_segment, connection_tolerance):
                        group['segments'].append(other_segment)
                        group['total_length'] += other_segment['length']
                        group['layers'].add(other_segment['layer'])
                        group['bounds'] = self._calculate_segment_bounds(group['segments'])
                        used_segments.add(j)
                        changed = True
                        break  # Process one connection per iteration to avoid excessive computation
            
            groups.append(group)
        
        print(f"Grouped {len(segments_to_process)} segments into {len(groups)} wall groups")
        return groups
    
    def _segments_connected(self, group_segments: List[Dict], new_segment: Dict, tolerance: float) -> bool:
        """
        Check if a new segment connects to any segment in the group
        """
        new_start, new_end = new_segment['start'], new_segment['end']
        
        for segment in group_segments:
            seg_start, seg_end = segment['start'], segment['end']
            
            # Check all possible connections
            distances = [
                self._distance(new_start, seg_start),
                self._distance(new_start, seg_end),
                self._distance(new_end, seg_start),
                self._distance(new_end, seg_end)
            ]
            
            if any(d <= tolerance for d in distances):
                return True
        
        return False
    
    def _distance(self, p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        """Calculate distance between two points"""
        return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    
    def _calculate_segment_bounds(self, segments: List[Dict]) -> Dict:
        """Calculate bounding box for a list of segments"""
        all_points = []
        for segment in segments:
            all_points.extend([segment['start'], segment['end']])
        
        return {
            'min_x': min(p[0] for p in all_points),
            'max_x': max(p[0] for p in all_points),
            'min_y': min(p[1] for p in all_points),
            'max_y': max(p[1] for p in all_points)
        }
    
    def _classify_walls_advanced(self, house_structure: Dict, entities: Dict) -> Dict:
        """
        Advanced wall classification to distinguish interior vs exterior walls
        """
        print("Classifying walls (interior vs exterior)...")
        
        if not house_structure['outline_detected']:
            return {'classifications': [], 'perimeter_wall_groups': [], 'interior_wall_groups': []}
        
        perimeter_segments = set(id(seg) for seg in house_structure['perimeter_segments'])
        wall_groups = house_structure['wall_groups']
        bounds = house_structure['bounds']
        
        classifications = []
        perimeter_groups = []
        interior_groups = []
        
        for group in wall_groups:
            # Determine if this wall group is primarily exterior or interior
            # Use more forgiving criteria for architectural drawings
            perimeter_segment_count = sum(
                1 for seg in group['segments'] 
                if id(seg) in perimeter_segments
            )
            
            # Exterior if: has ≥3 perimeter segments OR >30% are perimeter OR very long and touches perimeter
            is_exterior = (
                perimeter_segment_count >= 3 or  # At least 3 perimeter touches
                (perimeter_segment_count > len(group['segments']) * 0.3) or  # >30% are perimeter
                (perimeter_segment_count >= 1 and group['total_length'] > 200)  # Long wall touching perimeter
            )
            
            # Determine floor type based on geometry analysis
            floor_type = self._determine_floor_type(group, bounds, entities)
            
            # Determine if this might be a garage wall
            is_garage = self._is_garage_wall(group, bounds, entities)
            
            # Create classification
            if is_garage:
                wall_type = 'garage'
                layer_name = self.layer_naming['walls'][floor_type]['garage']
            elif is_exterior:
                wall_type = 'exterior'
                layer_name = self.layer_naming['walls'][floor_type]['exterior']
            else:
                wall_type = 'interior'
                layer_name = self.layer_naming['walls'][floor_type]['interior']
            
            classification = {
                'group_index': len(classifications),
                'wall_type': wall_type,
                'floor_type': floor_type,
                'layer_name': layer_name,
                'color': self.layer_colors.get(layer_name, 7),
                'segments': group['segments'],
                'total_length': group['total_length'],
                'bounds': group['bounds'],
                'is_exterior': is_exterior,
                'is_garage': is_garage,
                'confidence': 0.9 if is_exterior else 0.8
            }
            
            classifications.append(classification)
            
            if is_exterior:
                perimeter_groups.append(classification)
            else:
                interior_groups.append(classification)
        
        print(f"Classified {len(perimeter_groups)} exterior and {len(interior_groups)} interior wall groups")
        
        return {
            'classifications': classifications,
            'perimeter_wall_groups': perimeter_groups,
            'interior_wall_groups': interior_groups
        }
    
    def _determine_floor_type(self, wall_group: Dict, bounds: Dict, entities: Dict) -> str:
        """
        Determine floor type (basement, main_floor, second_floor) based on geometry
        """
        # For now, default to main_floor
        # In a more sophisticated implementation, this would analyze:
        # - Z-coordinates if available
        # - Layer names
        # - Text annotations
        # - Drawing structure
        
        # Check layer names for clues
        layer_names = ' '.join(wall_group['layers']).lower()
        
        if 'basement' in layer_names or 'bsmt' in layer_names:
            return 'basement'
        elif 'second' in layer_names or '2nd' in layer_names or 'upper' in layer_names:
            return 'second_floor'
        else:
            return 'main_floor'
    
    def _is_garage_wall(self, wall_group: Dict, bounds: Dict, entities: Dict) -> bool:
        """
        Determine if this wall group is associated with a garage
        """
        # Check layer names for garage indicators
        layer_names = ' '.join(wall_group['layers']).lower()
        garage_keywords = ['garage', 'gar', 'carport']
        
        return any(keyword in layer_names for keyword in garage_keywords)
    
    def _detect_architectural_elements(self, entities: Dict, house_structure: Dict) -> Dict:
        """
        Detect doors, windows, and other architectural elements
        """
        print("Detecting architectural elements (doors, windows, garages)...")
        
        elements = {
            'doors': [],
            'windows': [],
            'openings': []
        }
        
        # Detect doors from blocks or specific geometry patterns
        elements['doors'] = self._detect_doors(entities, house_structure)
        
        # Detect windows from blocks or geometry patterns
        elements['windows'] = self._detect_windows(entities, house_structure)
        
        # Detect openings in walls (potential doors/windows)
        elements['openings'] = self._detect_wall_openings(entities, house_structure)
        
        total_elements = len(elements['doors']) + len(elements['windows']) + len(elements['openings'])
        print(f"Detected {total_elements} architectural elements: "
              f"{len(elements['doors'])} doors, {len(elements['windows'])} windows, "
              f"{len(elements['openings'])} openings")
        
        return elements
    
    def _detect_doors(self, entities: Dict, house_structure: Dict) -> List[Dict]:
        """
        Detect door elements from DXF geometry
        """
        doors = []
        
        # Look for door blocks first
        for block in entities.get('blocks', []):
            block_name = block.get('name', '').lower()
            if any(keyword in block_name for keyword in ['door', 'dr']):
                door = self._analyze_door_block(block)
                if door:
                    doors.append(door)
        
        # Look for door-like arc patterns (swing doors)
        doors.extend(self._detect_door_arcs(entities, house_structure))
        
        # Look for rectangular openings that might be doors
        doors.extend(self._detect_door_rectangles(entities, house_structure))
        
        return doors
    
    def _detect_windows(self, entities: Dict, house_structure: Dict) -> List[Dict]:
        """
        Detect window elements from DXF geometry
        """
        windows = []
        
        # Look for window blocks
        for block in entities.get('blocks', []):
            block_name = block.get('name', '').lower()
            if any(keyword in block_name for keyword in ['window', 'win', 'wndw']):
                window = self._analyze_window_block(block)
                if window:
                    windows.append(window)
        
        # Look for small rectangular patterns that might be windows
        windows.extend(self._detect_window_rectangles(entities, house_structure))
        
        return windows
    
    def _detect_door_arcs(self, entities: Dict, house_structure: Dict) -> List[Dict]:
        """
        Detect doors from arc patterns (door swing indicators)
        """
        doors = []
        
        for arc in entities.get('arcs', []):
            # Check if arc could represent a door swing
            radius = arc['radius']
            if 24 <= radius <= 48:  # Typical door swing radius (inches)
                # Find nearby wall segments
                nearby_walls = self._find_nearby_wall_segments(
                    arc['center'], house_structure, radius + 6
                )
                
                if nearby_walls:
                    door = {
                        'type': 'swing_door',
                        'center': arc['center'],
                        'radius': radius,
                        'width': radius * 2,  # Approximate door width
                        'layer_name': self._determine_door_layer_name(arc['center'], house_structure),
                        'color': self.layer_colors.get(self._determine_door_layer_name(arc['center'], house_structure), 6),
                        'confidence': 0.7,
                        'source': 'arc_pattern'
                    }
                    doors.append(door)
        
        return doors
    
    def _detect_door_rectangles(self, entities: Dict, house_structure: Dict) -> List[Dict]:
        """
        Detect doors from rectangular openings
        """
        doors = []
        
        # Analyze closed polylines that might represent doors
        for polyline in entities.get('lwpolylines', []):
            if polyline.get('closed', False):
                bounds = self._calculate_polyline_bounds(polyline['points'])
                width = bounds['max_x'] - bounds['min_x']
                height = bounds['max_y'] - bounds['min_y']
                
                # Check if dimensions match typical door sizes
                if self._is_door_sized(width, height):
                    door = {
                        'type': 'rectangular_door',
                        'bounds': bounds,
                        'width': width,
                        'height': height,
                        'center': ((bounds['min_x'] + bounds['max_x'])/2, (bounds['min_y'] + bounds['max_y'])/2),
                        'layer_name': self._determine_door_layer_name((bounds['min_x'] + bounds['max_x'])/2, house_structure),
                        'color': self.layer_colors.get(self._determine_door_layer_name((bounds['min_x'] + bounds['max_x'])/2, house_structure), 6),
                        'confidence': 0.6,
                        'source': 'rectangle_pattern'
                    }
                    doors.append(door)
        
        return doors
    
    def _detect_window_rectangles(self, entities: Dict, house_structure: Dict) -> List[Dict]:
        """
        Detect windows from rectangular patterns
        """
        windows = []
        
        for polyline in entities.get('lwpolylines', []):
            if polyline.get('closed', False):
                bounds = self._calculate_polyline_bounds(polyline['points'])
                width = bounds['max_x'] - bounds['min_x']
                height = bounds['max_y'] - bounds['min_y']
                
                # Check if dimensions match typical window sizes
                if self._is_window_sized(width, height):
                    window = {
                        'type': 'rectangular_window',
                        'bounds': bounds,
                        'width': width,
                        'height': height,
                        'center': ((bounds['min_x'] + bounds['max_x'])/2, (bounds['min_y'] + bounds['max_y'])/2),
                        'layer_name': self._determine_window_layer_name((bounds['min_x'] + bounds['max_x'])/2, house_structure),
                        'color': self.layer_colors.get(self._determine_window_layer_name((bounds['min_x'] + bounds['max_x'])/2, house_structure), 7),
                        'confidence': 0.6,
                        'source': 'rectangle_pattern'
                    }
                    windows.append(window)
        
        return windows
    
    def _is_door_sized(self, width: float, height: float) -> bool:
        """Check if dimensions match typical door sizes"""
        # Standard door sizes (assuming inches)
        door_sizes = [
            (24, 80), (28, 80), (30, 80), (32, 80), (34, 80), (36, 80),  # Interior doors
            (32, 96), (36, 96), (42, 96), (48, 96)  # Exterior doors
        ]
        
        tolerance = 3  # inches
        
        for door_w, door_h in door_sizes:
            if (abs(width - door_w) <= tolerance and abs(height - door_h) <= tolerance) or \
               (abs(width - door_h) <= tolerance and abs(height - door_w) <= tolerance):
                return True
        
        return False
    
    def _is_window_sized(self, width: float, height: float) -> bool:
        """Check if dimensions match typical window sizes"""
        # Basic window size check - windows are typically smaller than doors
        # and have different aspect ratios
        return (12 <= width <= 96 and 12 <= height <= 72 and 
                not self._is_door_sized(width, height))
    
    def _calculate_polyline_bounds(self, points: List[Tuple[float, float]]) -> Dict:
        """Calculate bounds for a polyline"""
        if not points:
            return {'min_x': 0, 'max_x': 0, 'min_y': 0, 'max_y': 0}
        
        return {
            'min_x': min(p[0] for p in points),
            'max_x': max(p[0] for p in points),
            'min_y': min(p[1] for p in points),
            'max_y': max(p[1] for p in points)
        }
    
    def _find_nearby_wall_segments(self, center: Tuple[float, float], house_structure: Dict, radius: float) -> List[Dict]:
        """Find wall segments near a given point"""
        nearby_segments = []
        
        for segment in house_structure.get('segments', []):
            # Check distance from center to segment
            dist_to_start = self._distance(center, segment['start'])
            dist_to_end = self._distance(center, segment['end'])
            
            if dist_to_start <= radius or dist_to_end <= radius:
                nearby_segments.append(segment)
        
        return nearby_segments
    
    def _determine_door_layer_name(self, position: Tuple[float, float], house_structure: Dict) -> str:
        """Determine appropriate layer name for a door based on its position"""
        # For now, default to interior door
        # In a more sophisticated implementation, this would analyze position relative to walls
        return self.layer_naming['elements']['doors']['interior']
    
    def _determine_window_layer_name(self, position: Tuple[float, float], house_structure: Dict) -> str:
        """Determine appropriate layer name for a window based on its position"""
        # For now, default to side window
        return self.layer_naming['elements']['windows']['side']
    
    def _analyze_door_block(self, block: Dict) -> Optional[Dict]:
        """Analyze a door block to extract door information"""
        # This would analyze the block's geometry to extract door dimensions and properties
        # For now, return basic door info
        return {
            'type': 'block_door',
            'block_name': block.get('name', ''),
            'position': block.get('position', (0, 0)),
            'layer_name': self.layer_naming['elements']['doors']['interior'],
            'confidence': 0.8,
            'source': 'block'
        }
    
    def _analyze_window_block(self, block: Dict) -> Optional[Dict]:
        """Analyze a window block to extract window information"""
        # This would analyze the block's geometry to extract window dimensions and properties
        return {
            'type': 'block_window',
            'block_name': block.get('name', ''),
            'position': block.get('position', (0, 0)),
            'layer_name': self.layer_naming['elements']['windows']['side'],
            'confidence': 0.8,
            'source': 'block'
        }
    
    def _detect_wall_openings(self, entities: Dict, house_structure: Dict) -> List[Dict]:
        """Detect openings in walls that might be doors or windows"""
        # This would analyze wall segments for gaps that might indicate openings
        return []
    
    def _extract_measurements(self, entities: Dict, elements: Dict, wall_classification: Dict) -> Dict:
        """
        Extract measurements and dimensions from the DXF geometry
        """
        print("Extracting measurements and dimensions...")
        
        measurements = {
            'walls': [],
            'doors': [],
            'windows': [],
            'rooms': [],
            'total_area': 0,
            'perimeter_length': 0
        }
        
        # Extract wall measurements
        for classification in wall_classification.get('classifications', []):
            wall_measurement = {
                'wall_type': classification['wall_type'],
                'floor_type': classification['floor_type'],
                'layer_name': classification['layer_name'],
                'total_length': classification['total_length'],
                'segment_count': len(classification['segments']),
                'segments': []
            }
            
            # Measure individual segments
            for segment in classification['segments']:
                segment_measurement = {
                    'start': segment['start'],
                    'end': segment['end'],
                    'length': segment['length'],
                    'layer': segment['layer']
                }
                wall_measurement['segments'].append(segment_measurement)
            
            measurements['walls'].append(wall_measurement)
            
            if classification['is_exterior']:
                measurements['perimeter_length'] += classification['total_length']
        
        # Extract door measurements
        for door in elements.get('doors', []):
            door_measurement = {
                'type': door['type'],
                'layer_name': door['layer_name'],
                'width': door.get('width', 0),
                'height': door.get('height', 0),
                'position': door.get('center', door.get('position', (0, 0))),
                'area': door.get('width', 0) * door.get('height', 0) if door.get('width') and door.get('height') else 0
            }
            measurements['doors'].append(door_measurement)
        
        # Extract window measurements
        for window in elements.get('windows', []):
            window_measurement = {
                'type': window['type'],
                'layer_name': window['layer_name'],
                'width': window.get('width', 0),
                'height': window.get('height', 0),
                'position': window.get('center', window.get('position', (0, 0))),
                'area': window.get('width', 0) * window.get('height', 0) if window.get('width') and window.get('height') else 0
            }
            measurements['windows'].append(window_measurement)
        
        # Calculate total building area (simplified)
        # This would be enhanced to calculate actual room areas
        if house_structure := entities.get('building_bounds'):
            measurements['total_area'] = (house_structure.get('width', 0) * 
                                        house_structure.get('height', 0))
        
        print(f"Extracted measurements: {len(measurements['walls'])} walls, "
              f"{len(measurements['doors'])} doors, {len(measurements['windows'])} windows")
        
        return measurements
    
    def _enhance_with_ai(self, ai_analyzer, house_structure: Dict, wall_classification: Dict, 
                        elements: Dict, entities: Dict) -> Tuple[Dict, Dict, Dict]:
        """
        Enhance the analysis with AI insights
        """
        print("Enhancing analysis with AI...")
        
        try:
            # Prepare data for AI analysis
            analysis_data = {
                'house_structure': house_structure,
                'wall_classification': wall_classification,
                'elements': elements,
                'entity_summary': {
                    'lines': len(entities.get('lines', [])),
                    'polylines': len(entities.get('lwpolylines', [])) + len(entities.get('polylines', [])),
                    'arcs': len(entities.get('arcs', [])),
                    'circles': len(entities.get('circles', []))
                }
            }
            
            # Use AI to enhance classifications and detections
            enhanced_analysis = ai_analyzer.analyze_geometric_data(analysis_data, house_structure)
            
            # Apply AI enhancements
            if enhanced_analysis and isinstance(enhanced_analysis, dict):
                # Update classifications with AI insights
                ai_wall_classifications = enhanced_analysis.get('wall_classifications', [])
                for i, classification in enumerate(wall_classification.get('classifications', [])):
                    if i < len(ai_wall_classifications):
                        ai_class = ai_wall_classifications[i]
                        if ai_class.get('confidence', 0) > 0.7:
                            classification['ai_enhanced'] = True
                            classification['ai_confidence'] = ai_class.get('confidence', 0)
                
                # Update element detections with AI insights
                ai_elements = enhanced_analysis.get('elements', {})
                for element_type in ['doors', 'windows']:
                    if element_type in ai_elements:
                        elements[element_type].extend(ai_elements[element_type])
            
            print("AI enhancement completed successfully")
            
        except Exception as e:
            print(f"AI enhancement failed: {e}. Continuing with geometric analysis.")
        
        return house_structure, wall_classification, elements
    
    def _segments_to_polylines(self, segments: List[Dict]) -> List[List[Tuple[float, float]]]:
        """
        Convert a list of line segments into continuous polylines for boundary tracing.
        This groups connected segments into continuous paths.
        """
        if not segments:
            return []
        
        polylines = []
        used_segments = set()
        tolerance = 2.0  # Connection tolerance in units
        
        for i, segment in enumerate(segments):
            if i in used_segments:
                continue
            
            # Start a new polyline with this segment
            polyline = [segment['start'], segment['end']]
            used_segments.add(i)
            
            # Try to extend the polyline by finding connected segments
            extended = True
            while extended:
                extended = False
                last_point = polyline[-1]
                first_point = polyline[0]
                
                # Look for segments that connect to either end of the current polyline
                for j, other_segment in enumerate(segments):
                    if j in used_segments:
                        continue
                    
                    other_start = other_segment['start']
                    other_end = other_segment['end']
                    
                    # Check if this segment connects to the end of our polyline
                    if self._points_are_close(last_point, other_start, tolerance):
                        polyline.append(other_end)
                        used_segments.add(j)
                        extended = True
                        break
                    elif self._points_are_close(last_point, other_end, tolerance):
                        polyline.append(other_start)
                        used_segments.add(j)
                        extended = True
                        break
                    # Check if this segment connects to the beginning of our polyline
                    elif self._points_are_close(first_point, other_end, tolerance):
                        polyline.insert(0, other_start)
                        used_segments.add(j)
                        extended = True
                        break
                    elif self._points_are_close(first_point, other_start, tolerance):
                        polyline.insert(0, other_end)
                        used_segments.add(j)
                        extended = True
                        break
            
            polylines.append(polyline)
        
        return polylines
    
    def _points_are_close(self, point1: Tuple[float, float], point2: Tuple[float, float], tolerance: float) -> bool:
        """Check if two points are within tolerance distance"""
        dx = point1[0] - point2[0]
        dy = point1[1] - point2[1]
        distance = math.sqrt(dx*dx + dy*dy)
        return distance <= tolerance
    
    def _generate_drawing_commands(self, house_structure: Dict, wall_classification: Dict, elements: Dict) -> List[Dict]:
        """
        Generate drawing commands for AutoCAD layer creation and geometry drawing.
        This creates continuous boundary traces for outer and inner boundaries.
        """
        print("Generating drawing commands for boundary highlighting...")
        
        commands = []
        
        # Generate commands for wall boundaries - draw as continuous polylines
        for classification in wall_classification.get('classifications', []):
            layer_name = classification['layer_name']
            color = classification['color']
            wall_type = classification.get('wall_type', 'interior')
            
            # Create layer command
            commands.append({
                'action': 'create_layer',
                'layer_name': layer_name,
                'color': color,
                'linetype': 'CONTINUOUS'
            })
            
            # Convert segments to continuous polylines for boundary highlighting
            polylines = self._segments_to_polylines(classification['segments'])
            
            # Draw each continuous boundary as a polyline
            for polyline_points in polylines:
                if len(polyline_points) >= 2:
                    commands.append({
                        'action': 'draw_polyline',
                        'coordinates': polyline_points,
                        'layer_name': layer_name,
                        'closed': False
                    })
                    
            print(f"  Created {len(polylines)} continuous {'outer' if wall_type == 'exterior' else 'inner'} boundary traces on layer '{layer_name}'")
        
        # Generate commands for elements
        for element_type in ['doors', 'windows']:
            for element in elements.get(element_type, []):
                layer_name = element['layer_name']
                color = element['color']
                
                # Create layer command
                commands.append({
                    'action': 'create_layer',
                    'layer_name': layer_name,
                    'color': color,
                    'linetype': 'CONTINUOUS'
                })
                
                # Draw element
                if element['type'] == 'swing_door' and 'center' in element and 'radius' in element:
                    commands.append({
                        'action': 'draw_arc',
                        'center': element['center'],
                        'radius': element['radius'],
                        'start_angle': 0,
                        'end_angle': 90,
                        'layer_name': layer_name
                    })
                elif 'bounds' in element:
                    commands.append({
                        'action': 'draw_rectangle',
                        'point1': (element['bounds']['min_x'], element['bounds']['min_y']),
                        'point2': (element['bounds']['max_x'], element['bounds']['max_y']),
                        'layer_name': layer_name
                    })
        
        print(f"Generated {len(commands)} drawing commands")
        return commands
    
    def _format_results(self, house_structure: Dict, wall_classification: Dict, 
                       elements: Dict, measurements: Dict, drawing_commands: List[Dict]) -> Dict:
        """
        Format the results in the expected output format
        """
        # Count total elements for reporting
        total_elements = (len(elements.get('doors', [])) + 
                         len(elements.get('windows', [])) + 
                         len(elements.get('openings', [])))
        
        # Extract layer names for reporting
        layers_created = list(set(
            [cmd['layer_name'] for cmd in drawing_commands if cmd['action'] == 'create_layer']
        ))
        
        return {
            'success': True,
            'drawing_type': 'floor_plan',  # Determined from analysis
            'analysis_method': 'enhanced_geometry_processing',
            'spaces': [
                {
                    'type': classification['wall_type'],
                    'floor_type': classification['floor_type'],
                    'layer_name': classification['layer_name'],
                    'coordinates': [seg['start'] + seg['end'] for seg in classification['segments']],
                    'total_length': classification['total_length'],
                    'confidence': classification.get('confidence', 0.8)
                }
                for classification in wall_classification.get('classifications', [])
            ],
            'elements': [
                {
                    'type': element['type'],
                    'layer_name': element['layer_name'],
                    'position': element.get('center', element.get('position', (0, 0))),
                    'dimensions': {
                        'width': element.get('width', 0),
                        'height': element.get('height', 0)
                    },
                    'confidence': element.get('confidence', 0.8)
                }
                for element_type in ['doors', 'windows', 'openings']
                for element in elements.get(element_type, [])
            ],
            'layers_created': layers_created,
            'elements_detected': total_elements,
            'measurements': measurements,
            'drawing_commands': drawing_commands,
            'analysis_metadata': {
                'outline_detected': house_structure.get('outline_detected', False),
                'total_wall_groups': len(wall_classification.get('classifications', [])),
                'perimeter_length': measurements.get('perimeter_length', 0),
                'total_area': measurements.get('total_area', 0),
                'processing_method': 'enhanced_dxf_geometry'
            }
        }
    
    def _create_enhanced_fallback(self) -> Dict:
        """
        Create a fallback response when no geometry is detected
        """
        return {
            'success': False,
            'error': 'No valid geometry detected in DXF file',
            'drawing_type': 'unknown',
            'analysis_method': 'enhanced_geometry_processing',
            'spaces': [],
            'elements': [],
            'layers_created': [],
            'elements_detected': 0,
            'measurements': {
                'walls': [], 'doors': [], 'windows': [], 'rooms': [],
                'total_area': 0, 'perimeter_length': 0
            },
            'drawing_commands': [],
            'analysis_metadata': {
                'outline_detected': False,
                'total_wall_groups': 0,
                'processing_method': 'enhanced_dxf_geometry',
                'fallback_reason': 'no_geometry_detected'
            }
        }
    
    def export_measurements_csv(self, measurements: Dict, output_path: str) -> bool:
        """
        Export measurements to CSV format
        """
        try:
            import csv
            
            with open(output_path, 'w', newline='') as csvfile:
                writer = csv.writer(csvfile)
                
                # Write headers
                writer.writerow(['Element Type', 'Layer Name', 'Width', 'Height', 'Length', 'Area', 'Position X', 'Position Y'])
                
                # Write wall measurements
                for wall in measurements.get('walls', []):
                    for segment in wall['segments']:
                        writer.writerow([
                            f"Wall ({wall['wall_type']})",
                            wall['layer_name'],
                            '',  # Width
                            '',  # Height
                            segment['length'],
                            '',  # Area
                            segment['start'][0],
                            segment['start'][1]
                        ])
                
                # Write door measurements
                for door in measurements.get('doors', []):
                    writer.writerow([
                        'Door',
                        door['layer_name'],
                        door['width'],
                        door['height'],
                        '',  # Length
                        door['area'],
                        door['position'][0],
                        door['position'][1]
                    ])
                
                # Write window measurements
                for window in measurements.get('windows', []):
                    writer.writerow([
                        'Window',
                        window['layer_name'],
                        window['width'],
                        window['height'],
                        '',  # Length
                        window['area'],
                        window['position'][0],
                        window['position'][1]
                    ])
            
            print(f"Measurements exported to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting measurements to CSV: {e}")
            return False
    
    def export_measurements_json(self, measurements: Dict, output_path: str) -> bool:
        """
        Export measurements to JSON format
        """
        try:
            with open(output_path, 'w') as jsonfile:
                json.dump(measurements, jsonfile, indent=2)
            
            print(f"Measurements exported to {output_path}")
            return True
            
        except Exception as e:
            print(f"Error exporting measurements to JSON: {e}")
            return False