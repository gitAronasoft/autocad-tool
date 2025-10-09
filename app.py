import os
import json
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
from werkzeug.middleware.proxy_fix import ProxyFix
from src.architectural_analyzer import ArchitecturalAnalyzer
from src.autocad_integration import AutoCADIntegration
from src.pdf_converter import PDFConverter
import traceback

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  # needed for url_for to generate with https
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs('outputs', exist_ok=True)

ALLOWED_EXTENSIONS = {'pdf'}  # PDF architectural drawings only

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
        # Check if file was uploaded
        if 'pdf_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'})
        
        file = request.files['pdf_file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'})
        
        if not allowed_file(file.filename):
            return jsonify({'success': False, 'error': 'Invalid file type. Please upload PDF files only.'})
        
        # Save uploaded file
        if file.filename:
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        else:
            return jsonify({'success': False, 'error': 'Invalid filename'})
        file.save(filepath)
        
        # Get trace options from form data (default all to True)
        trace_options = {
            'trace_walls': request.form.get('trace_walls', 'true').lower() == 'true',
            'trace_doors': request.form.get('trace_doors', 'true').lower() == 'true',
            'trace_windows': request.form.get('trace_windows', 'true').lower() == 'true'
        }
        
        # Validate that at least one trace option is selected
        if not any(trace_options.values()):
            return jsonify({'success': False, 'error': 'Please select at least one element type to trace (Walls, Doors, or Windows).'})
        
        print(f"Trace options: {trace_options}")
        
        # Get page number for multi-page PDFs (default to page 1)
        page_num = int(request.form.get('page_num', 1))
        
        # Initialize AI analyzer and AutoCAD integration
        analyzer = ArchitecturalAnalyzer()
        autocad = AutoCADIntegration()
        
        # Process PDF file
        result = process_pdf_file(filepath, analyzer, autocad, trace_options, page_num)
        
        return jsonify(result)
        
    except Exception as e:
        print(f"Error processing file: {str(e)}")
        traceback.print_exc()
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'})

def process_pdf_file(filepath, analyzer, autocad, trace_options=None, page_num=1):
    """Process a PDF file using AI analysis and return DXF results with improved validation"""
    try:
        # Default trace options to all True if not provided
        if trace_options is None:
            trace_options = {'trace_walls': True, 'trace_doors': True, 'trace_windows': True}
        
        print("\n" + "="*60)
        print("STEP 1: PDF VALIDATION AND CONVERSION")
        print("="*60)
        
        # Initialize PDF converter with optimal settings
        pdf_converter = PDFConverter(dpi=300)
        
        # Validate PDF file
        print("Validating PDF file...")
        is_valid, error_msg = pdf_converter.validate_pdf(filepath)
        if not is_valid:
            return {
                'success': False, 
                'error': f'PDF validation failed: {error_msg}. Please ensure you upload a valid PDF file.'
            }
        print("✓ PDF validation passed")
        
        # Get page count and validate page number
        page_count = pdf_converter.get_page_count(filepath)
        print(f"PDF contains {page_count} page(s)")
        
        if page_num < 1 or page_num > page_count:
            return {
                'success': False,
                'error': f'Invalid page number {page_num}. PDF has {page_count} page(s). Please select a page between 1 and {page_count}.'
            }
        
        print(f"Processing page {page_num} of {page_count}...")
        
        # Convert PDF to high-quality images with preprocessing
        print("Converting PDF to images with quality enhancement...")
        image_paths = pdf_converter.convert_to_images(filepath, output_dir='uploads')
        
        if not image_paths:
            return {
                'success': False, 
                'error': 'PDF to image conversion failed. The PDF may be corrupted or in an unsupported format.'
            }
        
        print(f"✓ Successfully converted {len(image_paths)} page(s) to images")
        
        # Select the requested page
        image_path = image_paths[page_num - 1]
        print(f"Using image: {image_path}")
        
        print("\n" + "="*60)
        print("STEP 2: AI DRAWING TYPE DETECTION")
        print("="*60)
        
        # Determine drawing type (floor plan or elevation) and validate
        print("Analyzing drawing type with AI...")
        try:
            drawing_type_result = analyzer.analyze_drawing_type(image_path)
            drawing_type = drawing_type_result.get('type', 'floor_plan')
            confidence = drawing_type_result.get('confidence', 0)
            reasoning = drawing_type_result.get('reasoning', 'N/A')
            
            print(f"Detected drawing type: {drawing_type.upper()}")
            print(f"Confidence: {confidence:.1%}")
            print(f"Reasoning: {reasoning}")
            
        except Exception as e:
            # Clean up temp images before returning error
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': f'AI drawing type analysis failed: {str(e)}. Please try again or contact support.'
            }
        
        # Validate this is actually an architectural drawing
        if drawing_type not in ['floor_plan', 'elevation']:
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': f'The uploaded file does not appear to be an architectural drawing (detected as: {drawing_type}). Please upload a PDF containing floor plans or elevation drawings.'
            }
        
        # Check confidence level - if AI is uncertain, warn the user
        if confidence < 0.5:
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': f'Low confidence in drawing identification ({confidence:.0%}). The image may be unclear, rotated, or not a standard architectural drawing. Please ensure the PDF contains clear, properly oriented architectural drawings.'
            }
        
        print("✓ Drawing type validated")
        
        print("\n" + "="*60)
        print("STEP 3: AI WALL BOUNDARY DETECTION")
        print("="*60)
        
        # Analyze the drawing to detect wall boundaries
        try:
            if drawing_type == 'floor_plan':
                print("Analyzing floor plan for wall boundaries...")
                analysis_result = analyzer.analyze_floor_plan(image_path)
                
                # Log detected boundaries
                spaces = analysis_result.get('spaces', [])
                exterior_count = sum(1 for s in spaces if 'exterior' in s.get('type', '').lower())
                interior_count = len(spaces) - exterior_count
                
                print(f"✓ Detected {exterior_count} exterior boundary(ies)")
                print(f"✓ Detected {interior_count} interior boundary(ies)")
                
                for i, space in enumerate(spaces):
                    coords = space.get('coordinates', [])
                    space_type = space.get('type', 'unknown')
                    print(f"  Boundary {i+1} ({space_type}): {len(coords)} coordinate points")
            else:
                print("Analyzing elevation for doors and windows...")
                analysis_result = analyzer.analyze_elevation(image_path)
                elements = analysis_result.get('elements', [])
                print(f"✓ Detected {len(elements)} architectural elements")
                
        except ValueError as e:
            # Handle validation errors from the analyzer
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': f'Wall boundary analysis failed: {str(e)}. The drawing may be too complex or unclear for automatic detection.'
            }
        except Exception as e:
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': f'AI analysis error: {str(e)}. Please try again or contact support.'
            }
        
        # Validate analysis produced results
        if not analysis_result or (not analysis_result.get('spaces') and not analysis_result.get('elements')):
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': 'No architectural elements detected in the drawing. Please ensure the PDF contains clear, visible walls, doors, or windows. The drawing may need to be higher quality or more clearly defined.'
            }
        
        # Add drawing type to results
        analysis_result['drawing_type'] = drawing_type
        print("✓ AI analysis completed successfully")
        
        print("\n" + "="*60)
        print("STEP 4: DXF GENERATION WITH WALL HIGHLIGHTS")
        print("="*60)
        
        # Create new DXF document
        print("Creating new DXF document...")
        autocad_clean = AutoCADIntegration()
        if not autocad_clean.create_new_dxf():
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': 'Failed to create DXF document. Please try again.'
            }
        print("✓ DXF document created")
        
        # Insert PDF actual vector content (or image as fallback) for complete drawing
        print("Inserting original drawing content...")
        autocad_clean.insert_pdf_as_geometry(filepath, image_path, analysis_result, page_num - 1)
        print("✓ Original drawing content inserted on ORIGINAL_DRAWING layer")
        
        # Detect wall boundaries from actual vector geometry (not AI guessing)
        print("Analyzing vector geometry to detect actual wall boundaries...")
        wall_boundaries = autocad_clean.detect_wall_boundaries_from_vector_geometry()
        
        exterior_count = len(wall_boundaries.get('outer_boundaries', []))
        interior_count = len(wall_boundaries.get('inner_boundaries', []))
        
        # If vector detection failed, fall back to AI method
        if exterior_count == 0 and interior_count == 0:
            print("Vector detection found no walls, trying AI method as fallback...")
            from PIL import Image
            with Image.open(image_path) as img:
                image_dimensions = img.size
            wall_boundaries = autocad_clean.detect_wall_boundaries_from_ai(
                analysis_result, 
                image_dimensions, 
                trace_options
            )
            exterior_count = len(wall_boundaries.get('outer_boundaries', []))
            interior_count = len(wall_boundaries.get('inner_boundaries', []))
            print(f"✓ AI fallback: {exterior_count} exterior + {interior_count} interior boundaries")
        else:
            print(f"✓ Vector analysis: {exterior_count} exterior + {interior_count} interior wall boundaries")
        
        # Draw wall boundary highlights on dedicated layers
        print("Drawing wall boundary highlights...")
        commands_executed = autocad_clean.draw_wall_boundary_highlights(wall_boundaries)
        
        if commands_executed == 0:
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': 'No wall boundaries could be drawn. The AI may not have detected valid boundaries in the drawing.'
            }
        
        print(f"✓ Drew {commands_executed} wall boundary highlights")
        
        # Collect and validate layers
        layers_created = []
        all_layers = autocad_clean.list_layers()
        for layer in all_layers:
            layer_name = layer.get('name')
            if layer_name and layer_name != '0':
                layers_created.append(layer_name)
        
        print(f"Created layers: {', '.join(layers_created)}")
        
        # Validate required layers exist
        required_layers = ['ORIGINAL_DRAWING', 'EXTERIOR_WALL_HIGHLIGHT', 'INTERIOR_WALL_HIGHLIGHT']
        missing_layers = [l for l in required_layers if l not in layers_created]
        if 'ORIGINAL_DRAWING' in missing_layers:
            print("Note: ORIGINAL_DRAWING layer may be empty (no vector trace available)")
        
        print("\n" + "="*60)
        print("STEP 5: SAVING OUTPUT FILES")
        print("="*60)
        
        # Save output DXF
        output_filename = f"processed_{os.path.splitext(os.path.basename(filepath))[0]}.dxf"
        output_path = os.path.join('outputs', output_filename)
        
        if not autocad_clean.save_dxf(output_path):
            for img_path in image_paths:
                try:
                    os.remove(img_path)
                except:
                    pass
            return {
                'success': False,
                'error': 'Failed to save DXF file. Please try again.'
            }
        
        print(f"✓ Saved DXF: {output_path}")
        
        # Copy the image file to outputs folder so DXF can reference it
        import shutil
        output_image_filename = f"processed_{os.path.splitext(os.path.basename(filepath))[0]}.png"
        output_image_path = os.path.join('outputs', output_image_filename)
        try:
            shutil.copy(image_path, output_image_path)
            print(f"✓ Saved reference image: {output_image_path}")
        except Exception as e:
            print(f"Warning: Could not copy image file: {e}")
        
        # Clean up temporary image files (keep the one we copied to outputs)
        print("Cleaning up temporary files...")
        cleanup_count = 0
        for img_path in image_paths:
            if img_path != output_image_path:
                try:
                    os.remove(img_path)
                    cleanup_count += 1
                except:
                    pass
        print(f"✓ Cleaned up {cleanup_count} temporary file(s)")
        
        print("\n" + "="*60)
        print("PROCESSING COMPLETE!")
        print("="*60)
        print(f"✓ Output DXF: {output_filename}")
        print(f"✓ Layers created: {', '.join(layers_created)}")
        print(f"✓ Wall boundaries: {exterior_count} exterior + {interior_count} interior")
        print(f"✓ Total elements: {commands_executed}")
        print("="*60 + "\n")
        
        return {
            'success': True,
            'analysis': {
                'drawing_type': drawing_type,
                'layers_created': layers_created,
                'elements_detected': commands_executed,
                'measurements_summary': {
                    'total_walls': len(analysis_result.get('spaces', [])),
                    'exterior_boundaries': exterior_count,
                    'interior_boundaries': interior_count,
                    'total_doors': len([e for e in analysis_result.get('elements', []) if 'door' in e.get('type', '').lower()]),
                    'total_windows': len([e for e in analysis_result.get('elements', []) if 'window' in e.get('type', '').lower()]),
                    'perimeter_length': 0,
                    'total_area': 0
                }
            },
            'download_url': f'/download/{output_filename}'
        }
        
    except Exception as e:
        print(f"PDF processing error: {str(e)}")
        traceback.print_exc()
        return {'success': False, 'error': f'PDF processing error: {str(e)}'}

def convert_ai_to_autocad_commands(analysis_result, trace_options):
    """Convert AI analysis results to AutoCAD drawing commands"""
    commands = []
    
    # Process spaces (walls)
    for space in analysis_result.get('spaces', []):
        space_type = space.get('type', 'interior')
        layer_name = space.get('layer_name', f'unknown_{space_type}')
        coordinates = space.get('coordinates', [])
        
        # Determine color based on type
        if 'exterior' in space_type.lower():
            color = 2  # Yellow for exterior
        elif 'garage' in space_type.lower():
            color = 4  # Cyan for garage
        else:
            color = 6  # Magenta for interior
        
        # Skip if trace option disabled
        if not trace_options.get('trace_walls', True):
            continue
        
        # Create layer command
        commands.append({
            'action': 'create_layer',
            'layer_name': layer_name,
            'color': color,
            'linetype': 'CONTINUOUS'
        })
        
        # Draw polyline
        if len(coordinates) >= 2:
            commands.append({
                'action': 'draw_polyline',
                'coordinates': coordinates,
                'layer_name': layer_name,
                'closed': False
            })
    
    # Process elements (doors, windows)
    for element in analysis_result.get('elements', []):
        element_type = element.get('type', 'unknown')
        layer_name = element.get('layer_name', f'unknown_{element_type}')
        coordinates = element.get('coordinates', [])
        
        # Determine color based on element type
        if 'door' in element_type.lower():
            color = 3  # Green for doors
            if not trace_options.get('trace_doors', True):
                continue
        elif 'window' in element_type.lower():
            color = 5  # Blue for windows
            if not trace_options.get('trace_windows', True):
                continue
        else:
            color = 7  # White for other elements
        
        # Create layer command
        commands.append({
            'action': 'create_layer',
            'layer_name': layer_name,
            'color': color,
            'linetype': 'CONTINUOUS'
        })
        
        # Draw element
        if len(coordinates) >= 2:
            commands.append({
                'action': 'draw_polyline',
                'coordinates': coordinates,
                'layer_name': layer_name,
                'closed': False
            })
    
    print(f"Generated {len(commands)} AutoCAD commands from AI analysis")
    return commands

def process_dxf_file(filepath, analyzer, autocad, trace_options=None):
    """Process a DXF file and return analysis results"""
    try:
        # Default trace options to all True if not provided
        if trace_options is None:
            trace_options = {'trace_walls': True, 'trace_doors': True, 'trace_windows': True}
        
        # Load the DXF file for analysis
        success = autocad.load_dxf_file(filepath)
        if not success:
            return {'success': False, 'error': 'Could not load DXF file'}
        
        # Perform real DXF geometric analysis to extract wall patterns and coordinates
        print("Starting real DXF geometric analysis...")
        
        # Use the new geometric analysis method with AI enhancement instead of hardcoded coordinates
        analysis_result = autocad.analyze_dxf_geometry(analyzer)
        
        # Check if analysis detected PDF underlay or other fatal errors
        if not analysis_result.get('success', True) and analysis_result.get('pdf_underlay_detected'):
            return {
                'success': False, 
                'error': analysis_result.get('error', 'DXF file contains no extractable geometry')
            }
        
        # Filter drawing commands based on trace options
        if 'drawing_commands' in analysis_result:
            original_commands = analysis_result['drawing_commands']
            filtered_commands = []
            
            for cmd in original_commands:
                layer_name = cmd.get('layer_name', '').lower()
                action = cmd.get('action', '')
                
                # Always keep essential non-geometry commands
                if action in ['set_units', 'configure', 'initialize']:
                    filtered_commands.append(cmd)
                    continue
                
                # Keep create_layer commands for layers we'll use
                if action == 'create_layer':
                    # Check if this layer will be used based on trace options
                    keep_layer = False
                    if trace_options['trace_walls'] and ('wall' in layer_name or 'exterior' in layer_name or 'interior' in layer_name):
                        keep_layer = True
                    if trace_options['trace_doors'] and 'door' in layer_name:
                        keep_layer = True
                    if trace_options['trace_windows'] and 'window' in layer_name:
                        keep_layer = True
                    
                    if keep_layer:
                        filtered_commands.append(cmd)
                # Filter drawing commands only if they have a layer_name
                elif layer_name:
                    keep_cmd = False
                    if trace_options['trace_walls'] and ('wall' in layer_name or 'exterior' in layer_name or 'interior' in layer_name):
                        keep_cmd = True
                    if trace_options['trace_doors'] and 'door' in layer_name:
                        keep_cmd = True
                    if trace_options['trace_windows'] and 'window' in layer_name:
                        keep_cmd = True
                    
                    if keep_cmd:
                        filtered_commands.append(cmd)
                # Keep all commands without a layer_name (can't filter them)
                else:
                    filtered_commands.append(cmd)
            
            analysis_result['drawing_commands'] = filtered_commands
            print(f"Filtered commands: {len(original_commands)} → {len(filtered_commands)} based on trace options")
        
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
        
        # Create a NEW clean DXF document for the output (only highlighted boundaries)
        print("Creating clean output with only highlighted wall boundaries...")
        autocad_clean = AutoCADIntegration()
        autocad_clean.create_new_dxf()
        
        layers_created = []
        
        # Execute the drawing commands on the clean document
        commands_executed = autocad_clean.execute_autocad_commands(analysis_result)
        elements_detected = commands_executed
        
        # Collect layer names from the drawing commands
        for cmd in analysis_result.get('drawing_commands', []):
            if cmd.get('action') == 'create_layer':
                layer_name = cmd.get('layer_name')
                if layer_name and layer_name not in layers_created:
                    layers_created.append(layer_name)
        
        # Save the clean processed file (only boundaries and elements)
        output_filename = f"processed_{os.path.basename(filepath)}"
        output_path = os.path.join('outputs', output_filename)
        autocad_clean.save_dxf(output_path)
        
        print(f"Saved clean output with {commands_executed} highlighted boundaries")
        
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