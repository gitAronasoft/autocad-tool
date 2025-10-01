# AI-Powered AutoCAD Analyzer

## Overview

This is an AI-powered architectural drawing analysis tool that integrates with AutoCAD to automatically process DXF/DWG files. The system uses computer vision and OpenAI's GPT models to analyze architectural drawings, detect building elements (walls, doors, windows), classify floor types (basement, main floor, second floor), and automatically generate properly named AutoCAD layers. The application provides both a web interface for file uploads and a command-line demo interface for testing functionality.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Web Interface**: Flask-based web application with Bootstrap CSS framework
- **File Upload System**: Drag-and-drop interface supporting DXF and DWG files up to 50MB
- **Real-time Feedback**: AJAX-based file processing with progress indicators
- **Responsive Design**: Mobile-friendly interface using Bootstrap grid system

### Backend Architecture
- **Framework**: Flask web framework for HTTP request handling
- **Modular Design**: Separation of concerns with dedicated modules for AI analysis and AutoCAD integration
- **File Processing Pipeline**: Secure file upload handling with filename sanitization and type validation
- **Error Handling**: Comprehensive exception handling with user-friendly error messages

### Core Components
- **ArchitecturalAnalyzer**: Main AI analysis engine that processes architectural drawings using OpenAI's vision models
- **AutoCADIntegration**: Handles DXF file creation, layer management, and AutoCAD-compatible output generation
- **Layer Management System**: Predefined naming conventions for different building elements and floor types

### AI Integration
- **Vision Analysis**: Uses OpenAI's latest GPT model for image analysis and element detection
- **Element Detection**: Automatically identifies walls (interior/exterior), doors, windows, and garage spaces
- **Floor Classification**: Distinguishes between basement, main floor, and second floor plans
- **Smart Layer Naming**: Generates contextually appropriate AutoCAD layer names based on building elements

### Data Processing
- **File Format Support**: Handles both DXF and DWG file formats using ezdxf library
- **Image Processing**: OpenCV and PIL for image manipulation and analysis
- **Vector Graphics**: Direct manipulation of CAD vector data for precise element detection

## External Dependencies

### AI Services
- **OpenAI API**: GPT models for architectural drawing analysis and element detection
- **Computer Vision**: OpenCV for image processing and feature detection

### CAD Integration
- **ezdxf**: Python library for reading, writing, and manipulating DXF files
- **AutoCAD Compatibility**: Generates R2010 format DXF files for broad compatibility

### Web Framework
- **Flask**: Python web framework for request handling and routing
- **Bootstrap**: Frontend CSS framework for responsive design
- **Font Awesome**: Icon library for user interface elements

### File Processing
- **Werkzeug**: Secure filename handling and file upload utilities
- **PIL (Pillow)**: Image processing and format conversion
- **NumPy**: Numerical operations for image and vector data processing

### Environment Configuration
- **Environment Variables**: OpenAI API key configuration through environment variables
- **File System**: Local file storage for uploads and outputs with automatic directory creation

## Recent Changes (October 2025)

### Boundary Highlighting System (October 2025)
**Issues Fixed**: 
1. Entity extraction failing (returning 0 entities)
2. Perimeter detection finding wrong segments due to dimension/annotation outliers
3. All walls classified as interior (0 exterior detected)
4. Drawing individual line segments instead of continuous boundaries

**Solutions Implemented**:

1. **Fixed Entity Extraction**:
   - Added stateless extraction method to avoid state corruption
   - Fixed issue where `current_doc` was being overwritten before extraction
   - Now successfully extracts 5,000+ entities from architectural drawings

2. **Improved Perimeter Detection**:
   - Implemented 2% percentile-based bounds trimming to exclude dimension/annotation outliers
   - Adaptive tolerance based on building size (1% of smaller dimension, minimum 5 units)
   - Increased perimeter detection from 3-11 segments to 200+ segments

3. **Smart Wall Classification**:
   - Prioritizes longest segments first for better main wall detection
   - Forgiving multi-criteria classification:
     * ≥3 perimeter segments = exterior
     * >30% perimeter segments = exterior  
     * Long wall (>200 units) touching perimeter = exterior
   - Successfully identifies 20-30 exterior groups and 400+ interior groups

4. **Continuous Boundary Tracing**:
   - Groups connected segments into continuous polylines
   - Traces outer boundaries (building perimeter) as complete paths
   - Traces inner boundaries (interior walls) as complete paths
   - Uses connection tolerance of 2.0 units with bidirectional extension

**Visual Output**:
- **Outer boundaries (exterior)**: Yellow polylines on `[floor] exterior line` layer
- **Inner boundaries (interior)**: Magenta polylines on `[floor] interior line` layer
- Doors: Green on element-specific layers
- Windows: Blue on element-specific layers

**Performance**:
- Processes up to 1,500 prioritized segments for grouping
- Handles large architectural drawings (7,000+ segments)
- Completes analysis in under 30 seconds

### Replit Environment Setup (Completed October 1, 2025)
- **Flask Web App**: Running on port 5000 with webview output ✓
- **Workflow**: Configured with `uv run python main.py` ✓
- **Deployment**: Autoscale deployment with gunicorn configured ✓
- **Environment Secrets**: 
  - SESSION_SECRET: Configured ✓
  - OPENAI_API_KEY: Configured ✓
- **Dependencies**: All Python packages installed via uv (pyproject.toml) ✓
- **Web Interface**: Accessible and fully functional ✓
- **Git Configuration**: .gitignore updated with uv/Python entries ✓
- **Project Structure**:
  - `/src` - Core modules (architectural_analyzer.py, autocad_integration.py, enhanced_geometry_processor.py)
  - `/templates` - Flask HTML templates
  - `/uploads` - User uploaded DXF files
  - `/outputs` - Processed DXF files and measurements
  - `app.py` - Main Flask application with proxy fix for Replit
  - `main.py` - Application entry point
  - `demo.py` - Command-line demo (optional)

**GitHub Import Complete**: Fresh clone successfully configured and running in Replit environment with all dependencies, workflows, and deployment settings properly configured.