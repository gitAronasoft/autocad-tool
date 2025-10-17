import os
import logging
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from src.pdf_processor import PDFProcessor
from src.floor_plan_analyzer import FloorPlanAnalyzer
from src.dxf_builder import DXFBuilder
from src.advanced_wall_detector import AdvancedWallDetector
import traceback

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['OUTPUT_FOLDER'] = 'outputs'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    """Process uploaded PDF file with AI analysis"""
    try:
        # Validate file upload
        if 'pdf_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload PDF files only.'})
        
        # Save uploaded file
        filename = secure_filename(file.filename or 'uploaded.pdf')
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"Processing uploaded file: {filename}")
        
        # Process the PDF
        result = process_pdf_drawing(filepath)
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'})

def process_pdf_drawing(filepath: str) -> dict:
    """
    Main processing pipeline for PDF architectural drawings.
    Combines vector extraction + AI analysis + DXF generation.
    """
    try:
        logger.info("="*60)
        logger.info("STAGE 1: FLOOR PLAN BOUNDARY TRACING")
        logger.info("="*60)
        
        # Step 1: Extract PDF data and convert to image
        logger.info("Step 1: Processing PDF...")
        with PDFProcessor(filepath) as processor:
            # Get page info
            page_info = processor.get_page_info(0)
            logger.info(f"  PDF: {page_info['width_pt']:.0f}x{page_info['height_pt']:.0f} pt, "
                       f"{page_info['num_vector_paths']} vector paths")
            
            # Extract vector paths for original drawing
            vector_paths = processor.extract_vector_paths(0)
            logger.info(f"  Extracted {len(vector_paths)} vector paths")
            
            # Convert to image for AI analysis
            image, metadata = processor.convert_to_image(0, dpi=300)
            logger.info(f"  Converted to {metadata['width_px']}x{metadata['height_px']} image")
        
        # Step 2A: High-fidelity wall detection with fixed classification
        logger.info("Step 2A: Detecting wall boundaries (high-fidelity mode)...")
        wall_detector = AdvancedWallDetector()
        wall_boundaries = wall_detector.detect_walls(vector_paths, page_info['width_pt'], page_info['height_pt'])
        
        # Step 2B: AI Analysis - detect metadata only (floor type, garage)
        logger.info("Step 2B: AI analyzing floor plan metadata...")
        analyzer = FloorPlanAnalyzer()
        metadata_result = analyzer.analyze_floor_plan(image)
        
        floor_type = metadata_result['floor_type']
        confidence = metadata_result['confidence']
        logger.info(f"  Floor type: {floor_type} (confidence: {confidence:.0%})")
        logger.info(f"  Has garage: {metadata_result['has_garage']}")
        
        # Step 3: Build DXF with original drawing + traced boundaries
        logger.info("Step 3: Building DXF output...")
        
        # Create output filename
        base_name = os.path.splitext(os.path.basename(filepath))[0]
        output_filename = f"processed_{base_name}.dxf"
        output_path = os.path.join(app.config['OUTPUT_FOLDER'], output_filename)
        
        # Initialize DXF builder
        dxf_builder = DXFBuilder(output_path)
        
        # Add original PDF vectors
        dxf_builder.add_pdf_vectors(
            vector_paths,
            page_info['width_pt'],
            page_info['height_pt']
        )
        
        # Transform PDF coordinates to DXF coordinates
        page_height_pt = page_info['height_pt']
        scale = 1000.0 / max(page_info['width_pt'], page_info['height_pt'])
        
        # Convert PDF point coordinates to DXF coordinates
        def pdf_to_dxf(coords):
            """Convert PDF point coordinates to DXF coordinates"""
            dxf_coords = []
            for x_pt, y_pt in coords:
                # Transform to DXF coordinates (flip Y, scale)
                dxf_x = x_pt * scale
                dxf_y = (page_height_pt - y_pt) * scale
                dxf_coords.append((dxf_x, dxf_y))
            return dxf_coords
        
        # Add ONLY exterior walls - outer and inner boundaries (main wall only)
        if wall_boundaries['exterior_outer']:
            outer_coords = pdf_to_dxf(wall_boundaries['exterior_outer'])
            dxf_builder.add_boundary(outer_coords, floor_type, 'exterior_outer')
            logger.info(f"  Added exterior OUTER boundary ({len(outer_coords)} points)")
        
        # Add exterior walls - inner boundary
        if wall_boundaries['exterior_inner']:
            inner_coords = pdf_to_dxf(wall_boundaries['exterior_inner'])
            dxf_builder.add_boundary(inner_coords, floor_type, 'exterior_inner')
            logger.info(f"  Added exterior INNER boundary ({len(inner_coords)} points)")
        
        # Interior walls are NOT highlighted - only showing outer main wall boundaries
        logger.info(f"  Skipping {len(wall_boundaries['interior_walls'])} interior walls (main wall only mode)")
        
        # Save DXF file
        dxf_builder.save()
        logger.info(f"  DXF saved: {output_filename}")
        
        logger.info("="*60)
        logger.info("PROCESSING COMPLETE!")
        logger.info("="*60)
        
        # Prepare response
        layers_created = ['ORIGINAL_DRAWING']
        
        if wall_boundaries['exterior_outer']:
            layers_created.append(f'{floor_type}_exterior_outer')
        
        if wall_boundaries['exterior_inner']:
            layers_created.append(f'{floor_type}_exterior_inner')
        
        # Count boundaries (only exterior walls - main wall only)
        num_exterior_outer = 1 if wall_boundaries['exterior_outer'] else 0
        num_exterior_inner = 1 if wall_boundaries['exterior_inner'] else 0
        
        return {
            'success': True,
            'analysis': {
                'floor_type': floor_type,
                'confidence': confidence,
                'has_garage': metadata_result['has_garage'],
                'layers_created': layers_created,
                'boundaries_detected': {
                    'exterior_outer': num_exterior_outer,
                    'exterior_inner': num_exterior_inner
                }
            },
            'download_url': f'/download/{output_filename}'
        }
        
    except Exception as e:
        logger.error(f"Processing failed: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed DXF file"""
    try:
        file_path = os.path.join(app.config['OUTPUT_FOLDER'], filename)
        if os.path.exists(file_path):
            return send_file(file_path, as_attachment=True)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        logger.error(f"Download error: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
