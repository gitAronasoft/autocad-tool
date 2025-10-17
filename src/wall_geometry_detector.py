import numpy as np
from typing import List, Dict, Tuple, Optional
import math
from collections import defaultdict

class WallGeometryDetector:
    """
    Detect wall boundaries from extracted vector geometry by finding parallel line pairs
    that represent wall thickness (inner and outer edges)
    """
    
    def __init__(self, wall_thickness_min: float = 3.0, wall_thickness_max: float = 30.0):
        """
        Initialize wall detector with thickness tolerances
        
        Args:
            wall_thickness_min: Minimum wall thickness in DXF units (default 3.0)
            wall_thickness_max: Maximum wall thickness in DXF units (default 30.0)
        """
        self.wall_thickness_min = wall_thickness_min
        self.wall_thickness_max = wall_thickness_max
        self.parallel_tolerance = 5.0  # degrees
        self.lines = []
    
    def extract_lines_from_dxf(self, dxf_doc, layer_name: str = "ORIGINAL_DRAWING") -> List[Dict]:
        """
        Extract all line entities from a DXF document
        
        Returns:
            List of line dictionaries with start, end, angle, length
        """
        lines = []
        modelspace = dxf_doc.modelspace()
        
        for entity in modelspace:
            if entity.dxftype() == 'LINE' and entity.dxf.layer == layer_name:
                start = (entity.dxf.start.x, entity.dxf.start.y)
                end = (entity.dxf.end.x, entity.dxf.end.y)
                
                # Calculate line properties
                dx = end[0] - start[0]
                dy = end[1] - start[1]
                length = math.sqrt(dx**2 + dy**2)
                
                if length > 0.1:  # Ignore very short lines
                    angle = math.degrees(math.atan2(dy, dx))
                    # Normalize angle to 0-180
                    if angle < 0:
                        angle += 180
                    
                    lines.append({
                        'start': start,
                        'end': end,
                        'length': length,
                        'angle': angle,
                        'midpoint': ((start[0] + end[0]) / 2, (start[1] + end[1]) / 2)
                    })
        
        self.lines = lines
        print(f"Extracted {len(lines)} line entities from DXF")
        return lines
    
    def find_parallel_line_pairs(self) -> List[Tuple[Dict, Dict, float]]:
        """
        Find pairs of parallel lines that could represent wall edges
        
        Returns:
            List of (line1, line2, distance) tuples
        """
        parallel_pairs = []
        
        # Group lines by angle (within tolerance)
        angle_groups = defaultdict(list)
        for line in self.lines:
            angle_key = round(line['angle'] / self.parallel_tolerance) * self.parallel_tolerance
            angle_groups[angle_key].append(line)
        
        print(f"Grouped lines into {len(angle_groups)} angle groups")
        
        # For each angle group, find parallel pairs
        for angle_key, group_lines in angle_groups.items():
            if len(group_lines) < 2:
                continue
            
            # Check each pair in the group
            for i in range(len(group_lines)):
                for j in range(i + 1, len(group_lines)):
                    line1 = group_lines[i]
                    line2 = group_lines[j]
                    
                    # Calculate perpendicular distance between parallel lines
                    distance = self._perpendicular_distance(line1, line2)
                    
                    # Check if distance is within wall thickness range
                    if self.wall_thickness_min <= distance <= self.wall_thickness_max:
                        # Check if lines overlap (are adjacent)
                        if self._lines_overlap(line1, line2):
                            parallel_pairs.append((line1, line2, distance))
        
        print(f"Found {len(parallel_pairs)} parallel line pairs (potential walls)")
        return parallel_pairs
    
    def _perpendicular_distance(self, line1: Dict, line2: Dict) -> float:
        """Calculate perpendicular distance between two parallel lines"""
        # Use midpoints to calculate distance
        p1 = line1['midpoint']
        p2 = line2['midpoint']
        
        # Calculate distance
        dist = math.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
        
        # Adjust for angle - we want perpendicular distance
        angle_diff = abs(line1['angle'] - line2['angle'])
        if angle_diff > 90:
            angle_diff = 180 - angle_diff
        
        # If lines are truly parallel, use projection
        angle_rad = math.radians(line1['angle'])
        perpendicular_angle = angle_rad + math.pi / 2
        
        # Project distance onto perpendicular direction
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        perp_dist = abs(dx * math.sin(angle_rad) - dy * math.cos(angle_rad))
        
        return perp_dist
    
    def _lines_overlap(self, line1: Dict, line2: Dict) -> bool:
        """Check if two lines overlap along their direction (are adjacent)"""
        # Project line endpoints onto a common axis
        angle_rad = math.radians(line1['angle'])
        
        # Project line1 endpoints
        l1_s = line1['start'][0] * math.cos(angle_rad) + line1['start'][1] * math.sin(angle_rad)
        l1_e = line1['end'][0] * math.cos(angle_rad) + line1['end'][1] * math.sin(angle_rad)
        l1_min, l1_max = min(l1_s, l1_e), max(l1_s, l1_e)
        
        # Project line2 endpoints
        l2_s = line2['start'][0] * math.cos(angle_rad) + line2['start'][1] * math.sin(angle_rad)
        l2_e = line2['end'][0] * math.cos(angle_rad) + line2['end'][1] * math.sin(angle_rad)
        l2_min, l2_max = min(l2_s, l2_e), max(l2_s, l2_e)
        
        # Check for overlap with some tolerance
        tolerance = 5.0  # Allow small gaps
        overlap = max(0, min(l1_max, l2_max) - max(l1_min, l2_min) + tolerance)
        
        return overlap > 0
    
    def trace_wall_boundaries(self, parallel_pairs: List[Tuple[Dict, Dict, float]]) -> Dict:
        """
        Convert parallel line pairs into inner and outer boundary polylines
        by collecting all lines and creating continuous paths
        
        Returns:
            Dictionary with 'inner_boundaries' and 'outer_boundaries' as list of polylines
        """
        if not parallel_pairs:
            print("No parallel pairs to trace")
            return {'inner_boundaries': [], 'outer_boundaries': []}
        
        print(f"Processing {len(parallel_pairs)} parallel line pairs...")
        
        # Separate all inner and outer edge lines
        inner_lines = []
        outer_lines = []
        
        for line1, line2, distance in parallel_pairs:
            # Use distance from origin to determine which is inner vs outer
            dist1 = math.sqrt(line1['midpoint'][0]**2 + line1['midpoint'][1]**2)
            dist2 = math.sqrt(line2['midpoint'][0]**2 + line2['midpoint'][1]**2)
            
            if dist1 > dist2:
                outer_lines.append(line1)
                inner_lines.append(line2)
            else:
                outer_lines.append(line2)
                inner_lines.append(line1)
        
        # Build continuous paths from line segments
        inner_paths = self._build_continuous_paths(inner_lines)
        outer_paths = self._build_continuous_paths(outer_lines)
        
        print(f"Built {len(inner_paths)} inner paths and {len(outer_paths)} outer paths")
        
        # Convert paths to boundary polylines (only keep closed loops or long paths)
        inner_boundaries = []
        outer_boundaries = []
        
        for path in inner_paths:
            if len(path) >= 4:  # Minimum points for a meaningful boundary
                inner_boundaries.append(path)
        
        for path in outer_paths:
            if len(path) >= 4:
                outer_boundaries.append(path)
        
        print(f"Created {len(inner_boundaries)} inner boundaries and {len(outer_boundaries)} outer boundaries")
        
        return {
            'inner_boundaries': inner_boundaries,
            'outer_boundaries': outer_boundaries
        }
    
    def _build_continuous_paths(self, lines: List[Dict], max_gap: float = 5.0) -> List[List[Tuple[float, float]]]:
        """
        Build continuous paths from a collection of line segments
        Connects lines that share endpoints (within tolerance)
        """
        if not lines:
            return []
        
        paths = []
        used_lines = set()
        
        # Try to build paths starting from each unused line
        for start_idx, start_line in enumerate(lines):
            if start_idx in used_lines:
                continue
            
            # Start a new path
            path = [start_line['start'], start_line['end']]
            used_lines.add(start_idx)
            
            # Try to extend the path by finding connected lines
            extended = True
            while extended:
                extended = False
                current_end = path[-1]
                
                # Look for a line that starts near the current end
                for idx, line in enumerate(lines):
                    if idx in used_lines:
                        continue
                    
                    # Check if this line connects to the path end
                    dist_to_start = math.sqrt((line['start'][0] - current_end[0])**2 + 
                                            (line['start'][1] - current_end[1])**2)
                    dist_to_end = math.sqrt((line['end'][0] - current_end[0])**2 + 
                                          (line['end'][1] - current_end[1])**2)
                    
                    if dist_to_start <= max_gap:
                        # Line starts at path end
                        path.append(line['end'])
                        used_lines.add(idx)
                        extended = True
                        break
                    elif dist_to_end <= max_gap:
                        # Line ends at path end (reverse direction)
                        path.append(line['start'])
                        used_lines.add(idx)
                        extended = True
                        break
            
            # Check if path closes (forms a loop)
            if len(path) >= 4:
                first_point = path[0]
                last_point = path[-1]
                closure_dist = math.sqrt((last_point[0] - first_point[0])**2 + 
                                        (last_point[1] - first_point[1])**2)
                
                if closure_dist <= max_gap:
                    # Close the path
                    path.append(first_point)
            
            if len(path) >= 4:
                paths.append(path)
        
        return paths
    
    def _group_wall_segments(self, parallel_pairs: List[Tuple[Dict, Dict, float]]) -> List[List[Tuple]]:
        """Group parallel line pairs into connected wall segments - DEPRECATED"""
        # This method is no longer used - see trace_wall_boundaries instead
        return []
    
    def _create_polyline(self, points: List[Tuple[float, float]]) -> List[Tuple[float, float]]:
        """
        Create an ordered polyline from a list of points
        Remove duplicates and order by connectivity
        """
        if not points:
            return []
        
        # Remove near-duplicate points
        unique_points = []
        tolerance = 1.0
        
        for point in points:
            is_duplicate = False
            for existing in unique_points:
                dist = math.sqrt((point[0] - existing[0])**2 + (point[1] - existing[1])**2)
                if dist < tolerance:
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_points.append(point)
        
        return unique_points
    
    def classify_exterior_interior(self, boundaries: Dict) -> Dict:
        """
        Classify boundaries as exterior (outer perimeter) or interior (room dividers)
        Based on polygon area and nesting
        
        Returns:
            Dictionary with 'exterior' and 'interior' boundary lists
        """
        all_boundaries = boundaries.get('outer_boundaries', []) + boundaries.get('inner_boundaries', [])
        
        if not all_boundaries:
            return {'exterior': [], 'interior': []}
        
        # Calculate areas
        boundary_areas = []
        for boundary in all_boundaries:
            area = self._calculate_polygon_area(boundary)
            boundary_areas.append((boundary, area))
        
        # Sort by area (largest first)
        boundary_areas.sort(key=lambda x: abs(x[1]), reverse=True)
        
        # Largest boundaries are likely exterior
        # Take top 20% as exterior, rest as interior
        split_idx = max(1, len(boundary_areas) // 5)
        
        exterior = [b[0] for b in boundary_areas[:split_idx]]
        interior = [b[0] for b in boundary_areas[split_idx:]]
        
        print(f"Classified {len(exterior)} exterior boundaries and {len(interior)} interior boundaries")
        
        return {
            'exterior': exterior,
            'interior': interior
        }
    
    def _calculate_polygon_area(self, points: List[Tuple[float, float]]) -> float:
        """Calculate polygon area using shoelace formula"""
        if len(points) < 3:
            return 0
        
        area = 0
        for i in range(len(points)):
            j = (i + 1) % len(points)
            area += points[i][0] * points[j][1]
            area -= points[j][0] * points[i][1]
        
        return abs(area) / 2
