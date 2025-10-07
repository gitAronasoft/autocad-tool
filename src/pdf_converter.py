import os
import fitz  # PyMuPDF
from typing import List, Tuple
from PIL import Image

class PDFConverter:
    """Convert PDF architectural drawings to high-quality images for AI analysis"""
    
    def __init__(self, dpi: int = 300):
        """
        Initialize PDF converter
        
        Args:
            dpi: Resolution for image conversion (default 300 for architectural drawings)
        """
        self.dpi = dpi
        self.zoom = dpi / 72.0  # PDF default is 72 DPI
    
    def convert_to_images(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """
        Convert PDF pages to high-resolution PNG images
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save images (default: same as PDF)
            
        Returns:
            List of paths to generated image files
        """
        if output_dir is None:
            output_dir = os.path.dirname(pdf_path)
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        image_paths = []
        
        try:
            # Open PDF document
            doc = fitz.open(pdf_path)
            
            print(f"Converting PDF with {len(doc)} page(s) at {self.dpi} DPI...")
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Create transformation matrix for high DPI
                mat = fitz.Matrix(self.zoom, self.zoom)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Generate output filename
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.png")
                
                # Save as PNG
                pix.save(output_path)
                image_paths.append(output_path)
                
                print(f"  Converted page {page_num + 1}: {pix.width}x{pix.height} pixels -> {output_path}")
            
            doc.close()
            
            print(f"Successfully converted {len(image_paths)} page(s) from PDF")
            return image_paths
            
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            raise Exception(f"PDF conversion failed: {str(e)}")
    
    def get_page_count(self, pdf_path: str) -> int:
        """Get number of pages in PDF"""
        try:
            doc = fitz.open(pdf_path)
            count = len(doc)
            doc.close()
            return count
        except Exception as e:
            print(f"Error reading PDF: {e}")
            return 0
    
    def validate_pdf(self, pdf_path: str) -> Tuple[bool, str]:
        """
        Validate PDF file
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            doc = fitz.open(pdf_path)
            page_count = len(doc)
            doc.close()
            
            if page_count == 0:
                return False, "PDF file contains no pages"
            
            return True, ""
            
        except Exception as e:
            return False, f"Invalid PDF file: {str(e)}"
