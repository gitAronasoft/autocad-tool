import fitz  # PyMuPDF
import ezdxf
from typing import List, Dict, Tuple, Optional
import os

class PDFVectorExtractor:
    """
    Extract vector content from PDF and convert to DXF entities
    This ensures the DXF contains the actual drawing, not just a reference image
    """
    
    def __init__(self):
        self.scale_factor = 1.0
        self.offset_x = 0
        self.offset_y = 0
    
    def extract_vector_paths_to_dxf(self, pdf_path: str, dxf_doc, page_num: int = 0, 
                                     target_width: float = 1000.0) -> Dict:
        """
        Extract all vector paths from PDF and add them to the DXF document
        
        Args:
            pdf_path: Path to PDF file
            dxf_doc: ezdxf document to add entities to
            page_num: Page number to extract (0-indexed)
            target_width: Target width for scaling (default 1000 units)
            
        Returns:
            Dictionary with extraction stats
        """
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                raise ValueError(f"Page {page_num} does not exist in PDF")
            
            page = doc.load_page(page_num)
            
            # Get page dimensions
            page_rect = page.rect
            page_width = page_rect.width
            page_height = page_rect.height
            
            # Calculate scaling factor to fit target width
            self.scale_factor = target_width / page_width if page_width > 0 else 1.0
            scaled_height = page_height * self.scale_factor
            
            print(f"PDF page dimensions: {page_width:.1f} x {page_height:.1f} points")
            print(f"DXF scaling: {self.scale_factor:.4f} (target: {target_width:.1f} x {scaled_height:.1f} units)")
            
            # Get all vector paths from the PDF
            paths = page.get_drawings()
            
            print(f"Found {len(paths)} vector paths in PDF")
            
            if not paths:
                print("Warning: No vector content found in PDF. This may be a raster/scanned document.")
                return {'success': False, 'vector_count': 0, 'error': 'No vector content'}
            
            # Create layer for original drawing content
            layers = dxf_doc.layers
            if "ORIGINAL_DRAWING" not in layers:
                original_layer = layers.new(name="ORIGINAL_DRAWING")
                original_layer.dxf.color = 8  # Gray
                original_layer.dxf.linetype = 'CONTINUOUS'
            
            modelspace = dxf_doc.modelspace()
            
            # Statistics
            stats = {
                'lines': 0,
                'curves': 0,
                'beziers': 0,
                'rectangles': 0,
                'other': 0
            }
            
            # Process each path
            for path in paths:
                path_items = path.get('items', [])
                
                for item in path_items:
                    try:
                        if not item or len(item) < 1:
                            stats['other'] += 1
                            continue
                        
                        item_type = item[0]  # First element is the type
                        
                        if item_type == 'l':  # Line
                            # Format: ('l', point1, point2)
                            if len(item) < 3:
                                stats['other'] += 1
                                continue
                            
                            p1 = self._convert_pdf_to_dxf_coords(item[1], page_height)
                            p2 = self._convert_pdf_to_dxf_coords(item[2], page_height)
                            
                            line = modelspace.add_line(
                                (p1[0], p1[1], 0),
                                (p2[0], p2[1], 0)
                            )
                            line.dxf.layer = "ORIGINAL_DRAWING"
                            stats['lines'] += 1
                        
                        elif item_type == 'c':  # Cubic Bezier curve
                            # Format: ('c', point1, point2, point3, point4)
                            if len(item) < 5:
                                stats['other'] += 1
                                continue
                            
                            # Convert Bezier to polyline approximation
                            points = [
                                self._convert_pdf_to_dxf_coords(item[1], page_height),
                                self._convert_pdf_to_dxf_coords(item[2], page_height),
                                self._convert_pdf_to_dxf_coords(item[3], page_height),
                                self._convert_pdf_to_dxf_coords(item[4], page_height)
                            ]
                            
                            # Approximate Bezier with line segments
                            bezier_points = self._approximate_bezier(points, num_segments=10)
                            
                            polyline = modelspace.add_lwpolyline(bezier_points)
                            polyline.dxf.layer = "ORIGINAL_DRAWING"
                            stats['beziers'] += 1
                        
                        elif item_type == 're':  # Rectangle
                            # Format: ('re', rect)
                            if len(item) < 2:
                                stats['other'] += 1
                                continue
                            
                            rect = item[1]
                            
                            # Handle Rect object properly
                            if hasattr(rect, 'x0'):
                                x0, y0, x1, y1 = rect.x0, rect.y0, rect.x1, rect.y1
                            elif hasattr(rect, 'ul'):
                                # Quad object
                                x0, y0 = rect.ul.x, rect.ul.y
                                x1, y1 = rect.lr.x, rect.lr.y
                            else:
                                # Skip unknown rect type
                                stats['other'] += 1
                                continue
                            
                            # Convert corners
                            p1 = self._convert_pdf_to_dxf_coords(fitz.Point(x0, y0), page_height)
                            p2 = self._convert_pdf_to_dxf_coords(fitz.Point(x1, y0), page_height)
                            p3 = self._convert_pdf_to_dxf_coords(fitz.Point(x1, y1), page_height)
                            p4 = self._convert_pdf_to_dxf_coords(fitz.Point(x0, y1), page_height)
                            
                            # Draw rectangle as closed polyline
                            rect_points = [p1, p2, p3, p4]
                            polyline = modelspace.add_lwpolyline(rect_points)
                            polyline.close(True)
                            polyline.dxf.layer = "ORIGINAL_DRAWING"
                            stats['rectangles'] += 1
                        
                        elif item_type == 'qu':  # Quadratic curve
                            # Format: ('qu', point1, point2, point3)
                            if len(item) < 4:
                                stats['other'] += 1
                                continue
                            
                            points = [
                                self._convert_pdf_to_dxf_coords(item[1], page_height),
                                self._convert_pdf_to_dxf_coords(item[2], page_height),
                                self._convert_pdf_to_dxf_coords(item[3], page_height)
                            ]
                            
                            # Approximate quadratic curve with line segments
                            curve_points = self._approximate_quadratic(points, num_segments=8)
                            
                            polyline = modelspace.add_lwpolyline(curve_points)
                            polyline.dxf.layer = "ORIGINAL_DRAWING"
                            stats['curves'] += 1
                        
                        else:
                            stats['other'] += 1
                    
                    except Exception as e:
                        # Skip malformed items but continue processing
                        stats['other'] += 1
                        continue
            
            doc.close()
            
            total_entities = sum(stats.values())
            print(f"Extracted vector content: {total_entities} entities")
            print(f"  Lines: {stats['lines']}, Curves: {stats['curves']}, "
                  f"Beziers: {stats['beziers']}, Rectangles: {stats['rectangles']}, "
                  f"Other: {stats['other']}")
            
            return {
                'success': True,
                'vector_count': total_entities,
                'stats': stats,
                'scale_factor': self.scale_factor,
                'dimensions': (target_width, scaled_height)
            }
            
        except Exception as e:
            print(f"Error extracting vector paths: {e}")
            import traceback
            traceback.print_exc()
            return {'success': False, 'vector_count': 0, 'error': str(e)}
    
    def _convert_pdf_to_dxf_coords(self, pdf_obj, page_height: float) -> Tuple[float, float]:
        """
        Convert PDF coordinates to DXF coordinates
        PDF: Origin at top-left, Y increases downward
        DXF: Origin at bottom-left, Y increases upward
        
        Handles Point, Quad, Rect, and tuple objects
        """
        # Handle different object types from PyMuPDF
        if hasattr(pdf_obj, 'x') and hasattr(pdf_obj, 'y'):
            # Point object
            x = pdf_obj.x
            y = pdf_obj.y
        elif hasattr(pdf_obj, 'x0') and hasattr(pdf_obj, 'y0'):
            # Rect object - use bottom-left corner
            x = pdf_obj.x0
            y = pdf_obj.y0
        elif hasattr(pdf_obj, 'ul'):
            # Quad object - use upper-left corner
            x = pdf_obj.ul.x
            y = pdf_obj.ul.y
        elif isinstance(pdf_obj, (list, tuple)) and len(pdf_obj) >= 2:
            # Tuple or list [x, y]
            x = pdf_obj[0]
            y = pdf_obj[1]
        else:
            # Unknown type, try to extract x, y
            print(f"Warning: Unknown coordinate type: {type(pdf_obj)}")
            x = 0
            y = 0
        
        # Apply scaling and flip Y coordinate
        x_dxf = x * self.scale_factor + self.offset_x
        y_dxf = (page_height - y) * self.scale_factor + self.offset_y
        
        return (x_dxf, y_dxf)
    
    def _approximate_bezier(self, control_points: List[Tuple[float, float]], 
                           num_segments: int = 10) -> List[Tuple[float, float]]:
        """
        Approximate a cubic Bezier curve with line segments
        
        Args:
            control_points: List of 4 control points [(x,y), ...]
            num_segments: Number of line segments to use
        """
        if len(control_points) != 4:
            return control_points
        
        p0, p1, p2, p3 = control_points
        points = []
        
        for i in range(num_segments + 1):
            t = i / num_segments
            
            # Cubic Bezier formula
            x = (1-t)**3 * p0[0] + 3*(1-t)**2*t * p1[0] + 3*(1-t)*t**2 * p2[0] + t**3 * p3[0]
            y = (1-t)**3 * p0[1] + 3*(1-t)**2*t * p1[1] + 3*(1-t)*t**2 * p2[1] + t**3 * p3[1]
            
            points.append((x, y))
        
        return points
    
    def _approximate_quadratic(self, control_points: List[Tuple[float, float]], 
                               num_segments: int = 8) -> List[Tuple[float, float]]:
        """
        Approximate a quadratic curve with line segments
        
        Args:
            control_points: List of 3 control points [(x,y), ...]
            num_segments: Number of line segments to use
        """
        if len(control_points) != 3:
            return control_points
        
        p0, p1, p2 = control_points
        points = []
        
        for i in range(num_segments + 1):
            t = i / num_segments
            
            # Quadratic Bezier formula
            x = (1-t)**2 * p0[0] + 2*(1-t)*t * p1[0] + t**2 * p2[0]
            y = (1-t)**2 * p0[1] + 2*(1-t)*t * p1[1] + t**2 * p2[1]
            
            points.append((x, y))
        
        return points
    
    def check_pdf_has_vector_content(self, pdf_path: str, page_num: int = 0) -> Tuple[bool, str]:
        """
        Check if PDF page has vector content
        
        Returns:
            (has_vector, message)
        """
        try:
            doc = fitz.open(pdf_path)
            
            if page_num >= len(doc):
                doc.close()
                return False, f"Page {page_num} does not exist"
            
            page = doc.load_page(page_num)
            paths = page.get_drawings()
            images = page.get_images()
            
            doc.close()
            
            if len(paths) > 0:
                return True, f"Found {len(paths)} vector paths"
            elif len(images) > 0:
                return False, f"PDF contains only raster images ({len(images)} images, no vector content)"
            else:
                return False, "PDF appears to be empty or unsupported format"
                
        except Exception as e:
            return False, f"Error checking PDF: {e}"
