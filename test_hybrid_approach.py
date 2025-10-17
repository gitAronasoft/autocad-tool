#!/usr/bin/env python3
"""
Test the hybrid approach - Vector detection + AI classification + Boundary matching
"""
import logging
from src.pdf_processor import PDFProcessor
from src.advanced_wall_detector import AdvancedWallDetector
from src.floor_plan_analyzer import FloorPlanAnalyzer
from src.boundary_matcher import BoundaryMatcher

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Test with user's PDF
pdf_path = 'uploads/2024_10_10_-_162_Ironwood_Trail_-_The_Linden_-_RH_-_Architectural_-_Copy_2.pdf'

logger.info("="*70)
logger.info("TESTING HYBRID APPROACH: Vector Precision + AI Semantic Classification")
logger.info("="*70)

# Step 1: Extract PDF data
logger.info("\nStep 1: Processing PDF...")
with PDFProcessor(pdf_path) as processor:
    vector_paths = processor.extract_vector_paths(0)
    image, metadata = processor.convert_to_image(0, dpi=300)
    page_width = metadata['width_pt']
    page_height = metadata['height_pt']
    img_width = metadata['width_px']
    img_height = metadata['height_px']

logger.info(f"  PDF: {page_width:.0f}x{page_height:.0f} pt")
logger.info(f"  Image: {img_width}x{img_height} px")
logger.info(f"  Vector paths: {len(vector_paths)}")

# Step 2A: Detect ALL boundary candidates with vector detector (no classification)
logger.info("\nStep 2A: Vector detection (ALL raw candidates)...")
wall_detector = AdvancedWallDetector()
all_boundary_candidates = wall_detector.detect_all_boundaries(vector_paths)
logger.info(f"  Total raw candidates detected: {len(all_boundary_candidates)}")

# Step 2B: AI classification (metadata + wall locations)
logger.info("\nStep 2B: AI classification (semantic understanding)...")
analyzer = FloorPlanAnalyzer()
ai_result = analyzer.analyze_floor_plan(image)

logger.info(f"  Floor type: {ai_result['floor_type']}")
logger.info(f"  Confidence: {ai_result['confidence']:.0%}")
logger.info(f"  Has garage: {ai_result['has_garage']}")

if ai_result.get('exterior_outer_bbox'):
    bbox = ai_result['exterior_outer_bbox']
    logger.info(f"  AI outer wall bbox: ({bbox['min_x']}, {bbox['min_y']}) to ({bbox['max_x']}, {bbox['max_y']})")
else:
    logger.info(f"  AI outer wall bbox: None")

if ai_result.get('exterior_inner_bbox'):
    bbox = ai_result['exterior_inner_bbox']
    logger.info(f"  AI inner wall bbox: ({bbox['min_x']}, {bbox['min_y']}) to ({bbox['max_x']}, {bbox['max_y']})")
else:
    logger.info(f"  AI inner wall bbox: None")

# Step 2C: Intelligent boundary matching
logger.info("\nStep 2C: Hybrid matching (AI guidance + vector precision)...")
matcher = BoundaryMatcher()
wall_boundaries = matcher.match_boundaries(
    ai_outer_bbox=ai_result.get('exterior_outer_bbox'),
    ai_inner_bbox=ai_result.get('exterior_inner_bbox'),
    all_boundaries=all_boundary_candidates,
    page_width=page_width,
    page_height=page_height,
    image_width=img_width,
    image_height=img_height
)

logger.info("\n" + "="*70)
logger.info("FINAL RESULTS:")
logger.info("="*70)
logger.info(f"✓ Exterior OUTER wall: {len(wall_boundaries['exterior_outer'])} points")
logger.info(f"✓ Exterior INNER wall: {len(wall_boundaries['exterior_inner'])} points")
logger.info(f"  Interior walls: {len(wall_boundaries['interior_walls'])} boundaries")

logger.info("\n" + "="*70)
logger.info("HYBRID APPROACH TEST COMPLETE!")
logger.info("="*70)
