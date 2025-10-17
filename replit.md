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
The system uses a **Hybrid Approach** combining vector-based precision with AI semantic classification for robust wall detection.

**Processing Flow (Hybrid Approach)**:
1.  **PDF Upload**: User uploads a PDF architectural drawing.
2.  **PDFProcessor Service**: Extracts all vector paths from the PDF and converts the page to a 300 DPI image for AI analysis.
3.  **AdvancedWallDetector Service**: Processes all path commands (m, l, c, qu, re, h) to extract wall boundaries with high fidelity. Uses KDTree for vertex snapping (0.5pt tolerance) and graph-based loop tracing to preserve curves and geometric detail. Filters by stroke color (black) and line weight (≥0.2pt), producing all candidate boundaries.
4.  **FloorPlanAnalyzer Service (AI Visual Classification)**: Utilizes GPT-4o Vision for two purposes:
    *   **Metadata Detection**: Floor type (basement/main/second/terrace) and garage presence
    *   **Main Wall Identification**: Returns bounding box coordinates for exterior outer and inner walls (semantic understanding of "main building perimeter")
5.  **BoundaryMatcher Service**: Intelligent matching layer that compares AI-identified wall regions with vector-detected boundaries using overlap scoring. Selects the boundaries that best match AI's semantic classification.
6.  **DXFBuilder Service**: Combines the original PDF vectors onto an `ORIGINAL_DRAWING` layer with the matched wall boundaries onto properly named layers (e.g., `[floor_type]_exterior_outer`, `[floor_type]_exterior_inner`).
7.  **DXF Download**: User downloads the generated DXF file, ready for AutoCAD.

### Key Design Decisions
*   **Hybrid Architecture**: Combines vector precision (exact coordinates from PDF) with AI semantic understanding (identifies "what is a main wall").
*   **AI Semantic Classification**: GPT-4o Vision identifies WHERE main walls are located, preventing misidentification of interior elements as building perimeter.
*   **Vector-Based Coordinates**: All final boundaries use actual PDF geometry (no AI hallucination), ensuring measurement accuracy.
*   **Intelligent Boundary Matching**: Overlap scoring algorithm matches AI bounding boxes with vector-detected boundaries for reliable selection.
*   **Preservation of Original Drawing**: The DXF output includes all original PDF vectors, ensuring completeness.
*   **Standardized Layer Organization**: Layers in the DXF output follow a strict naming convention and color scheme (Yellow for exterior outer, Magenta for exterior inner) for AutoCAD compatibility.
*   **Robustness**: Handles various PDF drawing styles, complex geometries, and edge cases where interior elements are near page borders.

### Technology Stack
*   **Backend**: Flask (Python 3.11)
*   **Wall Detection**: AdvancedWallDetector (vector-based) + BoundaryMatcher (AI-guided selection)
*   **AI Classification**: OpenAI GPT-4o Vision
*   **PDF Processing**: PyMuPDF (fitz)
*   **DXF Generation**: ezdxf (AutoCAD R2010 format)
*   **Geometry Processing**: NumPy, SciPy (KDTree for spatial indexing)
*   **Storage**: Local filesystem

### Future Scope & Architecture Evolution

**Stage 1 Enhancements (Floor Plans)**:
*   **Multi-Floor Relationships**: AI identifies relationships between basement/main/second floor boundaries for consistency validation
*   **Quality Validation**: AI verifies traced boundaries match drawing intent and flags inconsistencies
*   **Adaptive Learning**: Track which boundary selection criteria work best for different drawing styles

**Stage 2 Foundation (Elevations)**:
*   **Reusable Pattern**: Same hybrid approach applies to door/window detection
    - Vector detector extracts all rectangular shapes
    - AI Vision identifies "this is a door" vs "this is a window" 
    - BoundaryMatcher selects correct elements based on AI guidance
*   **Cross-Reference**: Link elevation elements to floor plan boundaries for height calculations

**Stage 3 Integration (Full Automation)**:
*   **AI Measurement Extraction**: AI identifies dimension lines and text, validates against vector measurements
*   **Batch Intelligence**: AI learns from multiple drawings to improve classification accuracy
*   **Quality Assurance**: AI-powered validation ensures exported measurements are consistent

**Architectural Benefits**:
*   **Separation of Concerns**: Vector precision (coordinates) + AI intelligence (classification) = best of both worlds
*   **Scalability**: Add new element types (stairs, columns) without changing core detection engine
*   **Reliability**: Fallback to geometric methods if AI classification fails
*   **Accuracy**: No AI hallucination in final measurements (always uses actual PDF vectors)

## External Dependencies
*   **OpenAI API**: For GPT-4o Vision, used by the `FloorPlanAnalyzer` for floor type and garage detection.
*   **PyMuPDF (fitz)**: Python library for PDF processing, used by `PDFProcessor` for vector extraction and image conversion.
*   **ezdxf**: Python library for creating and modifying DXF files, used by `DXFBuilder` to generate AutoCAD-compatible outputs.
*   **NumPy**: Python library for numerical operations, utilized for geometric calculations in wall detection.