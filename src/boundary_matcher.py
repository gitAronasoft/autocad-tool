"""
BoundaryMatcher - Intelligent matching of AI-identified regions with vector-detected boundaries
Uses overlap scoring to select the correct boundaries based on AI semantic classification
"""
import logging
import numpy as np

logger = logging.getLogger(__name__)


class BoundaryMatcher:
    """Matches AI bounding boxes with vector-detected boundary candidates"""
    
    def __init__(self):
        self.min_overlap_threshold = 0.3  # Minimum 30% overlap to consider a match
    
    def match_boundaries(
        self, 
        ai_outer_bbox: dict, 
        ai_inner_bbox: dict, 
        all_boundaries: list,
        page_width: float,
        page_height: float,
        image_width: int,
        image_height: int
    ) -> dict:
        """
        Match AI-identified wall regions with vector-detected boundaries.
        
        Args:
            ai_outer_bbox: AI bounding box for exterior outer wall (in pixels)
            ai_inner_bbox: AI bounding box for exterior inner wall (in pixels)
            all_boundaries: List of all vector-detected boundary candidates
            page_width: PDF page width in points
            page_height: PDF page height in points
            image_width: Image width in pixels (for coordinate conversion)
            image_height: Image height in pixels (for coordinate conversion)
            
        Returns:
            Dictionary with matched exterior_outer and exterior_inner boundaries
        """
        logger.info("Matching AI-identified regions with vector boundaries...")
        
        # Convert AI bboxes from image pixels to PDF points
        outer_bbox_pt = self._convert_bbox_to_points(
            ai_outer_bbox, image_width, image_height, page_width, page_height
        ) if ai_outer_bbox else None
        
        inner_bbox_pt = self._convert_bbox_to_points(
            ai_inner_bbox, image_width, image_height, page_width, page_height
        ) if ai_inner_bbox else None
        
        if not outer_bbox_pt and not inner_bbox_pt:
            logger.warning("No valid AI bounding boxes - using geometric fallback")
            return self._geometric_fallback(all_boundaries, page_width, page_height)
        
        # Calculate overlap scores for each boundary with AI regions
        boundary_scores = []
        for i, boundary in enumerate(all_boundaries):
            if len(boundary) < 3:
                continue
            
            # Calculate bounding box of this boundary
            xs = [p[0] for p in boundary]
            ys = [p[1] for p in boundary]
            boundary_bbox = {
                'min_x': min(xs), 'max_x': max(xs),
                'min_y': min(ys), 'max_y': max(ys)
            }
            
            # Calculate overlap with AI outer bbox
            outer_overlap = 0
            if outer_bbox_pt:
                outer_overlap = self._calculate_overlap(boundary_bbox, outer_bbox_pt)
            
            # Calculate overlap with AI inner bbox
            inner_overlap = 0
            if inner_bbox_pt:
                inner_overlap = self._calculate_overlap(boundary_bbox, inner_bbox_pt)
            
            boundary_scores.append({
                'index': i,
                'boundary': boundary,
                'bbox': boundary_bbox,
                'outer_overlap': outer_overlap,
                'inner_overlap': inner_overlap,
                'num_points': len(boundary)
            })
        
        # Select best matches
        result = {'exterior_outer': [], 'exterior_inner': [], 'interior_walls': []}
        
        # Find boundary with highest overlap with outer bbox
        if outer_bbox_pt:
            outer_candidates = [b for b in boundary_scores if b['outer_overlap'] > self.min_overlap_threshold]
            if outer_candidates:
                # Sort by overlap score, then by number of points (higher detail preferred)
                outer_candidates.sort(key=lambda b: (b['outer_overlap'], b['num_points']), reverse=True)
                best_outer = outer_candidates[0]
                result['exterior_outer'] = best_outer['boundary']
                logger.info(f"  Matched OUTER: {best_outer['num_points']} points, {best_outer['outer_overlap']:.1%} overlap with AI bbox")
        
        # Find boundary with highest overlap with inner bbox
        if inner_bbox_pt:
            inner_candidates = [b for b in boundary_scores if b['inner_overlap'] > self.min_overlap_threshold]
            # Exclude the one we already selected as outer
            if result['exterior_outer']:
                inner_candidates = [b for b in inner_candidates if b['boundary'] is not result['exterior_outer']]
            
            if inner_candidates:
                # Sort by overlap score, then by number of points
                inner_candidates.sort(key=lambda b: (b['inner_overlap'], b['num_points']), reverse=True)
                best_inner = inner_candidates[0]
                result['exterior_inner'] = best_inner['boundary']
                logger.info(f"  Matched INNER: {best_inner['num_points']} points, {best_inner['inner_overlap']:.1%} overlap with AI bbox")
        
        # If no matches found, use geometric fallback
        if not result['exterior_outer'] or not result['exterior_inner']:
            logger.warning("Insufficient AI matches - using geometric fallback for missing boundaries")
            fallback = self._geometric_fallback(all_boundaries, page_width, page_height)
            if not result['exterior_outer']:
                result['exterior_outer'] = fallback['exterior_outer']
                logger.info(f"  Fallback OUTER: {len(result['exterior_outer'])} points")
            if not result['exterior_inner']:
                result['exterior_inner'] = fallback['exterior_inner']
                logger.info(f"  Fallback INNER: {len(result['exterior_inner'])} points")
        
        return result
    
    def _convert_bbox_to_points(
        self, bbox_px: dict, img_w: int, img_h: int, page_w: float, page_h: float
    ) -> dict:
        """Convert bounding box from image pixels to PDF points"""
        if not bbox_px:
            return None
        
        # Scale factors
        x_scale = page_w / img_w
        y_scale = page_h / img_h
        
        return {
            'min_x': bbox_px['min_x'] * x_scale,
            'min_y': bbox_px['min_y'] * y_scale,
            'max_x': bbox_px['max_x'] * x_scale,
            'max_y': bbox_px['max_y'] * y_scale
        }
    
    def _calculate_overlap(self, bbox1: dict, bbox2: dict) -> float:
        """
        Calculate overlap ratio between two bounding boxes.
        Returns ratio of intersection area to bbox1 area (0.0 to 1.0)
        """
        # Calculate intersection rectangle
        inter_min_x = max(bbox1['min_x'], bbox2['min_x'])
        inter_min_y = max(bbox1['min_y'], bbox2['min_y'])
        inter_max_x = min(bbox1['max_x'], bbox2['max_x'])
        inter_max_y = min(bbox1['max_y'], bbox2['max_y'])
        
        # Check if there's an intersection
        if inter_min_x >= inter_max_x or inter_min_y >= inter_max_y:
            return 0.0
        
        # Calculate areas
        inter_area = (inter_max_x - inter_min_x) * (inter_max_y - inter_min_y)
        bbox1_area = (bbox1['max_x'] - bbox1['min_x']) * (bbox1['max_y'] - bbox1['min_y'])
        
        if bbox1_area == 0:
            return 0.0
        
        return inter_area / bbox1_area
    
    def _geometric_fallback(self, boundaries: list, page_width: float, page_height: float) -> dict:
        """
        Fallback to geometric selection when AI matching fails.
        Selects boundaries closest to page edges with largest bounding boxes.
        """
        if not boundaries:
            return {'exterior_outer': [], 'exterior_inner': []}
        
        boundary_info = []
        for boundary in boundaries:
            if len(boundary) < 3:
                continue
            
            xs = [p[0] for p in boundary]
            ys = [p[1] for p in boundary]
            min_x, max_x = min(xs), max(xs)
            min_y, max_y = min(ys), max(ys)
            
            # Calculate bbox size and edge proximity
            bbox_width = max_x - min_x
            bbox_height = max_y - min_y
            bbox_size_ratio = ((bbox_width / page_width) + (bbox_height / page_height)) / 2
            
            edge_distance = min(min_x, min_y, page_width - max_x, page_height - max_y)
            
            boundary_info.append({
                'points': boundary,
                'bbox_size_ratio': bbox_size_ratio,
                'edge_distance': edge_distance,
                'num_points': len(boundary)
            })
        
        # Sort by edge proximity (closer is better), then bbox size
        boundary_info.sort(key=lambda b: (-b['edge_distance'], b['bbox_size_ratio']), reverse=True)
        
        result = {'exterior_outer': [], 'exterior_inner': []}
        
        if len(boundary_info) >= 1:
            result['exterior_outer'] = boundary_info[0]['points']
        
        if len(boundary_info) >= 2:
            result['exterior_inner'] = boundary_info[1]['points']
        
        return result
