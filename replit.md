# AI-Powered AutoCAD Wall Boundary Tracer - SaaS Application

## Overview
This project is a SaaS application designed to automate the tracing of wall boundaries from PDF architectural drawings. It processes floor plans to identify inner and outer wall lines, including garage spaces, and generates DXF files compatible with AutoCAD. The DXF output includes the original drawing content and newly traced boundaries on properly named, distinct layers, facilitating easy measurement extraction. The ultimate vision is to create a tool capable of full automation, including measurement extraction and integration with other estimation tools, minimizing human intervention.


## Product Vision & Roadmap

### Stage 1: Floor Plans (CURRENT PRIORITY - MVP)
**Objective**: Automatically trace wall boundaries in floor plan drawings

**What It Does**:
- Upload PDF architectural drawing (basement, main floor, second floor, etc.)
- AI detects floor type automatically (basement/main/second/garage)
- Traces **inner boundary** (interior wall line) 
- Traces **outer boundary** (exterior wall line)
- Detects **garage spaces** and traces garage wall (buffered/protected space)
- Generates DXF with original drawing + boundary highlights

**Layer Naming Convention**:
- `[floor_type]_exterior_outer` - Outer edge of exterior walls (building perimeter)
- `[floor_type]_exterior_inner` - Inner edge of exterior walls (conditioned space boundary)
- `[floor_type]_interior_walls` - Interior wall boundaries (room dividers)
- `[floor_type]_garage_wall` - Wall separating garage from conditioned space

**Examples**:
- `basement_exterior_outer`, `basement_exterior_inner`, `basement_interior_walls`
- `main_floor_exterior_outer`, `main_floor_exterior_inner`, `main_floor_interior_walls`, `main_floor_garage_wall`
- `second_floor_exterior_outer`, `second_floor_exterior_inner`, `second_floor_interior_walls`

**Output**: DXF file ready for AutoCAD containing:
- ORIGINAL_DRAWING layer - Complete PDF vector content (walls, dimensions, text, etc.)
- Traced boundary layers with proper names
- Ready for measurement extraction in AutoCAD

**Success Criteria**:
- AI correctly identifies floor type
- Boundary traces are accurate
- DXF opens in AutoCAD with all layers properly named
- Processing time < 30 seconds per drawing

### Stage 2: Elevations (FUTURE)
**Objective**: Detect and trace doors/windows in elevation views

**Features**:
- Detect elevation type (front/back/left/right view)
- Trace door shapes: `front_door_main`, `back_door_basement`
- Trace window shapes: `front_window_main`, `left_window_basement`
- Trace door windows: `front_door_window`
- Layer naming: `[direction]_[element]_[floor]`

**Output**: DXF with elevation elements traced on named layers

### Stage 3: Advanced Automation (FUTURE)
**Objective**: Full automation with measurements and batch processing

**Features**:
- Height calculations from elevation data
- Automatic measurement extraction (area, perimeter, XYZ)
- Excel export of all measurements
- Batch processing of multiple drawings
- Quality validation and error detection
- Integration with HVAC/estimation tools

**Vision**: Zero human intervention - upload → process → export measurements

## User Preferences
- Communication: Simple, everyday language
- Focus: Production-ready, accurate wall tracing
- Priority: Speed (< 30s) + proper AutoCAD layer naming

## System Architecture

### Core Processing Strategy
The system primarily uses a vector-based geometric approach for wall detection due to limitations with AI vision for precise tracing. AI is leveraged only for metadata analysis.

**Processing Flow (Vector-Based Approach)**:
1.  **PDF Upload**: User uploads a PDF.
2.  **PDFProcessor Service**: Extracts all vector paths from the PDF and converts the page to a 300 DPI image for metadata analysis.
3.  **VectorWallDetector Service**: Filters wall segments by stroke color (black) and line weight (≥0.2pt), groups connected segments into accurate wall boundaries, and classifies them as exterior outer, exterior inner, or interior walls. This service processes all path commands (m, l, c, qu, re, h) to preserve curves and geometric detail. It uses a KDTree for vertex snapping and graph-based loop tracing for precision.
4.  **FloorPlanAnalyzer Service (AI for Metadata Only)**: Utilizes AI (GPT-4o Vision) to detect the floor type (basement/main/second/terrace) with 95% confidence and identify the presence of a garage. It does *not* perform wall tracing.
5.  **DXFBuilder Service**: Combines the original PDF vectors onto an `ORIGINAL_DRAWING` layer with the vector-based wall boundaries onto properly named layers (e.g., `[floor_type]_exterior_outer`, `[floor_type]_exterior_inner`, `[floor_type]_interior_walls`, `[floor_type]_garage_wall`).
6.  **DXF Download**: The user downloads the generated DXF file, ready for AutoCAD.

### Key Design Decisions
*   **Vector-Based Wall Detection**: Prioritizes processing actual PDF geometry over AI vision inference for accuracy.
*   **AI for Metadata Only**: GPT-4o Vision is used solely for high-level classifications like floor type and garage presence.
*   **Preservation of Original Drawing**: The DXF output includes all original PDF vectors, ensuring completeness.
*   **Geometric Filtering & Classification**: Walls are identified by stroke color, line weight, and grouped into coherent boundaries, then classified based on their spatial relationship. A combined metric of `perimeter × √(num_points)` is used to accurately identify main wall boundaries, preventing small features from being misidentified.
*   **Standardized Layer Organization**: Layers in the DXF output follow a strict naming convention and color scheme (e.g., Yellow for exterior outer, Magenta for exterior inner) for AutoCAD compatibility.
*   **Robustness**: Handles various PDF drawing styles and complex geometries, processing curves and polylines accurately.

### Technology Stack
*   **Backend**: Flask (Python 3.11)
*   **Wall Detection**: Custom VectorWallDetector (geometric/CV approach)
*   **AI Metadata**: OpenAI GPT-4o Vision
*   **PDF Processing**: PyMuPDF (fitz)
*   **DXF Generation**: ezdxf (AutoCAD R2010 format)
*   **Geometry Processing**: NumPy
*   **Storage**: Local filesystem

## External Dependencies
*   **OpenAI API**: For GPT-4o Vision, used by the `FloorPlanAnalyzer` for floor type and garage detection.
*   **PyMuPDF (fitz)**: Python library for PDF processing, used by `PDFProcessor` for vector extraction and image conversion.
*   **ezdxf**: Python library for creating and modifying DXF files, used by `DXFBuilder` to generate AutoCAD-compatible outputs.
*   **NumPy**: Python library for numerical operations, utilized for geometric calculations in wall detection.