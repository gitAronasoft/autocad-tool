"""
VectorWallDetector - Extract wall boundaries from PDF vector paths using geometric analysis
"""
import logging
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class VectorWallDetector:
    """Detects and traces wall boundaries from PDF vector geometry"""
    
    def __init__(self):
        self.wall_threshold_width = 0.2  # Minimum line width for walls
        self.connection_tolerance = 2.0  # Points within this distance are considered connected
        
    def detect_walls(self, vector_paths: list, page_width: float, page_height: float) -> dict:
        """
        Extract wall boundaries from PDF vector paths.
        
        Args:
            vector_paths: List of drawing paths from PyMuPDF
            page_width: Page width in points
            page_height: Page height in points
            
        Returns:
            Dictionary with exterior_outer, exterior_inner, and interior_walls boundaries
        """
        logger.info(f"Analyzing {len(vector_paths)} vector paths for walls...")
        
        # Step 1: Filter for wall lines (black strokes with appropriate width)
        wall_segments = self._extract_wall_segments(vector_paths)
        logger.info(f"  Found {len(wall_segments)} wall line segments")
        
        if not wall_segments:
            logger.warning("No wall segments found!")
            return {
                'exterior_outer': [],
                'exterior_inner': [],
                'interior_walls': []
            }
        
        # Step 2: Group segments by proximity to form boundaries
        boundaries = self._group_into_boundaries(wall_segments, page_width, page_height)
        logger.info(f"  Grouped into {len(boundaries)} boundaries")
        
        # Step 3: Classify boundaries as exterior or interior
        result = self._classify_boundaries(boundaries, page_width, page_height)
        
        logger.info(f"  Exterior outer: {len(result['exterior_outer'])} points")
        logger.info(f"  Exterior inner: {len(result['exterior_inner'])} points")
        logger.info(f"  Interior walls: {len(result['interior_walls'])} boundaries")
        
        return result
    
    def _extract_wall_segments(self, vector_paths: list) -> list:
        """Extract line segments that represent walls"""
        segments = []
        
        for path in vector_paths:
            # Filter for stroked paths (walls are stroked, not filled)
            stroke_color = path.get('color')
            fill_color = path.get('fill')
            width = path.get('width', 0)
            
            # Walls are typically black strokes (0,0,0) with meaningful width
            is_black_stroke = (stroke_color == (0.0, 0.0, 0.0) or 
                             stroke_color == [0.0, 0.0, 0.0])
            has_width = width is not None and width >= self.wall_threshold_width
            
            if not (is_black_stroke and has_width):
                continue
            
            # Extract line segments from path items
            items = path.get('items', [])
            for item in items:
                if not item:
                    continue
                    
                item_type = item[0] if len(item) > 0 else None
                
                if item_type == 'l' and len(item) >= 3:  # Line segment
                    p1 = item[1]
                    p2 = item[2]
                    
                    # Extract coordinates
                    if hasattr(p1, 'x') and hasattr(p2, 'x'):
                        x1, y1 = p1.x, p1.y
                        x2, y2 = p2.x, p2.y
                    elif isinstance(p1, (tuple, list)) and isinstance(p2, (tuple, list)):
                        x1, y1 = p1[0], p1[1]
                        x2, y2 = p2[0], p2[1]
                    else:
                        continue
                    
                    segments.append({
                        'start': (x1, y1),
                        'end': (x2, y2),
                        'width': width,
                        'length': np.sqrt((x2-x1)**2 + (y2-y1)**2)
                    })
        
        return segments
    
    def _group_into_boundaries(self, segments: list, page_width: float, page_height: float) -> list:
        """Group connected segments into boundary polylines"""
        if not segments:
            return []
        
        # Sort segments by length (longer segments are more likely to be main walls)
        segments = sorted(segments, key=lambda s: s['length'], reverse=True)
        
        # Build connectivity graph
        used = set()
        boundaries = []
        
        for i, seg in enumerate(segments):
            if i in used:
                continue
            
            # Start a new boundary with this segment
            boundary_points = [seg['start'], seg['end']]
            used.add(i)
            
            # Try to extend the boundary by finding connected segments
            changed = True
            max_iterations = len(segments)
            iteration = 0
            
            while changed and iteration < max_iterations:
                changed = False
                iteration += 1
                
                for j, other_seg in enumerate(segments):
                    if j in used:
                        continue
                    
                    # Check if this segment connects to our boundary
                    first_point = boundary_points[0]
                    last_point = boundary_points[-1]
                    
                    # Try all 4 connection possibilities
                    dist_start_start = self._point_distance(first_point, other_seg['start'])
                    dist_start_end = self._point_distance(first_point, other_seg['end'])
                    dist_end_start = self._point_distance(last_point, other_seg['start'])
                    dist_end_end = self._point_distance(last_point, other_seg['end'])
                    
                    tol = self.connection_tolerance
                    
                    if dist_end_start < tol:
                        # Connect at end
                        boundary_points.append(other_seg['end'])
                        used.add(j)
                        changed = True
                    elif dist_end_end < tol:
                        # Connect at end (reverse)
                        boundary_points.append(other_seg['start'])
                        used.add(j)
                        changed = True
                    elif dist_start_start < tol:
                        # Connect at start (reverse)
                        boundary_points.insert(0, other_seg['end'])
                        used.add(j)
                        changed = True
                    elif dist_start_end < tol:
                        # Connect at start
                        boundary_points.insert(0, other_seg['start'])
                        used.add(j)
                        changed = True
            
            # Only keep boundaries with enough points
            if len(boundary_points) >= 3:
                # Close the boundary if needed
                if self._point_distance(boundary_points[0], boundary_points[-1]) < self.connection_tolerance * 2:
                    boundary_points.append(boundary_points[0])
                
                boundaries.append(boundary_points)
        
        return boundaries
    
    def _classify_boundaries(self, boundaries: list, page_width: float, page_height: float) -> dict:
        """Classify boundaries as exterior outer, exterior inner, or interior walls"""
        if not boundaries:
            return {
                'exterior_outer': [],
                'exterior_inner': [],
                'interior_walls': []
            }
        
        # Calculate bounding box and perimeter for each boundary
        boundary_info = []
        for boundary in boundaries:
            xs = [p[0] for p in boundary]
            ys = [p[1] for p in boundary]
            
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            width = max_x - min_x
            height = max_y - min_y
            area = width * height
            perimeter = sum(self._point_distance(boundary[i], boundary[i+1]) 
                          for i in range(len(boundary)-1))
            
            boundary_info.append({
                'points': boundary,
                'area': area,
                'perimeter': perimeter,
                'min_x': min_x,
                'max_x': max_x,
                'min_y': min_y,
                'max_y': max_y
            })
        
        # Sort by area (largest first)
        boundary_info.sort(key=lambda b: b['area'], reverse=True)
        
        # The two largest boundaries are likely exterior walls (outer and inner)
        # Smaller boundaries are interior walls
        result = {
            'exterior_outer': [],
            'exterior_inner': [],
            'interior_walls': []
        }
        
        if len(boundary_info) >= 1:
            # Largest boundary is exterior outer
            result['exterior_outer'] = boundary_info[0]['points']
        
        if len(boundary_info) >= 2:
            # Second largest is exterior inner
            result['exterior_inner'] = boundary_info[1]['points']
        
        # Remaining boundaries are interior walls
        for i in range(2, len(boundary_info)):
            result['interior_walls'].append(boundary_info[i]['points'])
        
        return result
    
    def _point_distance(self, p1: tuple, p2: tuple) -> float:
        """Calculate Euclidean distance between two points"""
        return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
