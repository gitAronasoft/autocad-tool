"""
PDFProcessor - Extract vector paths and generate AI-ready images from PDF drawings
"""
import fitz  # PyMuPDF
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF processing for architectural drawings"""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = pdf_path
        self.doc = None
        self.vector_paths = []
        
    def __enter__(self):
        self.doc = fitz.open(self.pdf_path)
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.doc:
            self.doc.close()
    
    def extract_vector_paths(self, page_num: int = 0) -> list:
        """
        Extract all vector drawing paths from a PDF page.
        These will be preserved in the output DXF as ORIGINAL_DRAWING layer.
        
        Args:
            page_num: Page number to extract (0-indexed)
            
        Returns:
            List of drawing path dictionaries from PyMuPDF
        """
        if not self.doc:
            raise ValueError("PDF not loaded. Use context manager (with statement)")
            
        if page_num >= len(self.doc):
            raise ValueError(f"Page {page_num} does not exist. PDF has {len(self.doc)} pages")
        
        page = self.doc[page_num]
        self.vector_paths = page.get_drawings()
        
        logger.info(f"Extracted {len(self.vector_paths)} vector paths from page {page_num}")
        return self.vector_paths
    
    def convert_to_image(self, page_num: int = 0, dpi: int = 300) -> tuple[Image.Image, dict]:
        """
        Convert PDF page to high-quality image for AI analysis.
        
        Args:
            page_num: Page number to convert (0-indexed)
            dpi: Resolution for conversion (default 300 for quality)
            
        Returns:
            Tuple of (PIL Image, metadata dict with width/height/dpi)
        """
        if not self.doc:
            raise ValueError("PDF not loaded. Use context manager (with statement)")
            
        if page_num >= len(self.doc):
            raise ValueError(f"Page {page_num} does not exist. PDF has {len(self.doc)} pages")
        
        page = self.doc[page_num]
        
        # Get page dimensions in points
        page_rect = page.rect
        page_width_pt = page_rect.width
        page_height_pt = page_rect.height
        
        # Convert to image at specified DPI
        mat = fitz.Matrix(dpi / 72, dpi / 72)  # 72 DPI is default
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to PIL Image
        img_data = pix.pil_tobytes(format="PNG")
        img = Image.open(io.BytesIO(img_data))
        
        metadata = {
            "width_px": pix.width,
            "height_px": pix.height,
            "width_pt": page_width_pt,
            "height_pt": page_height_pt,
            "dpi": dpi,
            "page_num": page_num
        }
        
        logger.info(f"Converted page {page_num} to image: {pix.width}x{pix.height}px at {dpi} DPI")
        return img, metadata
    
    def get_page_info(self, page_num: int = 0) -> dict:
        """
        Get information about a PDF page.
        
        Args:
            page_num: Page number (0-indexed)
            
        Returns:
            Dictionary with page information
        """
        if not self.doc:
            raise ValueError("PDF not loaded. Use context manager (with statement)")
            
        if page_num >= len(self.doc):
            raise ValueError(f"Page {page_num} does not exist. PDF has {len(self.doc)} pages")
        
        page = self.doc[page_num]
        page_rect = page.rect
        
        return {
            "page_num": page_num,
            "total_pages": len(self.doc),
            "width_pt": page_rect.width,
            "height_pt": page_rect.height,
            "has_text": len(page.get_text().strip()) > 0,
            "num_images": len(page.get_images()),
            "num_vector_paths": len(page.get_drawings())
        }
