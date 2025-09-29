import os
import json
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from src.architectural_analyzer import ArchitecturalAnalyzer
from src.autocad_integration import AutoCADIntegration
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('outputs', exist_ok=True)

ALLOWED_EXTENSIONS = {'dxf'}  # DWG requires conversion to DXF

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main upload page"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_file():
    """Process uploaded DXF file with AI analysis"""
    try:
        # Check if file was uploaded
        if 'dxf_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['dxf_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload DXF files only. DWG files require conversion to DXF format.'})
        
        # Save uploaded file
        if file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            return jsonify({'success': False, 'error': 'Invalid filename'})
        file.save(filepath)
        
        # Initialize AI analyzer and AutoCAD integration
        analyzer = ArchitecturalAnalyzer()
        autocad = AutoCADIntegration()
        
        # For DXF files, we need to convert to image for AI analysis
        # For now, we'll load the DXF and process it directly
        result = process_dxf_file(filepath, analyzer, autocad)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'})

def process_dxf_file(filepath, analyzer, autocad):
    """Process a DXF file and return analysis results"""
    try:
        # Load the DXF file
        success = autocad.load_dxf_file(filepath)
        if not success:
            return {'success': False, 'error': 'Could not load DXF file'}
        
        # Perform real DXF geometric analysis to extract wall patterns and coordinates
        print("Starting real DXF geometric analysis...")
        
        # Use the new geometric analysis method with AI enhancement instead of hardcoded coordinates
        analysis_result = autocad.analyze_dxf_geometry(analyzer)
        
        layers_created = []
        elements_detected = 0
        
        # Create layers dynamically based on real analysis results
        for space in analysis_result.get('spaces', []):
            layer_name = space['layer_name']
            wall_type = space['type']
            
            # Get appropriate color for the wall type
            color = autocad.get_layer_color(wall_type)
            autocad.create_layer(layer_name, color)
            layers_created.append(layer_name)
        
        # Create layers for any detected elements (doors, windows, etc.)
        for element in analysis_result.get('elements', []):
            layer_name = element['layer_name']
            element_type = element['type']
            
            color = autocad.get_layer_color(element_type)
            autocad.create_layer(layer_name, color)
            if layer_name not in layers_created:
                layers_created.append(layer_name)
        
        # Log analysis metadata for debugging
        metadata = analysis_result.get('analysis_metadata', {})
        if metadata:
            print(f"Analysis metadata:")
            print(f"  Entities extracted: {metadata.get('entities_extracted', {})}")
            print(f"  Wall groups found: {metadata.get('wall_groups_found', 0)}")
            if metadata.get('building_bounds'):
                bounds = metadata['building_bounds']
                print(f"  Building bounds: {bounds['width']:.1f} x {bounds['height']:.1f} units")
            if metadata.get('fallback_used'):
                print("  Warning: Using fallback analysis - no geometry detected")
        
        # Execute the drawing commands
        commands_executed = autocad.execute_autocad_commands(analysis_result)
        elements_detected = commands_executed
        
        # Save the processed file
        output_filename = f"processed_{os.path.basename(filepath)}"
        output_path = os.path.join('outputs', output_filename)
        autocad.save_dxf(output_path)
        
        # Export measurements if available
        export_urls = {}
        if 'measurements' in analysis_result and analysis_result['measurements']:
            export_results = autocad.export_measurements(analysis_result['measurements'])
            for format_type, file_path in export_results.items():
                export_filename = os.path.basename(file_path)
                export_urls[format_type] = f'/download/{export_filename}'
        
        return {
            'success': True,
            'analysis': {
                'drawing_type': analysis_result['drawing_type'],
                'layers_created': layers_created,
                'elements_detected': elements_detected,
                'measurements_summary': {
                    'total_walls': len(analysis_result.get('measurements', {}).get('walls', [])),
                    'total_doors': len(analysis_result.get('measurements', {}).get('doors', [])),
                    'total_windows': len(analysis_result.get('measurements', {}).get('windows', [])),
                    'perimeter_length': analysis_result.get('measurements', {}).get('perimeter_length', 0),
                    'total_area': analysis_result.get('measurements', {}).get('total_area', 0)
                }
            },
            'download_url': f'/download/{output_filename}',
            'export_urls': export_urls
        }
        
    except Exception as e:
        return {'success': False, 'error': f'DXF processing error: {str(e)}'}

@app.route('/download/<filename>')
def download_file(filename):
    """Download processed DXF file"""
    try:
        return send_file(os.path.join('outputs', filename), as_attachment=True)
    except Exception as e:
        return jsonify({'error': f'Download error: {str(e)}'}), 404

if __name__ == '__main__':
    print("🚀 Starting AI-Powered AutoCAD Analyzer Web Server...")
    print("📁 Upload folder:", app.config['UPLOAD_FOLDER'])
    print("🌐 Access the interface at: http://localhost:5000")
    app.run(host='0.0.0.0', port=5000, debug=True)