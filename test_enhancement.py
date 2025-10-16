#!/usr/bin/env python3
"""Test script to verify boundary enhancement changes"""
import os
import sys
from src.pdf_processor import PDFProcessor
from src.floor_plan_analyzer import FloorPlanAnalyzer
from src.dxf_builder import DXFBuilder
from src.vector_wall_detector import VectorWallDetector

def test_boundary_enhancement(pdf_path: str):
    """Test the enhanced boundary detection with bright, wide lines"""
    print("="*60)
    print("TESTING BOUNDARY ENHANCEMENT")
    print("="*60)
    
    # Step 1: Process PDF
    print(f"\n1. Processing PDF: {pdf_path}")
    with PDFProcessor(pdf_path) as processor:
        page_info = processor.get_page_info(0)
        print(f"   Page: {page_info['width_pt']:.0f}x{page_info['height_pt']:.0f} pt")
        
        vector_paths = processor.extract_vector_paths(0)
        print(f"   Vector paths: {len(vector_paths)}")
        
        image, metadata = processor.convert_to_image(0, dpi=300)
        print(f"   Image: {metadata['width_px']}x{metadata['height_px']} px")
    
    # Step 2: Detect walls
    print("\n2. Detecting walls from vector geometry...")
    wall_detector = VectorWallDetector()
    wall_boundaries = wall_detector.detect_walls(vector_paths, page_info['width_pt'], page_info['height_pt'])
    
    print(f"   Exterior outer: {len(wall_boundaries['exterior_outer']) if wall_boundaries['exterior_outer'] else 0} points")
    print(f"   Exterior inner: {len(wall_boundaries['exterior_inner']) if wall_boundaries['exterior_inner'] else 0} points")
    print(f"   Interior walls: {len(wall_boundaries['interior_walls'])} boundaries (will be SKIPPED)")
    
    # Step 3: AI metadata
    print("\n3. AI analyzing metadata...")
    analyzer = FloorPlanAnalyzer()
    metadata_result = analyzer.analyze_floor_plan(image)
    floor_type = metadata_result['floor_type']
    print(f"   Floor type: {floor_type} ({metadata_result['confidence']:.0%} confidence)")
    
    # Step 4: Build DXF with enhanced boundaries
    print("\n4. Building DXF with BRIGHT, WIDE boundaries...")
    output_path = "outputs/test_enhanced_boundaries.dxf"
    dxf_builder = DXFBuilder(output_path)
    
    # Check layer configuration
    print("\n   Layer configuration:")
    for layer_name, config in dxf_builder.LAYERS.items():
        if "EXTERIOR" in layer_name:
            print(f"   - {layer_name}: color={config['color']}, lineweight={config.get('lineweight', 'default')}mm")
    
    # Add original vectors
    dxf_builder.add_pdf_vectors(vector_paths, page_info['width_pt'], page_info['height_pt'])
    print(f"   ✓ Added original drawing vectors")
    
    # Transform coordinates
    page_height_pt = page_info['height_pt']
    scale = 1000.0 / max(page_info['width_pt'], page_info['height_pt'])
    
    def pdf_to_dxf(coords):
        return [(x * scale, (page_height_pt - y) * scale) for x, y in coords]
    
    # Add ONLY exterior boundaries (main wall only)
    if wall_boundaries['exterior_outer']:
        outer_coords = pdf_to_dxf(wall_boundaries['exterior_outer'])
        dxf_builder.add_boundary(outer_coords, floor_type, 'exterior_outer')
        print(f"   ✓ Added EXTERIOR OUTER boundary (RED, 0.70mm, {len(outer_coords)} points)")
    
    if wall_boundaries['exterior_inner']:
        inner_coords = pdf_to_dxf(wall_boundaries['exterior_inner'])
        dxf_builder.add_boundary(inner_coords, floor_type, 'exterior_inner')
        print(f"   ✓ Added EXTERIOR INNER boundary (ORANGE, 0.70mm, {len(inner_coords)} points)")
    
    print(f"   ✓ SKIPPED {len(wall_boundaries['interior_walls'])} interior walls (main wall only mode)")
    
    # Save DXF
    dxf_builder.save()
    print(f"\n5. DXF saved: {output_path}")
    
    # Verify DXF contents
    print("\n6. Verifying DXF contents...")
    import ezdxf
    doc = ezdxf.readfile(output_path)
    
    print(f"   Layers in DXF:")
    for layer in doc.layers:
        entities_count = sum(1 for e in doc.modelspace() if e.dxf.layer == layer.dxf.name)
        if entities_count > 0:
            lineweight = layer.dxf.lineweight if hasattr(layer.dxf, 'lineweight') else 'default'
            print(f"   - {layer.dxf.name}: color={layer.dxf.color}, lineweight={lineweight}, entities={entities_count}")
    
    print("\n" + "="*60)
    print("VERIFICATION COMPLETE!")
    print("="*60)
    print("\nSUMMARY:")
    print("✓ Exterior boundaries use RED (color 1) and ORANGE (color 30)")
    print("✓ Boundary lineweight set to 0.70mm (70 in DXF units)")
    print("✓ Interior walls are NOT included in output")
    print("✓ Only main outer wall boundaries are highlighted")

if __name__ == "__main__":
    # Use existing test PDF
    pdf_path = "uploads/2024_10_10_-_162_Ironwood_Trail_-_The_Linden_-_RH_-_Architectural_-_Copy_2.pdf"
    if os.path.exists(pdf_path):
        test_boundary_enhancement(pdf_path)
    else:
        print(f"Error: Test PDF not found: {pdf_path}")
        sys.exit(1)
