"""
DXFBuilder - Creates AutoCAD DXF files with original drawing + traced boundaries
"""
import ezdxf
from ezdxf import colors
from ezdxf.enums import TextEntityAlignment
import logging

logger = logging.getLogger(__name__)


class DXFBuilder:
    """Builds DXF files with proper layer organization"""
    
    # Layer configuration
    LAYERS = {
        "ORIGINAL_DRAWING": {"color": colors.WHITE, "description": "Original PDF vector content"},
        "EXTERIOR": {"color": colors.YELLOW, "description": "Outer wall boundary"},
        "INTERIOR": {"color": colors.CYAN, "description": "Inner wall boundaries"},
        "GARAGE": {"color": colors.GREEN, "description": "Garage wall boundary"}
    }
    
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.doc = ezdxf.new('R2010')  # AutoCAD 2010 format for compatibility
        self.msp = self.doc.modelspace()
        self._create_layers()
    
    def _create_layers(self):
        """Create all required layers with proper colors"""
        for layer_name, config in self.LAYERS.items():
            self.doc.layers.add(
                name=layer_name,
                color=config["color"]
            )
        logger.info(f"Created {len(self.LAYERS)} standard layers")
    
    def add_pdf_vectors(self, vector_paths: list, page_width_pt: float, page_height_pt: float):
        """
        Add original PDF vector paths to ORIGINAL_DRAWING layer.
        
        Args:
            vector_paths: List of drawing paths from PyMuPDF
            page_width_pt: Page width in points
            page_height_pt: Page height in points
        """
        if not vector_paths:
            logger.warning("No vector paths to add")
            return
        
        # Calculate scale factor to fit in DXF space (target ~1000 units)
        scale = 1000.0 / max(page_width_pt, page_height_pt)
        
        added_count = 0
        skipped_count = 0
        
        for path in vector_paths:
            try:
                items = path.get("items", [])
                if not items:
                    skipped_count += 1
                    continue
                
                # Get path properties
                rect = path.get("rect")
                fill = path.get("fill")
                stroke = path.get("color")
                width = path.get("width", 0.5)
                
                # Extract coordinates from path items
                # PyMuPDF path items: 'l'=line, 'm'=move, 'c'=curve, 're'=rectangle, 'qu'=quad, etc.
                points = []
                current_pos = None
                
                for item in items:
                    item_type = item[0]
                    
                    if item_type == 'm':  # Move to
                        # Move command: ('m', Point(x, y))
                        if len(item) > 1:
                            point = item[1]
                            if hasattr(point, 'x') and hasattr(point, 'y'):
                                current_pos = (point.x, point.y)
                            elif isinstance(point, (tuple, list)) and len(point) >= 2:
                                current_pos = (point[0], point[1])
                            if current_pos:
                                points.append(self._transform_point(current_pos, page_height_pt, scale))
                    
                    elif item_type == 'l':  # Line
                        # Line command: ('l', Point(x1, y1), Point(x2, y2))
                        if len(item) >= 3:
                            # Extract start and end points
                            for point in [item[1], item[2]]:
                                if hasattr(point, 'x') and hasattr(point, 'y'):
                                    current_pos = (point.x, point.y)
                                    points.append(self._transform_point(current_pos, page_height_pt, scale))
                                elif isinstance(point, (tuple, list)) and len(point) >= 2:
                                    current_pos = (point[0], point[1])
                                    points.append(self._transform_point(current_pos, page_height_pt, scale))
                    
                    elif item_type == 'c':  # Curve (Bezier)
                        # Curve command: ('c', Point1, Point2, Point3) - 3 control points
                        for pt_item in item[1:]:
                            if hasattr(pt_item, 'x') and hasattr(pt_item, 'y'):
                                current_pos = (pt_item.x, pt_item.y)
                                points.append(self._transform_point(current_pos, page_height_pt, scale))
                            elif isinstance(pt_item, (tuple, list)) and len(pt_item) >= 2:
                                current_pos = (pt_item[0], pt_item[1])
                                points.append(self._transform_point(current_pos, page_height_pt, scale))
                    
                    elif item_type == 'qu':  # Quad bezier
                        # Quadratic bezier: ('qu', Point1, Point2)
                        for pt_item in item[1:]:
                            if hasattr(pt_item, 'x') and hasattr(pt_item, 'y'):
                                current_pos = (pt_item.x, pt_item.y)
                                points.append(self._transform_point(current_pos, page_height_pt, scale))
                            elif isinstance(pt_item, (tuple, list)) and len(pt_item) >= 2:
                                current_pos = (pt_item[0], pt_item[1])
                                points.append(self._transform_point(current_pos, page_height_pt, scale))
                    
                    elif item_type == 're':  # Rectangle
                        # Rectangle: ('re', Rect) or ('re', (x, y, w, h))
                        if len(item) > 1:
                            rect_item = item[1]
                            if hasattr(rect_item, 'x0'):  # Rect object
                                x, y, w, h = rect_item.x0, rect_item.y0, rect_item.width, rect_item.height
                            elif isinstance(rect_item, (tuple, list)) and len(rect_item) >= 4:
                                x, y, w, h = rect_item[:4]
                            else:
                                continue
                            
                            # Create rectangle points
                            rect_points = [
                                self._transform_point((x, y), page_height_pt, scale),
                                self._transform_point((x + w, y), page_height_pt, scale),
                                self._transform_point((x + w, y + h), page_height_pt, scale),
                                self._transform_point((x, y + h), page_height_pt, scale),
                                self._transform_point((x, y), page_height_pt, scale)
                            ]
                            points.extend(rect_points)
                
                # Draw path if we have points
                if len(points) >= 2:
                    # Draw as polyline
                    self.msp.add_lwpolyline(
                        points,
                        dxfattribs={
                            'layer': 'ORIGINAL_DRAWING',
                            'color': colors.WHITE
                        }
                    )
                    added_count += 1
                else:
                    skipped_count += 1
                    
            except Exception as e:
                logger.debug(f"Skipped path due to error: {e}")
                skipped_count += 1
                continue
        
        logger.info(f"Added {added_count} vector paths to ORIGINAL_DRAWING layer ({skipped_count} skipped)")
    
    def add_boundary(self, coordinates: list, floor_type: str, boundary_type: str):
        """
        Add a traced boundary to the appropriate layer.
        
        Args:
            coordinates: List of [x, y] pixel coordinates from AI
            floor_type: Floor type (basement, main_floor, etc.)
            boundary_type: Type of boundary (exterior, interior, garage_wall)
        """
        if not coordinates or len(coordinates) < 3:
            logger.warning(f"Skipping {boundary_type} boundary - insufficient points")
            return
        
        # Determine layer and create custom layer name
        layer_mapping = {
            "exterior": ("EXTERIOR", f"{floor_type}_exterior"),
            "interior": ("INTERIOR", f"{floor_type}_interior"),
            "garage_wall": ("GARAGE", f"{floor_type}_garage_wall")
        }
        
        base_layer, custom_layer_name = layer_mapping.get(boundary_type, ("EXTERIOR", f"{floor_type}_{boundary_type}"))
        
        # Create custom layer if it doesn't exist
        if custom_layer_name not in self.doc.layers:
            layer_config = self.LAYERS.get(base_layer.upper(), self.LAYERS["EXTERIOR"])
            self.doc.layers.add(
                name=custom_layer_name,
                color=layer_config["color"]
            )
        
        # Add polyline on custom layer
        self.msp.add_lwpolyline(
            coordinates,
            close=True,
            dxfattribs={
                'layer': custom_layer_name,
                'color': self.LAYERS[base_layer]["color"]
            }
        )
        
        logger.info(f"Added {boundary_type} boundary to layer '{custom_layer_name}' ({len(coordinates)} points)")
    
    def _transform_point(self, point: tuple, page_height: float, scale: float) -> tuple:
        """
        Transform PDF coordinates to DXF coordinates.
        
        PDF: (0,0) at top-left, Y increases downward
        DXF: (0,0) at bottom-left, Y increases upward
        
        Args:
            point: (x, y) in PDF coordinates
            page_height: PDF page height in points
            scale: Scale factor
            
        Returns:
            (x, y) in DXF coordinates
        """
        x, y = point
        # Flip Y axis and scale
        dxf_x = x * scale
        dxf_y = (page_height - y) * scale
        return (dxf_x, dxf_y)
    
    def save(self):
        """Save the DXF file"""
        try:
            self.doc.saveas(self.output_path)
            logger.info(f"DXF file saved successfully: {self.output_path}")
            return self.output_path
        except Exception as e:
            logger.error(f"Failed to save DXF: {e}")
            raise Exception(f"Failed to save DXF file: {str(e)}")
