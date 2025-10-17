"""
ParallelWallDetector - Detects parallel outer/inner wall boundaries from PDF vectors
Properly identifies double-line walls common in architectural drawings
"""
import logging
import numpy as np
from collections import defaultdict
from scipy.spatial import KDTree

logger = logging.getLogger(__name__)


class ParallelWallDetector:
    """Detects parallel wall boundaries (outer and inner) from PDF line segments"""
    
    def __init__(self):
        self.wall_threshold_width = 0.2
        self.snap_tolerance = 1.0  # Tolerance for connecting nearby segments
        self.parallel_tolerance = 2.0  # Distance threshold for parallel walls (typically 4-8 inches in architectural drawings)
        
    def detect_walls(self, vector_paths: list, page_width: float, page_height: float) -> dict:
        """Extract parallel outer/inner wall boundaries from PDF vectors"""
        logger.info(f"Detecting parallel wall boundaries from {len(vector_paths)} vector paths...")
        
        # Step 1: Extract all wall line segments
        segments = self._extract_wall_segments(vector_paths)
        logger.info(f"  Extracted {len(segments)} wall line segments")
        
        if len(segments) < 4:
            return {'exterior_outer': [], 'exterior_inner': [], 'interior_walls': []}
        
        # Step 2: Classify segments by proximity to page edges
        edge_margin = min(page_width, page_height) * 0.1
        exterior_segments = []
        interior_segments = []
        
        for seg in segments:
            x1, y1, x2, y2 = seg
            min_x = min(x1, x2)
            max_x = max(x1, x2)
            min_y = min(y1, y2)
            max_y = max(y1, y2)
            
            # Check if segment is near page edges (likely exterior wall)
            near_edge = (
                min_x < edge_margin or 
                max_x > page_width - edge_margin or
                min_y < edge_margin or
                max_y > page_height - edge_margin
            )
            
            if near_edge:
                exterior_segments.append(seg)
            else:
                interior_segments.append(seg)
        
        logger.info(f"  Classified: {len(exterior_segments)} exterior, {len(interior_segments)} interior segments")
        
        # Step 3: Find outer perimeter from exterior segments
        outer_boundary = self._trace_perimeter(exterior_segments, 'outer', page_width, page_height)
        
        # Step 4: Find inner perimeter (parallel to outer, offset inward)
        inner_boundary = self._find_parallel_inner_boundary(outer_boundary, segments, page_width, page_height)
        
        logger.info(f"  Outer boundary: {len(outer_boundary)} points")
        logger.info(f"  Inner boundary: {len(inner_boundary)} points")
        
        return {
            'exterior_outer': outer_boundary,
            'exterior_inner': inner_boundary,
            'interior_walls': []
        }
    
    def _extract_wall_segments(self, vector_paths: list) -> list:
        """Extract all wall line segments from vector paths"""
        segments = []
        
        for path in vector_paths:
            stroke_color = path.get('color')
            width = path.get('width', 0)
            
            # Filter for wall paths (black strokes with width)
            is_black = (stroke_color == (0.0, 0.0, 0.0) or stroke_color == [0.0, 0.0, 0.0])
            has_width = width is not None and width >= self.wall_threshold_width
            
            if not (is_black and has_width):
                continue
            
            # Extract line segments from this path
            items = path.get('items', [])
            current_pos = None
            
            for item in items:
                if not item or len(item) == 0:
                    continue
                
                item_type = item[0]
                
                # Move command
                if item_type == 'm' and len(item) > 1:
                    point = self._extract_point(item[1])
                    if point:
                        current_pos = point
                
                # Line command - add segment
                elif item_type == 'l' and len(item) >= 3:
                    p1 = self._extract_point(item[1])
                    p2 = self._extract_point(item[2])
                    if p1 and p2:
                        segments.append((p1[0], p1[1], p2[0], p2[1]))
                        current_pos = p2
                
                # Rectangle - add 4 segments
                elif item_type == 're' and len(item) > 1:
                    rect = item[1]
                    if hasattr(rect, 'x0'):
                        x, y, w, h = rect.x0, rect.y0, rect.width, rect.height
                    elif isinstance(rect, (tuple, list)) and len(rect) >= 4:
                        x, y, w, h = rect[:4]
                    else:
                        continue
                    
                    # Add 4 edges of rectangle
                    segments.append((x, y, x + w, y))  # bottom
                    segments.append((x + w, y, x + w, y + h))  # right
                    segments.append((x + w, y + h, x, y + h))  # top
                    segments.append((x, y + h, x, y))  # left
        
        return segments
    
    def _extract_point(self, point_data):
        """Extract (x, y) coordinates from various point formats"""
        if hasattr(point_data, 'x') and hasattr(point_data, 'y'):
            return (point_data.x, point_data.y)
        elif isinstance(point_data, (tuple, list)) and len(point_data) >= 2:
            return (point_data[0], point_data[1])
        return None
    
    def _trace_perimeter(self, segments: list, boundary_type: str, page_width: float, page_height: float) -> list:
        """Trace a perimeter boundary from segments using graph traversal"""
        if not segments:
            return []
        
        # Build endpoint graph
        endpoints = defaultdict(list)
        for x1, y1, x2, y2 in segments:
            # Snap endpoints to grid to handle floating point precision
            p1 = (round(x1 * 2) / 2, round(y1 * 2) / 2)
            p2 = (round(x2 * 2) / 2, round(y2 * 2) / 2)
            endpoints[p1].append(p2)
            endpoints[p2].append(p1)
        
        # Find starting point (for outer: closest to top-left corner)
        if boundary_type == 'outer':
            start = min(endpoints.keys(), key=lambda p: p[0]**2 + p[1]**2)
        else:
            start = min(endpoints.keys(), key=lambda p: (p[0] - page_width/2)**2 + (p[1] - page_height/2)**2)
        
        # Trace boundary using rightmost turn algorithm (follows outer edge)
        boundary = [start]
        current = start
        visited_edges = set()
        
        for _ in range(len(segments) * 2):  # Prevent infinite loops
            neighbors = endpoints.get(current, [])
            if not neighbors:
                break
            
            # Filter out already visited edges
            unvisited = [n for n in neighbors if (current, n) not in visited_edges]
            if not unvisited:
                break
            
            # Choose next point (prefer continuing in same general direction)
            if len(boundary) >= 2:
                # Calculate direction from previous segment
                prev = boundary[-2]
                prev_dir = np.arctan2(current[1] - prev[1], current[0] - prev[0])
                
                # Find neighbor that continues most in same direction (rightmost turn)
                next_point = max(unvisited, key=lambda n: 
                    np.cos(np.arctan2(n[1] - current[1], n[0] - current[0]) - prev_dir))
            else:
                # First segment - choose any neighbor
                next_point = unvisited[0]
            
            visited_edges.add((current, next_point))
            boundary.append(next_point)
            current = next_point
            
            # Stop if we've returned to start
            dist_to_start = np.sqrt((current[0] - start[0])**2 + (current[1] - start[1])**2)
            if len(boundary) > 3 and dist_to_start < self.snap_tolerance:
                break
        
        return boundary
    
    def _find_parallel_inner_boundary(self, outer_boundary: list, all_segments: list, 
                                     page_width: float, page_height: float) -> list:
        """Find inner boundary parallel to outer boundary"""
        if not outer_boundary or len(outer_boundary) < 4:
            return []
        
        # Calculate offset direction for each point in outer boundary (inward normal)
        inner_points = []
        
        for i in range(len(outer_boundary) - 1):
            p1 = outer_boundary[i]
            p2 = outer_boundary[i + 1]
            
            # Calculate segment direction
            dx = p2[0] - p1[0]
            dy = p2[1] - p1[1]
            length = np.sqrt(dx**2 + dy**2)
            
            if length < 0.1:
                continue
            
            # Perpendicular direction (inward)
            # For clockwise outer boundary, rotate 90° left for inward normal
            normal_x = -dy / length
            normal_y = dx / length
            
            # Search for parallel segments at typical wall thickness offset
            for offset_dist in [3, 4, 5, 6, 7, 8]:  # Try different wall thicknesses (pts)
                inner_x = p1[0] + normal_x * offset_dist
                inner_y = p1[1] + normal_y * offset_dist
                
                # Find segments near this expected inner position
                for seg in all_segments:
                    x1, y1, x2, y2 = seg
                    # Check if segment endpoints are near expected inner position
                    dist1 = np.sqrt((x1 - inner_x)**2 + (y1 - inner_y)**2)
                    dist2 = np.sqrt((x2 - inner_x)**2 + (y2 - inner_y)**2)
                    
                    if dist1 < self.parallel_tolerance or dist2 < self.parallel_tolerance:
                        # Check if segment is roughly parallel to outer segment
                        seg_dx = x2 - x1
                        seg_dy = y2 - y1
                        seg_length = np.sqrt(seg_dx**2 + seg_dy**2)
                        
                        if seg_length > 0.1:
                            # Dot product to check parallelism
                            dot = (dx * seg_dx + dy * seg_dy) / (length * seg_length)
                            if abs(dot) > 0.9:  # Roughly parallel (cos(25°) ≈ 0.9)
                                inner_points.append((x1, y1))
                                inner_points.append((x2, y2))
                                break
                else:
                    continue
                break
        
        # If we found inner points, trace them into a boundary
        if len(inner_points) >= 4:
            # Remove duplicates
            unique_inner = list(set(inner_points))
            # Trace boundary from these points
            inner_segments = []
            for i, p1 in enumerate(unique_inner):
                for p2 in unique_inner[i+1:]:
                    dist = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
                    if dist > 0.5:  # Not the same point
                        inner_segments.append((p1[0], p1[1], p2[0], p2[1]))
            
            if inner_segments:
                return self._trace_perimeter(inner_segments, 'inner', page_width, page_height)
        
        # Fallback: offset outer boundary inward by typical wall thickness
        return self._offset_boundary_inward(outer_boundary, offset=5.0)
    
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
            # Average the normals of the two adjacent segments
            dx1 = p_curr[0] - p_prev[0]
            dy1 = p_curr[1] - p_prev[1]
            len1 = np.sqrt(dx1**2 + dy1**2) or 1.0
            
            dx2 = p_next[0] - p_curr[0]
            dy2 = p_next[1] - p_curr[1]
            len2 = np.sqrt(dx2**2 + dy2**2) or 1.0
            
            # Perpendicular vectors (inward)
            norm1_x = -dy1 / len1
            norm1_y = dx1 / len1
            
            norm2_x = -dy2 / len2
            norm2_y = dx2 / len2
            
            # Average normal
            avg_norm_x = (norm1_x + norm2_x) / 2
            avg_norm_y = (norm1_y + norm2_y) / 2
            avg_len = np.sqrt(avg_norm_x**2 + avg_norm_y**2) or 1.0
            
            # Offset point inward
            offset_x = p_curr[0] + (avg_norm_x / avg_len) * offset
            offset_y = p_curr[1] + (avg_norm_y / avg_len) * offset
            
            offset_points.append((offset_x, offset_y))
        
        return offset_points
