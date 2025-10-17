"""
AdvancedWallDetector - High-fidelity wall boundary detection preserving all geometry
Retains all path vertices including curves and properly identifies parallel wall pairs
"""
import logging
import numpy as np
from scipy.spatial import KDTree
from collections import defaultdict

logger = logging.getLogger(__name__)


class AdvancedWallDetector:
    """High-fidelity wall detection preserving all vector geometry"""
    
    def __init__(self):
        self.wall_threshold_width = 0.2
        self.snap_tolerance = 0.5  # Very tight snapping for vertex precision
        
    def detect_walls(self, vector_paths: list, page_width: float, page_height: float) -> dict:
        """Extract high-fidelity wall boundaries from PDF vectors"""
        logger.info(f"Analyzing {len(vector_paths)} vector paths for walls (high-fidelity mode)...")
        
        # Step 1: Extract ALL vertices from wall paths (including curves, polylines, etc.)
        all_vertices, wall_paths = self._extract_all_wall_geometry(vector_paths)
        logger.info(f"  Extracted {len(all_vertices)} unique vertices from {len(wall_paths)} wall paths")
        
        if not all_vertices:
            return {'exterior_outer': [], 'exterior_inner': [], 'interior_walls': []}
        
        # Step 2: Build vertex graph and trace closed loops
        boundaries = self._trace_closed_loops(all_vertices, wall_paths)
        logger.info(f"  Traced {len(boundaries)} closed boundary loops")
        
        # Step 3: Identify outer/inner walls using geometric analysis
        result = self._classify_wall_boundaries(boundaries, page_width, page_height)
        
        logger.info(f"  Exterior outer: {len(result['exterior_outer'])} points")
        logger.info(f"  Exterior inner: {len(result['exterior_inner'])} points")
        logger.info(f"  Interior walls: {len(result['interior_walls'])} boundaries")
        
        return result
    
    def _extract_all_wall_geometry(self, vector_paths: list) -> tuple:
        """Extract ALL vertices from wall paths, preserving curves and polylines"""
        all_vertices = []
        wall_paths_data = []
        
        for path in vector_paths:
            stroke_color = path.get('color')
            width = path.get('width', 0)
            
            # Filter for wall paths (black strokes with width)
            is_black = (stroke_color == (0.0, 0.0, 0.0) or stroke_color == [0.0, 0.0, 0.0])
            has_width = width is not None and width >= self.wall_threshold_width
            
            if not (is_black and has_width):
                continue
            
            # Extract ALL vertices from this path
            path_vertices = []
            items = path.get('items', [])
            current_pos = None
            
            for item in items:
                if not item or len(item) == 0:
                    continue
                
                item_type = item[0]
                
                # Move command - update position
                if item_type == 'm' and len(item) > 1:
                    point = self._extract_point(item[1])
                    if point:
                        current_pos = point
                        path_vertices.append(point)
                
                # Line command - add both endpoints
                elif item_type == 'l' and len(item) >= 3:
                    p1 = self._extract_point(item[1])
                    p2 = self._extract_point(item[2])
                    if p1 and p2:
                        path_vertices.extend([p1, p2])
                        current_pos = p2
                
                # Curve command - add ALL control points
                elif item_type == 'c' and len(item) > 1:
                    for i in range(1, len(item)):
                        point = self._extract_point(item[i])
                        if point:
                            path_vertices.append(point)
                            current_pos = point
                
                # Quadratic bezier - add control points
                elif item_type == 'qu' and len(item) > 1:
                    for i in range(1, len(item)):
                        point = self._extract_point(item[i])
                        if point:
                            path_vertices.append(point)
                            current_pos = point
                
                # Rectangle - add all 4 corners
                elif item_type == 're' and len(item) > 1:
                    rect = item[1]
                    if hasattr(rect, 'x0'):
                        x, y, w, h = rect.x0, rect.y0, rect.width, rect.height
                    elif isinstance(rect, (tuple, list)) and len(rect) >= 4:
                        x, y, w, h = rect[:4]
                    else:
                        continue
                    
                    corners = [
                        (x, y), (x + w, y),
                        (x + w, y + h), (x, y + h)
                    ]
                    path_vertices.extend(corners)
                
                # Close path - connect back to start
                elif item_type == 'h':
                    if path_vertices and len(path_vertices) > 0:
                        path_vertices.append(path_vertices[0])
            
            if path_vertices:
                all_vertices.extend(path_vertices)
                wall_paths_data.append({
                    'vertices': path_vertices,
                    'width': width
                })
        
        # Remove duplicate vertices (snap nearby points)
        unique_vertices = self._snap_vertices(all_vertices)
        return unique_vertices, wall_paths_data
    
    def _extract_point(self, point_data):
        """Extract (x, y) coordinates from various point formats"""
        if hasattr(point_data, 'x') and hasattr(point_data, 'y'):
            return (point_data.x, point_data.y)
        elif isinstance(point_data, (tuple, list)) and len(point_data) >= 2:
            return (point_data[0], point_data[1])
        return None
    
    def _snap_vertices(self, vertices: list) -> list:
        """Snap nearby vertices together to remove duplicates"""
        if not vertices:
            return []
        
        # Build KD-tree for fast nearest neighbor search
        vertices_array = np.array(vertices)
        tree = KDTree(vertices_array)
        
        # Find clusters of nearby vertices
        visited = set()
        unique_vertices = []
        
        for i, vertex in enumerate(vertices):
            if i in visited:
                continue
            
            # Find all vertices within snap tolerance
            indices = tree.query_ball_point(vertex, self.snap_tolerance)
            
            # Average their positions to get snapped vertex
            cluster_points = vertices_array[indices]
            snapped = tuple(cluster_points.mean(axis=0))
            unique_vertices.append(snapped)
            
            # Mark all as visited
            visited.update(indices)
        
        return unique_vertices
    
    def _trace_closed_loops(self, vertices: list, wall_paths: list) -> list:
        """Trace closed boundary loops from wall path vertices"""
        boundaries = []
        
        # Each wall path is already a sequence of connected vertices
        # We just need to identify which ones form closed loops
        for path_data in wall_paths:
            path_vertices = path_data['vertices']
            
            if len(path_vertices) < 3:
                continue
            
            # Check if path is closed (first and last points are close)
            first = path_vertices[0]
            last = path_vertices[-1]
            dist = np.sqrt((first[0] - last[0])**2 + (first[1] - last[1])**2)
            
            if dist < self.snap_tolerance * 3:
                # Closed loop - use all vertices
                boundaries.append(path_vertices)
            else:
                # Open path - still include if it has enough vertices
                if len(path_vertices) >= 5:
                    boundaries.append(path_vertices)
        
        return boundaries
    
    def _classify_wall_boundaries(self, boundaries: list, page_width: float, page_height: float) -> dict:
        """Classify boundaries using perimeter length - longest boundaries are exterior walls"""
        if not boundaries:
            return {'exterior_outer': [], 'exterior_inner': [], 'interior_walls': []}
        
        # Calculate properties for each boundary
        boundary_info = []
        for boundary in boundaries:
            if len(boundary) < 3:
                continue
            
            # Calculate perimeter (total path length)
            perimeter = 0
            for i in range(len(boundary)):
                p1 = boundary[i]
                p2 = boundary[(i + 1) % len(boundary)]
                perimeter += np.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
            
            # Calculate bounding box
            xs = [p[0] for p in boundary]
            ys = [p[1] for p in boundary]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            boundary_info.append({
                'points': boundary,
                'perimeter': perimeter,
                'num_points': len(boundary),
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y
            })
        
        # Sort by combined metric: perimeter * sqrt(num_points)
        # This favors boundaries with BOTH long perimeter AND high detail
        boundary_info.sort(key=lambda b: b['perimeter'] * np.sqrt(b['num_points']), reverse=True)
        
        result = {
            'exterior_outer': [],
            'exterior_inner': [],
            'interior_walls': []
        }
        
        if len(boundary_info) >= 2:
            # Outer = longest perimeter boundary
            outer = boundary_info[0]
            result['exterior_outer'] = outer['points']
            
            # Inner = second longest boundary that's inside outer
            for candidate in boundary_info[1:]:
                # Check if inside outer (with tolerance)
                is_inside = (
                    candidate['min_x'] >= outer['min_x'] - 10 and
                    candidate['max_x'] <= outer['max_x'] + 10 and
                    candidate['min_y'] >= outer['min_y'] - 10 and
                    candidate['max_y'] <= outer['max_y'] + 10
                )
                
                # Must have significant perimeter (at least 40% of outer)
                is_significant = candidate['perimeter'] > outer['perimeter'] * 0.4
                
                if is_inside and is_significant:
                    result['exterior_inner'] = candidate['points']
                    # Rest are interior
                    for other in boundary_info[2:]:
                        if other is not candidate:
                            result['interior_walls'].append(other['points'])
                    break
            
            # If no suitable inner found, offset outer inward
            if not result['exterior_inner']:
                result['exterior_inner'] = self._offset_boundary_inward(outer['points'], offset=5.0)
        
        elif len(boundary_info) == 1:
            # Only one boundary - use as outer, offset for inner
            result['exterior_outer'] = boundary_info[0]['points']
            result['exterior_inner'] = self._offset_boundary_inward(boundary_info[0]['points'], offset=5.0)
        
        return result
    
    def _offset_boundary_inward(self, boundary: list, offset: float) -> list:
        """Offset a boundary inward by a fixed distance"""
        if len(boundary) < 3:
            return []
        
        offset_points = []
        
        for i in range(len(boundary)):
            # Get three consecutive points (with wrapping)
            p_prev = boundary[(i - 1) % len(boundary)]
            p_curr = boundary[i]
            p_next = boundary[(i + 1) % len(boundary)]
            
            # Calculate inward normal at current point
            dx1 = p_curr[0] - p_prev[0]
            dy1 = p_curr[1] - p_prev[1]
            len1 = np.sqrt(dx1**2 + dy1**2) or 1.0
            
            dx2 = p_next[0] - p_curr[0]
            dy2 = p_next[1] - p_curr[1]
            len2 = np.sqrt(dx2**2 + dy2**2) or 1.0
            
            # Perpendicular vectors (inward - rotate 90° clockwise for outer boundary)
            norm1_x = dy1 / len1
            norm1_y = -dx1 / len1
            
            norm2_x = dy2 / len2
            norm2_y = -dx2 / len2
            
            # Average normal
            avg_norm_x = (norm1_x + norm2_x) / 2
            avg_norm_y = (norm1_y + norm2_y) / 2
            avg_len = np.sqrt(avg_norm_x**2 + avg_norm_y**2) or 1.0
            
            # Offset point inward
            offset_x = p_curr[0] + (avg_norm_x / avg_len) * offset
            offset_y = p_curr[1] + (avg_norm_y / avg_len) * offset
            
            offset_points.append((offset_x, offset_y))
        
        return offset_points
