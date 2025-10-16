import os
import fitz  # PyMuPDF
from typing import List, Tuple
from PIL import Image, ImageEnhance
import cv2
import numpy as np

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
        self.min_dpi = 150  # Minimum acceptable DPI
        self.optimal_dpi = 300  # Optimal DPI for analysis
    
    def convert_to_images(self, pdf_path: str, output_dir: str = None) -> List[str]:
        """
        Convert PDF pages to high-resolution PNG images with preprocessing
        
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
            
            # Detect if PDF is vector or scanned
            is_vector = self._is_vector_pdf(doc)
            print(f"PDF type: {'Vector' if is_vector else 'Scanned/Raster'}")
            
            # Adjust DPI if needed for better quality
            effective_dpi = self._get_effective_dpi(doc, is_vector)
            effective_zoom = effective_dpi / 72.0
            
            print(f"Converting PDF with {len(doc)} page(s) at {effective_dpi} DPI...")
            
            # Process each page
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                
                # Create transformation matrix for high DPI
                mat = fitz.Matrix(effective_zoom, effective_zoom)
                
                # Render page to pixmap
                pix = page.get_pixmap(matrix=mat, alpha=False)
                
                # Generate output filename
                base_name = os.path.splitext(os.path.basename(pdf_path))[0]
                output_path = os.path.join(output_dir, f"{base_name}_page_{page_num + 1}.png")
                
                # Save as PNG
                pix.save(output_path)
                
                print(f"  Converted page {page_num + 1}: {pix.width}x{pix.height} pixels -> {output_path}")
                
                # Validate and preprocess image for better wall detection
                preprocessed_path = self._preprocess_image(output_path, is_vector)
                image_paths.append(preprocessed_path)
            
            doc.close()
            
            print(f"Successfully converted and preprocessed {len(image_paths)} page(s) from PDF")
            return image_paths
            
        except Exception as e:
            print(f"Error converting PDF to images: {e}")
            raise Exception(f"PDF conversion failed: {str(e)}")
    
    def _is_vector_pdf(self, doc) -> bool:
        """Detect if PDF contains vector graphics or is a scanned image"""
        try:
            # Check first page for vector content
            if len(doc) == 0:
                return False
            
            page = doc.load_page(0)
            
            # Count drawings (vector paths) vs images (raster)
            drawings = page.get_drawings()
            images = page.get_images()
            
            # If there are many drawings and few/no images, it's likely vector
            if len(drawings) > 10 and len(images) <= 1:
                return True
            
            # If it's mostly images, it's likely scanned
            if len(images) > 0 and len(drawings) < 5:
                return False
            
            # Default to vector for better quality
            return len(drawings) > 0
            
        except Exception as e:
            print(f"Warning: Could not detect PDF type: {e}")
            return True  # Default to vector
    
    def _get_effective_dpi(self, doc, is_vector: bool) -> int:
        """Determine optimal DPI based on PDF type"""
        if is_vector:
            # Vector PDFs can use higher DPI for better accuracy
            return max(self.dpi, self.optimal_dpi)
        else:
            # For scanned PDFs, use requested DPI but ensure minimum quality
            return max(self.dpi, self.min_dpi)
    
    def _preprocess_image(self, image_path: str, is_vector: bool) -> str:
        """
        Preprocess image to enhance wall visibility for AI analysis
        
        Args:
            image_path: Path to image file
            is_vector: Whether the source PDF was vector
            
        Returns:
            Path to preprocessed image (same as input, modified in place)
        """
        try:
            # Load image
            img = cv2.imread(image_path)
            if img is None:
                print(f"Warning: Could not load image for preprocessing: {image_path}")
                return image_path
            
            # Validate image quality
            quality_ok, quality_msg = self._validate_image_quality(img)
            if not quality_ok:
                print(f"Warning: Image quality issue: {quality_msg}")
            
            # Apply preprocessing based on PDF type
            if is_vector:
                # For vector PDFs, minimal processing (already clean)
                processed = self._enhance_vector_image(img)
            else:
                # For scanned PDFs, apply enhancement
                processed = self._enhance_scanned_image(img)
            
            # Save preprocessed image
            cv2.imwrite(image_path, processed)
            print(f"  Preprocessed image for optimal wall detection")
            
            return image_path
            
        except Exception as e:
            print(f"Warning: Image preprocessing failed: {e}")
            return image_path  # Return original if preprocessing fails
    
    def _validate_image_quality(self, img) -> Tuple[bool, str]:
        """Validate image quality for architectural analysis"""
        height, width = img.shape[:2]
        
        # Check minimum resolution
        if width < 800 or height < 600:
            return False, f"Image resolution too low ({width}x{height}). Minimum 800x600 recommended."
        
        # Check for blank or nearly blank images
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        mean_intensity = np.mean(gray)
        
        if mean_intensity < 10 or mean_intensity > 245:
            return False, f"Image appears too dark or too bright (mean intensity: {mean_intensity:.1f})"
        
        # Check for sufficient contrast (edge detection)
        edges = cv2.Canny(gray, 50, 150)
        edge_ratio = np.sum(edges > 0) / (width * height)
        
        if edge_ratio < 0.01:
            return False, f"Image has very low detail/contrast (edge ratio: {edge_ratio:.4f})"
        
        return True, "Image quality acceptable"
    
    def _enhance_vector_image(self, img):
        """Minimal enhancement for vector PDF images (already clean)"""
        # Convert to grayscale if needed for better wall detection
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            # Convert back to BGR for consistency
            enhanced = cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)
        else:
            enhanced = img
        
        # Slight contrast enhancement
        alpha = 1.1  # Contrast control
        beta = 5     # Brightness control
        enhanced = cv2.convertScaleAbs(enhanced, alpha=alpha, beta=beta)
        
        return enhanced
    
    def _enhance_scanned_image(self, img):
        """Enhanced preprocessing for scanned/raster PDF images"""
        # Convert to grayscale
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img
        
        # Apply denoising for scanned documents
        denoised = cv2.fastNlMeansDenoising(gray, None, h=10, templateWindowSize=7, searchWindowSize=21)
        
        # Enhance contrast using CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Apply sharpening to make walls more distinct
        kernel = np.array([[-1,-1,-1],
                          [-1, 9,-1],
                          [-1,-1,-1]])
        sharpened = cv2.filter2D(enhanced, -1, kernel)
        
        # Convert back to BGR for consistency
        result = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
        
        return result
    
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
