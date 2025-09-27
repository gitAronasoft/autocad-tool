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